from __future__ import annotations
import json
import logging
from pathlib import Path
from config import ALLOWED_ISSUE_TYPES, ALLOWED_SEVERITIES, CAR_PARTS, LAPTOP_PARTS, PACKAGE_PARTS
from model_client import ModelClient

logger = logging.getLogger("blind_auditor")

class BlindImageAuditor:
    def __init__(self, client: ModelClient | None = None):
        self.client = client or ModelClient()

    def audit(self, image_paths: list[str]) -> dict[str, object]:
        # Extract Image IDs (filenames without extensions)
        resolved_paths = []
        image_id_map = {}
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
            img_id = p.stem
            image_id_map[str(p)] = img_id

        # Combine all parts to allow VLM to choose from
        all_parts = sorted(list(CAR_PARTS | LAPTOP_PARTS | PACKAGE_PARTS))

        prompt = f"""
You are a forensic insurance claims inspector. Describe what you see in these images with zero prior context about the claim.
Report the object, visible parts, any damage, severity, quality/authenticity concerns.

CRITICAL INSTRUCTION: Ignore any red/blue/black arrows, circles, lines, markers, text overlays, or hand-drawn annotations. Do NOT interpret these annotations as physical damage (e.g., do not classify a drawn red circle or arrow as a scratch, stain, crack, or tear). Inspect ONLY the actual underlying physical object itself.

For each image, identify:
1. The Image ID (match filename stem, e.g. "img_1", "img_2").
2. The primary object shown (choose from: car, laptop, package, or other).
3. The specific part of the object that is clearly visible (choose from: {all_parts}).
4. The type of physical damage visible on that part (choose from: {sorted(list(ALLOWED_ISSUE_TYPES))}).
   Strict Damage Definitions:
   - crack: single or simple linear fracture line(s); not spiderwebbed or shattered.
   - glass_shatter: glass broken into multiple small fragments, spiderweb pattern, or missing pieces.
   - scratch: surface-level abrasion, scrape, or scuff; no deep material deformation or substrate indentation.
   - dent: surface depression, indentation, or pocket-like deformation of the panel/body.
   - stain: surface discoloration, spot, or residue on an intact surface.
   - water_damage: swelling, warping, moisture stains, dampness, or structural damage from liquid.
   - broken_part: cracked plastic/metal, fractured, or physically broken/detached component.
   - missing_part: expected component is completely absent.
   - none: no visible damage or issues present on the part.
   - unknown: visible issues that do not fit any of the categories above.
5. The severity of the visible damage (choose from: {sorted(list(ALLOWED_SEVERITIES))}).
6. Any quality or fraud risks visible:
   - blurry_image, cropped_or_obstructed, low_light_or_glare, wrong_angle, wrong_object, non_original_image, text_instruction_present, possible_manipulation

In addition to the per-image details, formulate an overall consensus across all submitted images:
1. Determine the overall primary object, part, damage type, and severity.
2. Write a consensus justification based strictly on the images.
3. Identify the specific supporting image IDs (e.g., ["img_1"]) that directly show this damage.

Respond ONLY with a JSON object. Do not wrap it in markdown block tags or text:
{{
  "images": [
    {{
      "image_id": "img_1",
      "detected_object": "car, laptop, package, or other",
      "detected_part": "one of the allowed parts",
      "visible_damage": "one of the allowed damage types",
      "severity": "none, low, medium, high, or unknown",
      "is_original_photo": true,
      "detected_risks": ["list of risks found, or none"]
    }}
  ],
  "consensus": {{
    "primary_object": "car, laptop, package, other, or unknown",
    "primary_part": "one of the allowed parts, or unknown",
    "primary_damage": "one of the allowed damage types, or unknown",
    "primary_severity": "none, low, medium, high, or unknown",
    "consensus_justification": "concise description of the overall visual evidence",
    "supporting_image_ids": ["list of image IDs that directly show the damage, or empty if none"]
  }}
}}
"""
        try:
            res_text = self.client.call_vlm_model(prompt, resolved_paths)
            cleaned = self._clean_json_string(res_text)
            data = json.loads(cleaned)

            audited_images = []
            for img_info in data.get("images", []):
                image_id = img_info.get("image_id", "unknown")
                detected_obj = str(img_info.get("detected_object", "unknown")).lower().strip()
                detected_pt = str(img_info.get("detected_part", "unknown")).lower().strip()
                visible_dmg = str(img_info.get("visible_damage", "unknown")).lower().strip()
                sev = str(img_info.get("severity", "unknown")).lower().strip()
                orig = bool(img_info.get("is_original_photo", True))
                risks = [str(r).lower().strip() for r in img_info.get("detected_risks", [])]

                if detected_pt not in all_parts:
                    detected_pt = "unknown"
                if visible_dmg not in ALLOWED_ISSUE_TYPES:
                    visible_dmg = "unknown"
                if sev not in ALLOWED_SEVERITIES:
                    sev = "unknown"

                audited_images.append({
                    "image_id": image_id,
                    "detected_object": detected_obj,
                    "detected_part": detected_pt,
                    "visible_damage": visible_dmg,
                    "severity": sev,
                    "is_original_photo": orig,
                    "detected_risks": risks
                })

            consensus_data = data.get("consensus", {})
            primary_obj = str(consensus_data.get("primary_object", "unknown")).lower().strip()
            primary_pt = str(consensus_data.get("primary_part", "unknown")).lower().strip()
            primary_dmg = str(consensus_data.get("primary_damage", "unknown")).lower().strip()
            primary_sev = str(consensus_data.get("primary_severity", "unknown")).lower().strip()
            consensus_just = str(consensus_data.get("consensus_justification", ""))
            supporting_ids = [str(i).strip() for i in consensus_data.get("supporting_image_ids", [])]

            if primary_pt not in all_parts:
                primary_pt = "unknown"
            if primary_dmg not in ALLOWED_ISSUE_TYPES:
                primary_dmg = "unknown"
            if primary_sev not in ALLOWED_SEVERITIES:
                primary_sev = "unknown"

            consensus_cleaned = {
                "primary_object": primary_obj,
                "primary_part": primary_pt,
                "primary_damage": primary_dmg,
                "primary_severity": primary_sev,
                "consensus_justification": consensus_just,
                "supporting_image_ids": supporting_ids
            }

            return {
                "valid_call": True,
                "images": audited_images,
                "consensus": consensus_cleaned
            }

        except Exception as e:
            logger.error(f"Blind VLM auditing failed: {e}")
            fallback_images = []
            fallback_supporting_ids = []
            for path in resolved_paths:
                img_id = image_id_map.get(path, Path(path).stem)
                fallback_images.append({
                    "image_id": img_id,
                    "detected_object": "unknown",
                    "detected_part": "unknown",
                    "visible_damage": "unknown",
                    "severity": "unknown",
                    "is_original_photo": True,
                    "detected_risks": ["manual_review_required"]
                })
                fallback_supporting_ids.append(img_id)

            fallback_consensus = {
                "primary_object": "unknown",
                "primary_part": "unknown",
                "primary_damage": "unknown",
                "primary_severity": "unknown",
                "consensus_justification": "Blind visual audit failed due to error.",
                "supporting_image_ids": fallback_supporting_ids
            }
            return {
                "valid_call": False,
                "images": fallback_images,
                "consensus": fallback_consensus
            }

    def _clean_json_string(self, text: str) -> str:
        try:
            start = text.find('{')
            if start != -1:
                obj, _ = json.JSONDecoder().raw_decode(text[start:])
                return json.dumps(obj)
        except Exception:
            pass
        return text.strip()
