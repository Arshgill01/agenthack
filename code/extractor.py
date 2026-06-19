from __future__ import annotations
import json
import re
import logging
from config import OBJECT_PARTS_MAP, ALLOWED_ISSUE_TYPES, ALLOWED_SEVERITIES
from model_client import ModelClient

logger = logging.getLogger("extractor")

class ClaimExtractor:
    def __init__(self, client: ModelClient | None = None):
        self.client = client or ModelClient()

    def extract(self, user_claim: str, claim_object: str) -> dict[str, str]:
        # Formulate prompt
        allowed_parts = sorted(list(OBJECT_PARTS_MAP.get(claim_object, {"unknown"})))
        allowed_damages = sorted(list(ALLOWED_ISSUE_TYPES))
        allowed_severities = sorted(list(ALLOWED_SEVERITIES))

        prompt = f"""
You are an expert claims processor. Analyze this conversation transcript between a customer and a support agent to identify:
1. The specific part of the {claim_object} they claim is damaged.
2. The primary type of damage they are reporting.
3. The severity stated or implied by the customer (low, medium, high, or unknown).

Object: {claim_object}
Allowed Parts for this object: {allowed_parts}
Allowed Damage Types: {allowed_damages}
Allowed Severities: {allowed_severities}

Conversation Transcript:
"{user_claim}"

Respond ONLY with a valid JSON object matching this schema. Do not write markdown blocks or text around the JSON:
{{
  "claimed_part": "one of the allowed parts, or unknown",
  "claimed_damage": "one of the allowed damage types, or unknown",
  "stated_severity": "one of the allowed severities"
}}
"""
        # Try LLM
        try:
            res_text = self.client.call_text_model(
                prompt=prompt,
                system_instruction="Extract damage claim parameters as strict JSON. Never write anything other than JSON."
            )
            # Parse JSON
            cleaned = self._clean_json_string(res_text)
            data = json.loads(cleaned)
            
            # Normalize fields to allowed values
            part = str(data.get("claimed_part", "unknown")).lower().strip().replace(" ", "_")
            damage = str(data.get("claimed_damage", "unknown")).lower().strip().replace(" ", "_")
            severity = str(data.get("stated_severity", "unknown")).lower().strip()

            if part not in allowed_parts:
                part = "unknown"
            if damage not in allowed_damages:
                damage = "unknown"
            if severity not in allowed_severities:
                severity = "unknown"

            return {
                "claimed_part": part,
                "claimed_damage": damage,
                "stated_severity": severity
            }

        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback keyword matcher: {e}")
            return self._fallback_extract(user_claim, claim_object)

    def _clean_json_string(self, text: str) -> str:
        try:
            start = text.find('{')
            if start != -1:
                obj, _ = json.JSONDecoder().raw_decode(text[start:])
                return json.dumps(obj)
        except Exception:
            pass
        return text.strip()

    def _fallback_extract(self, user_claim: str, claim_object: str) -> dict[str, str]:
        text = user_claim.lower()
        part = "unknown"
        damage = "unknown"
        severity = "medium" # default fallback

        # 1. Stated Severity Heuristic
        if any(w in text for w in ["completely shattered", "destroyed", "very bad", "badly crushed", "severe", "totally"]):
            severity = "high"
        elif any(w in text for w in ["scratch", "scrape", "minor", "small mark", "light"]):
            severity = "low"

        # 2. Heuristics based on object type
        if claim_object == "car":
            # Part Identification
            if "rear bumper" in text or "back bumper" in text or "bumper ke piche" in text:
                part = "rear_bumper"
            elif "front bumper" in text or "bumper ke upar" in text or "front side" in text:
                part = "front_bumper"
            elif "bumper" in text:
                if "back" in text or "behind" in text:
                    part = "rear_bumper"
                else:
                    part = "front_bumper"
            elif "windshield" in text or "front glass" in text or "glass" in text:
                part = "windshield"
            elif "mirror" in text or "side mirror" in text:
                part = "side_mirror"
            elif "door" in text:
                part = "door"
            elif "hood" in text:
                part = "hood"
            elif "headlight" in text or "left headlight" in text or "right headlight" in text:
                part = "headlight"
            elif "taillight" in text:
                part = "taillight"
            elif "fender" in text:
                part = "fender"
            elif "quarter panel" in text:
                part = "quarter_panel"
            else:
                part = "body"

            # Damage Identification
            if "dent" in text or "bump" in text:
                damage = "dent"
            elif "scratch" in text or "scrape" in text or "mark" in text or "line" in text:
                damage = "scratch"
            elif "shatter" in text or "crushed" in text or "broken" in text:
                if "glass" in text or "windshield" in text or "headlight" in text:
                    damage = "glass_shatter"
                else:
                    damage = "broken_part"
            elif "crack" in text:
                damage = "crack"
            elif "missing" in text or "stolen" in text:
                damage = "missing_part"

        elif claim_object == "laptop":
            # Part Identification
            if "screen" in text or "display" in text or "glass" in text:
                part = "screen"
            elif "keyboard" in text or "keys" in text or "spilled" in text:
                part = "keyboard"
            elif "trackpad" in text or "touchpad" in text:
                part = "trackpad"
            elif "hinge" in text or "open" in text:
                part = "hinge"
            elif "lid" in text or "top" in text:
                part = "lid"
            elif "corner" in text:
                part = "corner"
            elif "port" in text or "usb" in text or "charge" in text:
                part = "port"
            elif "base" in text or "bottom" in text:
                part = "base"
            else:
                part = "body"

            # Damage Identification
            if "crack" in text or "shatter" in text:
                damage = "crack"
            elif "dent" in text:
                damage = "dent"
            elif "scratch" in text:
                damage = "scratch"
            elif "spill" in text or "water" in text or "liquid" in text:
                damage = "water_damage"
            elif "stain" in text:
                damage = "stain"
            elif "broken" in text:
                damage = "broken_part"
            elif "missing" in text:
                damage = "missing_part"

        elif claim_object == "package":
            # Part Identification
            if "contents" in text or "item" in text or "inside" in text or "product" in text or "was not inside" in text:
                part = "contents"
            elif "corner" in text:
                part = "package_corner"
            elif "side" in text:
                part = "package_side"
            elif "seal" in text or "tape" in text:
                part = "seal"
            elif "label" in text or "address" in text:
                part = "label"
            else:
                part = "box"

            # Damage Identification
            if "crush" in text or "press" in text or "bent" in text:
                damage = "crushed_packaging"
            elif "tear" in text or "torn" in text or "open" in text or "ripped" in text:
                damage = "torn_packaging"
            elif "water" in text or "wet" in text or "rain" in text:
                damage = "water_damage"
            elif "stain" in text:
                damage = "stain"
            elif "missing" in text or "empty" in text or "stolen" in text:
                damage = "missing_part"

        return {
            "claimed_part": part,
            "claimed_damage": damage,
            "stated_severity": severity
        }
