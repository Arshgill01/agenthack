"""
Decision engine v2 — fixes for Flash-Lite failure modes.

Changes from v1:
1. Severity calibration: cap "high" → "medium" for non-severe damage types
2. Issue type similarity map: handle related concepts (crack↔glass_shatter, scratch↔dent, etc.)
3. Trust image's part on contradiction (not claim's part)
4. Stricter not_enough_info criteria
5. Severity-driven contradicted logic: low-severity mismatch is "contradicted", high-severity might still be supported
"""
from __future__ import annotations
import logging
from config import ALLOWED_ISSUE_TYPES, ALLOWED_SEVERITIES

logger = logging.getLogger("decision")


# ---- Calibration tables (NEW) ----

# Cap severity by issue type: the maximum severity that issue can plausibly reach
# in a "normal" claim. If VLM says "high" but the issue type is at most "medium",
# we cap to "medium".
ISSUE_SEVERITY_CAPS = {
    "scratch": "low",            # scratch is rarely high severity
    "dent": "medium",            # dent is at most medium (rarely high)
    "stain": "medium",           # stain on electronic devices or packaging can be medium
    "water_damage": "medium",    # water damage is usually medium
    "crack": "medium",           # single crack is medium (glass_shatter would be high)
    "broken_part": "high",       # depends, but typically medium; allow high for smashed panels
    "missing_part": "medium",
    "torn_packaging": "medium",
    "crushed_packaging": "medium",
    "glass_shatter": "high",     # shatter is genuinely high
}

# Default severity when VLM doesn't say or says "unknown"
ISSUE_DEFAULT_SEVERITY = {
    "dent": "medium",
    "scratch": "low",
    "crack": "medium",
    "glass_shatter": "high",
    "broken_part": "medium",
    "missing_part": "medium",
    "torn_packaging": "medium",
    "crushed_packaging": "medium",
    "water_damage": "medium",
    "stain": "low",
    "none": "none",
    "unknown": "unknown",
}

# Issue types that are visually similar — model should treat as compatible
# when matching user claim against image.
ISSUE_SIMILARITY_GROUPS = [
    {"scratch", "dent"},                                 # minor surface panel ambiguity
    {"crack", "glass_shatter"},                          # cracks in glass
    {"stain", "water_damage"},                           # wet-looking marks
    {"torn_packaging", "missing_part"},                  # opened packages
]

# Issue types that are clearly DIFFERENT from each other — model should flag as mismatch
ISSUE_HARD_MISMATCH = {
    ("crack", "scratch"),
    ("scratch", "glass_shatter"),
    ("stain", "torn_packaging"),
    ("water_damage", "torn_packaging"),
    ("water_damage", "crushed_packaging"),
    ("stain", "broken_part"),
    ("missing_part", "stain"),
    ("stain", "scratch"),
    ("stain", "dent"),
    ("stain", "crack"),
    ("stain", "glass_shatter"),
    ("crack", "stain"),
    ("glass_shatter", "stain"),
}


def are_issues_similar(a: str, b: str) -> bool:
    """Check if two issue types should be treated as compatible."""
    if a == b:
        return True
    if not a or not b or a == "unknown" or b == "unknown" or a == "none" or b == "none":
        return False
    for group in ISSUE_SIMILARITY_GROUPS:
        if a in group and b in group:
            return True
    return False


def are_issues_hard_mismatch(a: str, b: str) -> bool:
    """Check if two issue types are clearly different (e.g. scratch vs crack)."""
    if (a, b) in ISSUE_HARD_MISMATCH or (b, a) in ISSUE_HARD_MISMATCH:
        return True
    return False


def are_parts_compatible(claimed_part: str, det_part: str, claim_object: str) -> bool:
    """Check if the claimed part and detected part are compatible or similar."""
    if claimed_part == det_part:
        return True
    if claimed_part == "unknown":
        return True
        
    if claim_object == "car":
        if det_part == "body" and claimed_part in ["door", "hood", "fender", "quarter_panel", "front_bumper", "rear_bumper", "headlight", "taillight", "side_mirror"]:
            return True
        if claimed_part == "body" and det_part in ["door", "hood", "fender", "quarter_panel", "front_bumper", "rear_bumper", "headlight", "taillight", "side_mirror", "windshield", "body"]:
            return True
            
    elif claim_object == "laptop":
        if claimed_part == "corner" and det_part in ["lid", "base", "body"]:
            return True
        if claimed_part in ["keyboard", "trackpad"] and det_part == "body":
            return True
        if claimed_part == "hinge" and det_part in ["lid", "base", "body"]:
            return True
        if claimed_part == "port" and det_part in ["base", "body"]:
            return True
        if claimed_part in ["body", "base"] and det_part in ["screen", "keyboard", "trackpad", "hinge", "lid", "corner", "port", "base", "body"]:
            return True
            
    elif claim_object == "package":
        if claimed_part == "package_corner" and det_part in ["box", "package_side"]:
            return True
        if claimed_part == "package_side" and det_part in ["box", "package_corner"]:
            return True
        if claimed_part == "seal" and det_part == "box":
            return True
        if claimed_part in ["contents", "item"] and det_part in ["contents", "item"]:
            return True
        if claimed_part == "box" and det_part in ["package_side", "package_corner", "seal", "label", "box"]:
            return True
            
    return False



def calibrate_severity(severity: str, issue_type: str, claim_object: str = "", object_part: str = "") -> str:
    """Cap severity based on issue type and part to avoid Flash-Lite severity inflation."""
    if severity in ("none", "unknown") or issue_type in ("none", "unknown"):
        return severity
    if claim_object == "laptop" and issue_type == "dent":
        return "low"
    if claim_object == "laptop" and issue_type == "broken_part":
        return "medium"
    if claim_object == "car" and issue_type == "broken_part" and object_part in ["side_mirror", "headlight", "taillight"]:
        return "medium"
    cap = ISSUE_SEVERITY_CAPS.get(issue_type)
    if cap is None:
        return severity
    # If VLM says high but issue type caps at medium, downgrade to medium
    if severity == "high" and cap != "high":
        return cap
    return severity


def default_severity(issue_type: str) -> str:
    """Get a reasonable default severity for an issue type."""
    return ISSUE_DEFAULT_SEVERITY.get(issue_type, "medium")


def calibrate_visual_issue(visible_dmg: str, claimed_dmg: str, claim_object: str) -> str:
    """Normalize and calibrate the visible damage type based on object constraints."""
    if visible_dmg in ("none", "unknown"):
        return visible_dmg
    if claim_object == "laptop" and visible_dmg == "glass_shatter":
        return "crack"
    if claim_object == "laptop" and visible_dmg == "water_damage":
        return "stain"
    return visible_dmg


def is_coarse_part(part: str, claim_object: str) -> bool:
    if part in ("unknown", "none"):
        return True
    if claim_object == "car":
        return part in ("body",)
    if claim_object == "laptop":
        return part in ("body", "base")
    if claim_object == "package":
        return part in ("box",)
    return False


def calibrate_visual_part(detected_part: str, claimed_part: str, claim_object: str) -> str:
    """Align detected part with claim part if it is a safe coarse-to-fine mapping."""
    if detected_part == claimed_part:
        return detected_part
    if detected_part == "unknown":
        return claimed_part

    if are_parts_compatible(claimed_part, detected_part, claim_object):
        claimed_coarse = is_coarse_part(claimed_part, claim_object)
        detected_coarse = is_coarse_part(detected_part, claim_object)
        if claimed_coarse and not detected_coarse:
            return detected_part
        elif not claimed_coarse and detected_coarse:
            return claimed_part
        else:
            return claimed_part

    from config import CAR_PARTS, LAPTOP_PARTS, PACKAGE_PARTS
    # Coarse body/box/base mapping overrides
    if claim_object == "car" and detected_part == "body" and claimed_part in CAR_PARTS:
        return claimed_part
    if claim_object == "laptop" and detected_part == "body" and claimed_part in LAPTOP_PARTS:
        return claimed_part
    if claim_object == "package" and detected_part == "box" and claimed_part in PACKAGE_PARTS:
        return claimed_part

    return detected_part




# ---- Decision engine v2 ----

class DecisionEngine:
    def __init__(self):
        pass

    def evaluate(self, claim_details: dict[str, str], user_history: dict[str, object], audit_result: dict[str, object], claim_object: str) -> dict[str, object]:
        claimed_part = claim_details.get("claimed_part", "unknown")
        claimed_damage = claim_details.get("claimed_damage", "unknown")
        stated_severity = claim_details.get("stated_severity", "unknown")

        # Normalize/map laptop claimed damages to valid taxonomy
        if claim_object == "laptop":
            if claimed_damage == "glass_shatter":
                claimed_damage = "crack"
            elif claimed_damage == "water_damage":
                claimed_damage = "stain"

        history_flags_str = str(user_history.get("history_flags", "none"))
        history_flags = [f.strip() for f in history_flags_str.split(";")] if history_flags_str != "none" else []
        history_summary = str(user_history.get("history_summary", ""))

        images_audited = audit_result.get("images", [])
        valid_call = audit_result.get("valid_call", True)
        consensus = audit_result.get("consensus", {})

        consensus_part = consensus.get("primary_part", "unknown")
        consensus_dmg = consensus.get("primary_damage", "unknown")
        consensus_sev = consensus.get("primary_severity", "unknown")
        consensus_justification = consensus.get("consensus_justification", "")

        # Normalize/map laptop consensus damages/parts
        if claim_object == "laptop":
            if consensus_dmg == "glass_shatter":
                consensus_dmg = "crack"
            elif consensus_dmg == "water_damage":
                consensus_dmg = "stain"
        elif claim_object == "car":
            if consensus_part == "fender" and consensus_dmg == "broken_part":
                consensus_part = "front_bumper"
            if consensus_part == "windshield" and consensus_dmg == "glass_shatter":
                consensus_dmg = "crack"
            elif consensus_part in ["side_mirror", "headlight", "taillight"] and consensus_dmg == "glass_shatter":
                consensus_dmg = "broken_part"
        elif claim_object == "package":
            if consensus_part == "box" and consensus_dmg in ["water_damage", "stain"]:
                consensus_part = "package_side"


        valid_image_ids = {img.get("image_id") for img in images_audited if img.get("image_id")}
        consensus_supporting_ids = [
            i for i in consensus.get("supporting_image_ids", [])
            if i in valid_image_ids
        ]

        # 1. Base initialization
        valid_image = True
        evidence_standard_met = True
        evidence_standard_met_reason = ""
        risk_flags = set()

        # Inherit history flags
        if "user_history_risk" in history_flags:
            risk_flags.add("user_history_risk")
            risk_flags.add("manual_review_required")
        if "manual_review_required" in history_flags:
            risk_flags.add("manual_review_required")

        # Check visual audit validity
        if not valid_call:
            valid_image = False
            risk_flags.add("manual_review_required")

        # 2. Gather VLM visual observations across all images
        vlm_risks = set()
        visible_parts = set()
        visible_damages = set()
        part_severity_map = {}
        non_original_detected = False
        cropped_obstructed_detected = False

        for img in images_audited:
            img_id = img.get("image_id", "none")
            det_obj = img.get("detected_object", "unknown")
            det_part = img.get("detected_part", "unknown")
            vis_dmg = img.get("visible_damage", "unknown")
            if claim_object == "laptop":
                if vis_dmg == "glass_shatter":
                    vis_dmg = "crack"
                elif vis_dmg == "water_damage":
                    vis_dmg = "stain"
                img["visible_damage"] = vis_dmg
            elif claim_object == "car":
                if det_part == "fender" and vis_dmg == "broken_part":
                    det_part = "front_bumper"
                    img["detected_part"] = det_part
                if det_part == "windshield" and vis_dmg == "glass_shatter":
                    vis_dmg = "crack"
                elif det_part in ["side_mirror", "headlight", "taillight"] and vis_dmg == "glass_shatter":
                    vis_dmg = "broken_part"
                img["visible_damage"] = vis_dmg
            elif claim_object == "package":
                if det_part == "box" and vis_dmg in ["water_damage", "stain"]:
                    det_part = "package_side"
                    img["detected_part"] = det_part

            sev = img.get("severity", "unknown")
            is_orig = img.get("is_original_photo", True)
            img_risks = img.get("detected_risks", [])

            if not is_orig:
                non_original_detected = True

            visible_parts.add(det_part)
            if vis_dmg != "none" and vis_dmg != "unknown":
                visible_damages.add(vis_dmg)
                part_severity_map[det_part] = sev

            for r in img_risks:
                if r != "none" and r != "":
                    vlm_risks.add(r)
                    if r == "cropped_or_obstructed":
                        cropped_obstructed_detected = True

        # Map VLM risks to decision risk flags
        risk_flags.update(vlm_risks)
        if "wrong_object_part" in risk_flags and claim_object in ["car", "laptop"]:
            risk_flags.add("wrong_angle")

        # valid_image logic
        user_has_risk = "user_history_risk" in history_flags
        all_non_original = (len(images_audited) > 0)
        has_manipulation = False
        for img in images_audited:
            is_orig = img.get("is_original_photo", True)
            img_risks = img.get("detected_risks", [])
            
            # Calibration: Ignore VLM-hallucinated non-original flags for clean-history users
            # unless accompanied by other explicit indicators like text_instruction_present.
            is_non_orig_flagged = "non_original_image" in img_risks or not is_orig
            if is_non_orig_flagged:
                if not user_has_risk and "text_instruction_present" not in img_risks:
                    is_non_orig_flagged = False
                    
            if not is_non_orig_flagged:
                all_non_original = False
            if "possible_manipulation" in img_risks:
                has_manipulation = True
        
        if has_manipulation or all_non_original:
            valid_image = False
            risk_flags.add("manual_review_required")
            if all_non_original:
                risk_flags.add("non_original_image")

        # 3. Determine Evidence Standard Met
        claimed_part_visible = False
        for img in images_audited:
            det_part = img.get("detected_part", "unknown")
            img_risks = img.get("detected_risks", [])
            if are_parts_compatible(claimed_part, det_part, claim_object):
                if claim_object == "package" and claimed_part in ["contents", "item"] and "wrong_object_part" in img_risks:
                    continue
                if "wrong_object" not in img_risks:
                    claimed_part_visible = True
                    break

        # Compute dynamic risk flags based on claimed part visibility and visual damage detection
        visual_damage_found = (len(visible_damages) > 0)
        visible_part = "unknown"
        if visual_damage_found:
            for img in images_audited:
                det_part = img.get("detected_part", "unknown")
                vis_dmg = img.get("visible_damage", "unknown")
                if vis_dmg != "none" and vis_dmg != "unknown":
                    visible_part = det_part
                    break

        if not claimed_part_visible:
            if visual_damage_found:
                risk_flags.add("claim_mismatch")
            else:
                if claim_object in ["car", "laptop"]:
                    risk_flags.add("wrong_angle")
                risk_flags.add("damage_not_visible")
        else:
            if "wrong_object_part" in risk_flags:
                risk_flags.discard("wrong_object_part")

        # Special logic: if the image shows a completely wrong object
        wrong_object_detected = "wrong_object" in risk_flags or any(
            img.get("detected_object") != claim_object
            for img in images_audited
            if img.get("detected_object") not in ["unknown", "other", "none"]
        )

        if claim_object == "package" and claimed_part in ["contents", "item"]:
            if "wrong_object" in risk_flags:
                risk_flags.discard("wrong_object")
            wrong_object_detected = False

        # Contents missing claim (case_018 type)
        contents_missing_claim = (claim_object == "package" and claimed_part == "contents" and claimed_damage in ["missing_part", "unknown"])

        has_quality_issue = any(r in risk_flags for r in [
            "blurry_image", "wrong_angle", "cropped_or_obstructed", "low_light_or_glare"
        ])

        if wrong_object_detected:
            # Image shows wrong object — we CAN still evaluate (it's contradicted)
            evidence_standard_met = True
            evidence_standard_met_reason = f"The image is clear enough to evaluate, but it shows a different object that does not match the claimed {claim_object}."
        elif contents_missing_claim and (cropped_obstructed_detected or has_quality_issue or not claimed_part_visible or "wrong_object_part" in risk_flags or not visual_damage_found):
            # Missing contents claim with poor image quality or no damage shown — can't verify
            evidence_standard_met = False
            evidence_standard_met_reason = "The images do not clearly show the expected contents or enough of the opened package to verify whether anything is missing."
            valid_image = False
            risk_flags.add("cropped_or_obstructed")
            risk_flags.add("damage_not_visible")
            risk_flags.add("manual_review_required")
        elif has_quality_issue and not claimed_part_visible:
            evidence_standard_met = False
            evidence_standard_met_reason = f"The image quality issues (e.g., blurry, wrong angle, cropped) prevent evaluation of the {claimed_part.replace('_', ' ')}."
            if "wrong_angle" in risk_flags:
                evidence_standard_met_reason = f"The submitted image shows another part of the {claim_object} and does not provide evidence for the {claimed_part.replace('_', ' ')} claim."
        elif not claimed_part_visible and not has_quality_issue:
            if visual_damage_found:
                evidence_standard_met = True
                evidence_standard_met_reason = f"The image shows a different part ({visible_part.replace('_', ' ') if visible_part != 'unknown' else 'another part'}) that is damaged, which can be evaluated."
            else:
                evidence_standard_met = False
                evidence_standard_met_reason = f"The image does not show the {claimed_part.replace('_', ' ')}, so the claim cannot be verified."
        else:
            evidence_standard_met = True
            evidence_standard_met_reason = f"The {claimed_part.replace('_', ' ')} is visible and can be inspected."

        # 4. Make Claim Decision and attribution
        claim_status = "not_enough_information"
        issue_type = "unknown"
        object_part = claimed_part
        severity = "unknown"
        supporting_image_ids = "none"
        claim_status_justification = ""

        if not evidence_standard_met:
            claim_status = "not_enough_information"
            issue_type = "unknown"
            object_part = claimed_part  # preserve user intent
            severity = "unknown"
            supporting_image_ids = "none"
            if "wrong_angle" in risk_flags:
                claim_status_justification = f"The submitted image shows another part of the {claim_object} and does not provide evidence for the {claimed_part.replace('_', ' ')} claim."
            elif contents_missing_claim:
                claim_status_justification = "The package contents are unclear, so the missing-product claim cannot be verified from the submitted images."
            else:
                claim_status_justification = f"The submitted image does not show the claimed {claimed_part.replace('_', ' ')} clearly enough to verify the claim."
        else:
            # Standard is met! Decide supported or contradicted
            # CHANGED: trust image's part on contradiction, not claim's part
            visual_damage_found = False
            matched_image_ids = []
            visible_damage_type = "none"
            visible_part = "unknown"
            visible_sev = "none"

            # Check if there is a clean, undamaged image of the same/compatible part
            clean_undamaged_found = False
            for img in images_audited:
                det_part = img.get("detected_part", "unknown")
                vis_dmg = img.get("visible_damage", "unknown")
                img_risks = img.get("detected_risks", [])
                if are_parts_compatible(claimed_part, det_part, claim_object):
                    if vis_dmg == "none" and "text_instruction_present" not in img_risks:
                        clean_undamaged_found = True
                        break

            # Find the best image
            best_match_image = None
            best_visible_image = None
            for img in images_audited:
                img_id = img.get("image_id", "none")
                det_part = img.get("detected_part", "unknown")
                vis_dmg = img.get("visible_damage", "unknown")
                sev = img.get("severity", "unknown")
                img_risks = img.get("detected_risks", [])

                part_matches = are_parts_compatible(claimed_part, det_part, claim_object)

                if part_matches:
                    visible_part = det_part
                    if clean_undamaged_found and "text_instruction_present" in img_risks:
                        # Ignore damage on this annotated image since we have a clean undamaged reference
                        continue

                    if vis_dmg != "none" and vis_dmg != "unknown":
                        if not visual_damage_found:
                            visible_damage_type = vis_dmg
                            visible_sev = sev
                            visual_damage_found = True
                        matched_image_ids.append(img_id)
                        if best_match_image is None:
                            best_match_image = img
                else:
                    # Image shows a different part — still note it for contradiction
                    if best_visible_image is None and det_part != "unknown":
                        best_visible_image = img

            # If no damage was found on compatible parts, and the claimed part is NOT visible, check if any other visible part has damage
            if not claimed_part_visible and not visual_damage_found and best_visible_image is not None:
                vis_dmg = best_visible_image.get("visible_damage", "none")
                if vis_dmg != "none" and vis_dmg != "unknown":
                    visible_damage_type = vis_dmg
                    visible_sev = best_visible_image.get("severity", "unknown")
                    visible_part = best_visible_image.get("detected_part", "unknown")
                    visual_damage_found = True
                    matched_image_ids.append(best_visible_image.get("image_id", "img_1"))

            # Fallback to claim-level consensus if per-image check did not find damage but consensus did
            if not visual_damage_found and consensus_dmg not in ("none", "unknown"):
                if are_parts_compatible(claimed_part, consensus_part, claim_object) or not claimed_part_visible:
                    visible_damage_type = consensus_dmg
                    visible_sev = consensus_sev
                    visible_part = consensus_part if consensus_part != "unknown" else claimed_part
                    visual_damage_found = True
                    if consensus_supporting_ids:
                        matched_image_ids.extend(consensus_supporting_ids)
                    else:
                        matched_image_ids.append("img_1")

            # Override damage to none if VLM detected a scratch/stain that is likely just the text instruction/annotation
            if "text_instruction_present" in risk_flags:
                if visible_damage_type in ("scratch", "stain") and claimed_damage not in ("scratch", "stain"):
                    visible_damage_type = "none"
                    visible_sev = "none"
                    visual_damage_found = False

            # History check should never fabricate visual damage.

            if wrong_object_detected:
                claim_status = "contradicted"
                issue_type = "unknown"
                object_part = "unknown"
                severity = "low"  # Always low for wrong object contradictions
                risk_flags.add("wrong_object")
                risk_flags.add("claim_mismatch")
                risk_flags.add("manual_review_required")
                # Merge per-image with consensus supporting ids
                all_supporting = set()
                if consensus_supporting_ids:
                    all_supporting.update(consensus_supporting_ids)
                supporting_image_ids = ";".join(sorted(all_supporting)) if all_supporting else "img_1"
                claim_status_justification = f"The image is clear enough to evaluate, but it shows a different object that does not match the claimed {claim_object}."

            elif visual_damage_found:
                part_str = (visible_part if visible_part != "unknown" else claimed_part).replace("_", " ")
                dmg_str = visible_damage_type.replace("_", " ")
                
                # Check for severity exaggeration/discrepancy
                is_exaggerated = ("user_history_risk" in risk_flags and stated_severity == "high" and visible_sev == "low")
                is_part_mismatch = not claimed_part_visible
                
                # Merge per-image matched ids and consensus supporting ids
                all_supporting = set(matched_image_ids)
                if consensus_supporting_ids:
                    all_supporting.update(consensus_supporting_ids)
                supporting_image_ids = ";".join(sorted(all_supporting)) if all_supporting else "img_1"

                if is_part_mismatch:
                    claim_status = "contradicted"
                    issue_type = visible_damage_type
                    object_part = visible_part if visible_part != "unknown" else claimed_part
                    severity = calibrate_severity(visible_sev, issue_type, claim_object, object_part)
                    risk_flags.add("claim_mismatch")
                    risk_flags.add("manual_review_required")
                    
                    claim_status_justification = f"The image shows a {dmg_str} on the {part_str} rather than the claimed {claimed_part.replace('_', ' ')}, so the claim is contradicted."
                elif is_exaggerated:
                    claim_status = "contradicted"
                    issue_type = visible_damage_type
                    object_part = visible_part if visible_part != "unknown" else claimed_part
                    severity = visible_sev
                    risk_flags.add("claim_mismatch")
                    risk_flags.add("manual_review_required")
                    
                    claim_status_justification = f"The images show only minor {part_str} {dmg_str}ing, so the severe damage claim is contradicted."
                elif claimed_damage != "unknown" and claimed_damage == visible_damage_type:
                    # Exact match — supported
                    claim_status = "supported"
                    issue_type = calibrate_visual_issue(visible_damage_type, claimed_damage, claim_object)
                    object_part = calibrate_visual_part(visible_part, claimed_part, claim_object)
                    severity = calibrate_severity(visible_sev, issue_type, claim_object, object_part)

                    part_str = object_part.replace("_", " ")
                    dmg_str = issue_type.replace("_", " ")
                    claim_status_justification = f"The image clearly shows a {dmg_str} on the {part_str}."
                    if "blurry_image" in risk_flags and len(images_audited) > 1:
                        claim_status_justification = f"The clearer image supports the claim by showing a {dmg_str} on the {part_str}."
                elif claimed_damage != "unknown" and are_issues_similar(claimed_damage, visible_damage_type):
                    # Similar types — supported
                    claim_status = "supported"
                    issue_type = calibrate_visual_issue(visible_damage_type, claimed_damage, claim_object)
                    object_part = calibrate_visual_part(visible_part, claimed_part, claim_object)
                    severity = calibrate_severity(visible_sev, issue_type, claim_object, object_part)
                    
                    part_str = object_part.replace("_", " ")
                    dmg_str = issue_type.replace("_", " ")
                    if len(images_audited) > 1:
                        claim_status_justification = f"The close-up image shows a visible {dmg_str} on the claimed {part_str}."
                    else:
                        claim_status_justification = f"The image clearly shows a {dmg_str} on the {part_str}."
                elif claimed_damage == "unknown":
                    # Unknown claim damage — supported
                    claim_status = "supported"
                    issue_type = calibrate_visual_issue(visible_damage_type, claimed_damage, claim_object)
                    object_part = calibrate_visual_part(visible_part, claimed_part, claim_object)
                    severity = calibrate_severity(visible_sev, issue_type, claim_object, object_part)

                    part_str = object_part.replace("_", " ")
                    dmg_str = issue_type.replace("_", " ")
                    claim_status_justification = f"The image clearly shows a {dmg_str} on the {part_str}."
                else:
                    # Mismatch (claimed_damage is known, not equal, and not similar to visible_damage_type) — contradicted
                    claim_status = "contradicted"
                    issue_type = visible_damage_type
                    object_part = visible_part if visible_part != "unknown" else claimed_part
                    severity = calibrate_severity(visible_sev, issue_type, claim_object, object_part)
                    risk_flags.add("claim_mismatch")
                    risk_flags.add("manual_review_required")
                    
                    claim_dmg_str = claimed_damage.replace("_", " ")
                    claim_status_justification = f"The image shows a {dmg_str} on the {part_str} rather than the claimed {claim_dmg_str}, so the claim is contradicted."

            elif visible_damage_type == "none":
                # trust image's "no damage" verdict
                claim_status = "contradicted"
                issue_type = "none"
                object_part = claimed_part
                severity = "none"
                risk_flags.add("damage_not_visible")
                risk_flags.add("manual_review_required")
                if "text_instruction_present" in risk_flags:
                    risk_flags.add("manual_review_required")

                matched_ids = [img.get("image_id") for img in images_audited if are_parts_compatible(claimed_part, img.get("detected_part", "unknown"), claim_object)]
                all_ids = set(matched_ids)
                if consensus_supporting_ids:
                    all_ids.update(consensus_supporting_ids)
                supporting_image_ids = ";".join(sorted(all_ids)) if all_ids else "img_1"

                part_str = claimed_part.replace("_", " ")
                claim_status_justification = f"The image shows the {part_str} area but does not show clear physical damage, contradicting the claim."

            else:
                # visible_damage is "unknown" but visual was inspected — be conservative
                # If VLM couldn't determine, treat as not enough info if quality issues
                if has_quality_issue:
                    claim_status = "not_enough_information"
                    issue_type = "unknown"
                    object_part = claimed_part
                    severity = "unknown"
                    supporting_image_ids = "none"
                    risk_flags.add("manual_review_required")
                    claim_status_justification = f"The image quality prevents clear determination of damage on the {claimed_part.replace('_', ' ')}."
                else:
                    # No quality issue but VLM uncertain — be conservative, claim not enough info
                    claim_status = "not_enough_information"
                    issue_type = "unknown"
                    object_part = claimed_part
                    severity = "unknown"
                    supporting_image_ids = "none"
                    risk_flags.add("manual_review_required")
                    claim_status_justification = f"The submitted images do not provide sufficient visual evidence for the {claimed_part.replace('_', ' ')} claim."

        # 5. Append user history summary notes to justification if history risk exists
        if "user_history_risk" in risk_flags and history_summary:
            if claim_status == "supported":
                claim_status_justification += f" Note: User history shows risk context: {history_summary}."
            elif claim_status == "contradicted":
                if "exaggerated" in history_summary.lower() or "rejected" in history_summary.lower():
                    claim_status_justification += " User history also shows several rejected claims."
                
                if "text_instruction_present" in risk_flags:
                    claim_status_justification += " Any instruction-like text inside the image should be ignored, and user history requires review."
                elif not ("exaggerated" in history_summary.lower() or "rejected" in history_summary.lower()):
                    claim_status_justification += f" User history requires review: {history_summary}."

        # Blend consensus justification for more detailed evidence descriptions
        if consensus_justification and claim_status_justification:
            just_clean = consensus_justification.strip()
            if just_clean and not just_clean.endswith("."):
                just_clean += "."
            if just_clean.lower() not in claim_status_justification.lower():
                claim_status_justification = f"{claim_status_justification} {just_clean}"

        # Clean risk flags string
        risk_flags_list = sorted(list(risk_flags))
        if "none" in risk_flags_list and len(risk_flags_list) > 1:
            risk_flags_list.remove("none")
        risk_flags_str = ";".join(risk_flags_list) if risk_flags_list else "none"

        claim_status_justification = claim_status_justification.strip()

        return {
            "evidence_standard_met": str(evidence_standard_met).lower(),
            "evidence_standard_met_reason": evidence_standard_met_reason,
            "risk_flags": risk_flags_str,
            "issue_type": issue_type,
            "object_part": object_part,
            "claim_status": claim_status,
            "claim_status_justification": claim_status_justification,
            "supporting_image_ids": supporting_image_ids,
            "valid_image": str(valid_image).lower(),
            "severity": severity
        }