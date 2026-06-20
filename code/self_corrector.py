from __future__ import annotations
import json
import logging
import random
import hashlib
from pathlib import Path
from config import (
    ALLOWED_ISSUE_TYPES, ALLOWED_SEVERITIES, CAR_PARTS, LAPTOP_PARTS,
    PACKAGE_PARTS, ALLOWED_RISK_FLAGS, OBJECT_PARTS_MAP
)
from model_client import ModelClient

logger = logging.getLogger("self_corrector")

class SelfCorrector:
    def __init__(self, client: ModelClient | None = None):
        self.client = client or ModelClient()

    def reconcile(
        self,
        image_paths: list[str],
        claim_object: str,
        claim_details: dict[str, str],
        blind_result: dict[str, object],
        aware_result: dict[str, object],
        matched_reqs: list[dict[str, str]] | None = None
    ) -> dict[str, object]:
        # Extract metadata
        user_id = claim_details.get("user_id", "unknown")
        claimed_part = claim_details.get("claimed_part", "unknown")
        claimed_damage = claim_details.get("claimed_damage", "unknown")
        stated_severity = claim_details.get("stated_severity", "unknown")

        resolved_paths = []
        for path in image_paths:
            p = Path(path)
            if not p.is_absolute():
                from config import REPO_ROOT, DATA_DIR
                p_resolved = DATA_DIR / path
                if p_resolved.exists():
                    p = p_resolved
                else:
                    p_resolved_root = REPO_ROOT / path
                    if p_resolved_root.exists():
                        p = p_resolved_root
            resolved_paths.append(str(p))

        # Get valid parts
        allowed_parts = sorted(list(OBJECT_PARTS_MAP.get(claim_object, CAR_PARTS | LAPTOP_PARTS | PACKAGE_PARTS)))

        # Format Pass A and Pass B anonymously with randomized order based on user_id hash for determinism
        blind_consensus = blind_result.get("consensus", {})
        aware_consensus = aware_result.get("consensus", {})

        blind_summary = (
            f"Pass Type: Blind Audit (No prior claim info)\n"
            f"Detected Part: {blind_consensus.get('primary_part', 'unknown')}\n"
            f"Detected Damage: {blind_consensus.get('primary_damage', 'unknown')}\n"
            f"Detected Severity: {blind_consensus.get('primary_severity', 'unknown')}\n"
            f"Justification: {blind_consensus.get('consensus_justification', '')}\n"
            f"Confidence: {blind_consensus.get('confidence', 0.5)}"
        )

        aware_summary = (
            f"Pass Type: Aware Audit (With claim info)\n"
            f"Detected Part: {aware_consensus.get('primary_part', 'unknown')}\n"
            f"Detected Damage: {aware_consensus.get('primary_damage', 'unknown')}\n"
            f"Detected Severity: {aware_consensus.get('primary_severity', 'unknown')}\n"
            f"Justification: {aware_consensus.get('consensus_justification', '')}\n"
            f"Confidence: {aware_consensus.get('confidence', 0.5)}"
        )

        passes = [("Pass A", blind_summary), ("Pass B", aware_summary)]
        # Deterministic shuffle using hash of image paths/user_id
        seed_str = "".join(image_paths) + user_id
        seed = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16) % 10000
        rng = random.Random(seed)
        rng.shuffle(passes)

        pass_1_label, pass_1_text = passes[0]
        pass_2_label, pass_2_text = passes[1]

        # Checklist format if requirements exist
        checklist_instruction = ""
        checklist_schema = ""
        if matched_reqs:
            checklist_items = []
            schema_items = []
            for req in matched_reqs:
                req_id = req.get("requirement_id", "REQ_UNKNOWN")
                min_evidence = req.get("minimum_image_evidence", "")
                checklist_items.append(f"- [{req_id}]: {min_evidence}")
                schema_items.append(f'"{req_id}": true/false')
            
            checklist_instruction = "\nAdditionally, verify if the images satisfy these evidence checklist requirements:\n" + "\n".join(checklist_items)
            checklist_schema = ',\n  "requirements_met": {\n    ' + ",\n    ".join(schema_items) + '\n  }'

        prompt = f"""
You are a senior forensic claims reconciler. Your job is to resolve discrepancies between two prior audit passes of a claim.
The claim is for a {claim_object} with:
- Claimed Part: {claimed_part}
- Claimed Damage: {claimed_damage}
- Stated Severity: {stated_severity}

Below are the summaries of the two prior audit runs:

---
### {pass_1_label} Findings:
{pass_1_text}

---
### {pass_2_label} Findings:
{pass_2_text}

---

Perform your audit in 3 strict stages:
Stage 1: Raw Visual Read. List all visible parts, physical damage, and severity observed in the images, completely ignoring the prior passes.
Stage 2: Prior Pass Review. Analyze why {pass_1_label} and {pass_2_label} might differ or have low confidence. Note any potential anchoring risk (where a pass might have just repeated the user's claim instead of grounding in visual reality).
Stage 3: Reconciliation Synthesis. Formulate a final, unified consensus that is visually grounded.

CRITICAL INSTRUCTION: Ignore all red/blue/black drawing annotations, circles, or arrows. Do not classify annotations as physical damage.
Do NOT flag 'wrong_object' or model mismatch simply because one image is a close-up of a bumper/panel and another shows the full vehicle. Close-up photos lack model-identifying features (logos, grilles) and may look like a different model to you. Only flag 'wrong_object' or model mismatch if there is clear, undeniable contradiction (e.g. different vehicle colors, different body types like pickup vs sedan, or completely different brand logos).
For laptop claims, note that many laptops have different colors and materials on different parts, such as a silver aluminum outer lid/body but black/grey plastic inner screen bezels, keys, or hinge covers. Do NOT flag 'wrong_object' or model mismatch due to these color or material differences between the inner keyboard/screen view and the outer lid view.
If any image in the set is blurry or low quality, do NOT use it to flag 'wrong_object' or model mismatch as fine structural features are distorted.
Do NOT flag 'non_original_image' for standard photos taken on a mobile phone, even if they have minor reflections, glare, or are close-ups. Only flag it if there is an explicit watermarked logo like Alamy, Getty, or Shutterstock.
For 'evidence_standard_met', report true if the images are clear enough to inspect the physical attributes (even if you suspect a stock photo, watermark, or wrong object), so that the claim can be evaluated and decided. Report false ONLY if the images are uninspectable due to extreme blurriness, darkness, or obstruction.
Reconcile any disagreement between the prior passes based strictly on the visual evidence. Do not bias towards the user's claimed damage or either of the passes; identify the true underlying physical damage and severity objectively from the images.

Allowed parts: {allowed_parts}
Allowed damages: {sorted(list(ALLOWED_ISSUE_TYPES))}
Allowed severities: {sorted(list(ALLOWED_SEVERITIES))}
Allowed risk flags: {sorted(list(ALLOWED_RISK_FLAGS))}
{checklist_instruction}

Respond ONLY with a JSON object. Do not wrap in markdown code blocks:
{{
  "reasoning_trace": [
    "Stage 1 analysis...",
    "Stage 2 analysis...",
    "Stage 3 reconciliation..."
  ],
  "resolved_part": "one of the allowed parts",
  "resolved_damage": "one of the allowed damage types",
  "resolved_severity": "none, low, medium, high, or unknown",
  "confidence": 0.0-1.0,
  "resolution_status": "auto_resolved | unresolved_escalate",
  "evidence_standard_met": "true | false",
  "evidence_standard_met_reason": "grounded visual justification",
  "risk_flags": ["list of flags, or none"]{checklist_schema}
}}
"""
        # Execute VLM call with single retry logic
        try:
            res_text = self.client.call_vlm_model(prompt, resolved_paths)
            result = self._parse_and_validate(res_text, allowed_parts, matched_reqs)
            if result:
                return result
            
            # If validation failed, attempt one self-correction retry
            logger.warning("Reconciler JSON schema validation failed. Retrying with feedback...")
            retry_prompt = prompt + f"\n\nWARNING: Your previous response was invalid. Please ensure all values match the exact taxonomies. Do not include markdown wraps."
            retry_res = self.client.call_vlm_model(retry_prompt, resolved_paths)
            result = self._parse_and_validate(retry_res, allowed_parts, matched_reqs)
            if result:
                return result
            
        except Exception as e:
            logger.error(f"Reconciler VLM call failed: {e}")

        # Final fallback on failure
        return self._make_fallback(claim_object, claimed_part, matched_reqs)

    def _parse_and_validate(self, text: str, allowed_parts: list[str], matched_reqs: list[dict[str, str]] | None) -> dict[str, object] | None:
        try:
            cleaned = self._clean_json_string(text)
            data = json.loads(cleaned)

            part = str(data.get("resolved_part", "unknown")).lower().strip().replace(" ", "_")
            dmg = str(data.get("resolved_damage", "unknown")).lower().strip().replace(" ", "_")
            sev = str(data.get("resolved_severity", "unknown")).lower().strip().replace(" ", "_")
            conf = float(data.get("confidence", 0.5))
            status = str(data.get("resolution_status", "auto_resolved")).lower().strip()
            ev_std = str(data.get("evidence_standard_met", "true")).lower().strip()
            ev_std_reason = str(data.get("evidence_standard_met_reason", ""))
            risks = [str(r).lower().strip() for r in data.get("risk_flags", [])]
            trace = [str(t) for t in data.get("reasoning_trace", [])]

            # Validate Taxonomies
            if part not in allowed_parts:
                return None
            if dmg not in ALLOWED_ISSUE_TYPES:
                return None
            if sev not in ALLOWED_SEVERITIES:
                return None
            if status not in ("auto_resolved", "unresolved_escalate"):
                return None
            
            # Map valid/invalid risks
            valid_risks = [r for r in risks if r in ALLOWED_RISK_FLAGS]

            # Parse checklist requirements
            requirements_met = {}
            if matched_reqs:
                reqs_raw = data.get("requirements_met", {})
                for req in matched_reqs:
                    req_id = req.get("requirement_id", "REQ_UNKNOWN")
                    val = reqs_raw.get(req_id, True)
                    if isinstance(val, str):
                        requirements_met[req_id] = val.lower() in ("true", "yes", "1")
                    else:
                        requirements_met[req_id] = bool(val)

            return {
                "valid_call": True,
                "resolved_part": part,
                "resolved_damage": dmg,
                "resolved_severity": sev,
                "confidence": conf,
                "resolution_status": status,
                "evidence_standard_met": "true" if ev_std in ("true", "1", "yes") else "false",
                "evidence_standard_met_reason": ev_std_reason,
                "risk_flags": valid_risks,
                "requirements_met": requirements_met,
                "reasoning_trace": trace
            }
        except Exception as e:
            logger.debug(f"JSON validation parser error: {e}")
            return None

    def _clean_json_string(self, text: str) -> str:
        try:
            start = text.find('{')
            if start != -1:
                obj, _ = json.JSONDecoder().raw_decode(text[start:])
                return json.dumps(obj)
        except Exception:
            pass
        return text.strip()

    def _make_fallback(self, claim_object: str, claimed_part: str, matched_reqs: list[dict[str, str]] | None) -> dict[str, object]:
        fallback_reqs = {}
        if matched_reqs:
            for req in matched_reqs:
                fallback_reqs[req.get("requirement_id", "REQ_UNKNOWN")] = False

        return {
            "valid_call": False,
            "resolved_part": claimed_part,
            "resolved_damage": "unknown",
            "resolved_severity": "unknown",
            "confidence": 0.0,
            "resolution_status": "unresolved_escalate",
            "evidence_standard_met": "false",
            "evidence_standard_met_reason": "Reconciler failed to resolve discrepancies.",
            "risk_flags": ["manual_review_required"],
            "requirements_met": fallback_reqs,
            "reasoning_trace": ["Reconciler execution failed, triggered fallback escalation."]
        }
