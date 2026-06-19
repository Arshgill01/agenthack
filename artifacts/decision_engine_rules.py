"""
Pass 5 — Decision engine rules reference. This is NOT executable code yet,
just the formal spec for how Stage 4 should aggregate visual + textual findings.

Pseudocode shown for each rule. Will be translated to Python in implementation phase.
"""

# ============================================================
# INPUT: per-image VLM findings + per-row text extraction + user history
# ============================================================

# per_image_findings = [
#   {
#     "image_id": "img_1",
#     "object": "car" | "laptop" | "package" | "other",
#     "part": <part>,
#     "damage_visible": <issue_type> | "none" | "unknown",
#     "damage_magnitude": "low" | "medium" | "high" | "unknown" | None,
#     "quality_issues": [...],
#     "is_original_photo": bool,
#     "has_text_instruction": bool,
#     "confidence": "low" | "medium" | "high",
#   },
#   ...
# ]

# text_extraction = {
#   "claimed_part": <part> | "unknown",
#   "claimed_damage": <issue_type> | "unknown",
#   "claimed_severity_words": "low" | "medium" | "high" | None,
#   "multi_part": bool,
#   "is_injection": bool,
#   "language": "en" | "romanized_hindi" | "romanized_spanish" | "romanized_chinese",
# }

# user_history = {
#   "history_flags": "none" | "user_history_risk" | "manual_review_required",
#   "past_claim_count": int,
#   "rejected_claim": int,
#   "last_90_days_claim_count": int,
#   "history_summary": str,
# }

# ============================================================
# STEP 1: Filter out low-quality images from consideration
# ============================================================
# usable_images = [img for img in per_image_findings
#                  if img["confidence"] != "low"
#                 ]
# If empty: all images unusable → evidence_standard_met=false, valid_image=false

# ============================================================
# STEP 2: Determine "best" image (highest confidence + cleanest)
# ============================================================
# score_image(img):
#   s = 0
#   s += {"high": 3, "medium": 2, "low": 1}[img["confidence"]]
#   s -= len(img["quality_issues"])  # quality issues reduce score
#   s += 2 if img["is_original_photo"] else -3  # non-original is a strong negative
#   return s
#
# best_image = max(usable_images, key=score_image) if usable_images else None

# ============================================================
# STEP 3: Build aggregate visual finding from best image
# ============================================================
# aggregate = {
#   "object": best_image["object"] if best_image else "unknown",
#   "part": best_image["part"] if best_image else "unknown",
#   "damage_visible": best_image["damage_visible"] if best_image else "unknown",
#   "damage_magnitude": best_image["damage_magnitude"] if best_image else "unknown",
#   "is_original": best_image["is_original_photo"] if best_image else True,
#   "quality_issues": union across all images,
#   "has_text_instruction": any across all images,
# }

# ============================================================
# STEP 4: Verify object matches claim_object
# ============================================================
# if aggregate["object"] != claim_object and aggregate["object"] != "unknown":
#   object_mismatch = True
# else:
#   object_mismatch = False

# ============================================================
# STEP 5: Decide verdict
# ============================================================
# if not usable_images:
#   verdict = "not_enough_information"
#   evidence_standard_met = False
#   valid_image = False
# elif object_mismatch:
#   verdict = "contradicted"
#   evidence_standard_met = True  # image is fine, just wrong object
#   valid_image = True
# elif aggregate["part"] != text_extraction["claimed_part"] \
#      and aggregate["part"] != "unknown" \
#      and text_extraction["claimed_part"] != "unknown":
#   verdict = "contradicted"  # wrong part
#   evidence_standard_met = True
#   valid_image = True
# elif aggregate["damage_visible"] == "none":
#   verdict = "contradicted"  # claimed damage not visible
#   evidence_standard_met = True
#   valid_image = True
# elif aggregate["damage_visible"] == "unknown":
#   verdict = "not_enough_information"
#   evidence_standard_met = False
#   valid_image = True
# elif aggregate["damage_visible"] != text_extraction["claimed_damage"]:
#   verdict = "contradicted"  # different damage type
#   evidence_standard_met = True
#   valid_image = True
# else:
#   verdict = "supported"
#   evidence_standard_met = True
#   valid_image = True

# ============================================================
# STEP 6: Set issue_type and object_part based on IMAGE (not claim)
# ============================================================
# When verdict == "supported":
#   issue_type = aggregate["damage_visible"]
#   object_part = aggregate["part"]
# When verdict == "contradicted":
#   issue_type = aggregate["damage_visible"]  # what image actually shows
#   object_part = aggregate["part"]            # what image actually shows
#   # Special: if no damage visible at all, issue_type = "none"
#   # Special: if image is wrong_object or quality too bad to tell, issue_type = "unknown"
# When verdict == "not_enough_information":
#   issue_type = "unknown"
#   object_part = text_extraction["claimed_part"]  # preserve user intent
#   # EXCEPT if user claimed part is unknown itself, then "unknown"

# ============================================================
# STEP 7: Severity
# ============================================================
# if issue_type == "none":
#   severity = "none"
# elif issue_type == "unknown":
#   severity = "unknown"
# elif aggregate["damage_magnitude"] in ("low", "medium", "high"):
#   severity = aggregate["damage_magnitude"]
# else:
#   # Heuristic by damage type
#   severity_map = {
#     "scratch": "low",
#     "dent": "medium",  # default to medium unless image shows small
#     "crack": "medium",
#     "glass_shatter": "high",
#     "broken_part": "medium",
#     "missing_part": "medium",
#     "torn_packaging": "medium",
#     "crushed_packaging": "medium",
#     "water_damage": "medium",
#     "stain": "medium",
#   }
#   severity = severity_map.get(issue_type, "medium")

# ============================================================
# STEP 8: Risk flags (union)
# ============================================================
# risk_flags = set()
#
# # Visual quality issues from VLM
# for img in per_image_findings:
#   for q in img["quality_issues"]:
#     if q != "none":
#       risk_flags.add(q)
#
# # Object mismatch
# if object_mismatch:
#   risk_flags.add("wrong_object")
# if aggregate["part"] != text_extraction["claimed_part"] and verdict == "contradicted":
#   if "wrong_object_part" not in risk_flags:
#     risk_flags.add("wrong_object_part")
#
# # Damage type mismatch
# if verdict == "contradicted" and aggregate["damage_visible"] != "none":
#   if text_extraction["claimed_damage"] != "unknown":
#     risk_flags.add("claim_mismatch")
#
# # Damage not visible (claimed something, image shows none)
# if verdict == "contradicted" and aggregate["damage_visible"] == "none":
#   risk_flags.add("damage_not_visible")
#
# # Non-original photo
# if not aggregate["is_original"]:
#   risk_flags.add("non_original_image")
#   risk_flags.add("possible_manipulation")
#
# # Text instruction in image
# if aggregate["has_text_instruction"]:
#   risk_flags.add("text_instruction_present")
#
# # User history risk
# if user_history["history_flags"] == "user_history_risk":
#   risk_flags.add("user_history_risk")
#   risk_flags.add("manual_review_required")
# elif user_history["history_flags"] == "manual_review_required":
#   risk_flags.add("manual_review_required")
#
# # Any visual risk → manual review (per sample pattern)
# if any(r in risk_flags for r in [
#   "blurry_image", "cropped_or_obstructed", "low_light_or_glare",
#   "wrong_angle", "wrong_object", "wrong_object_part",
#   "non_original_image", "text_instruction_present",
# ]):
#   risk_flags.add("manual_review_required")
#
# # Edge: contradicted with no other risks → add manual_review_required (sample shows this)
# if verdict == "contradicted" and not risk_flags:
#   risk_flags.add("manual_review_required")
#
# # If empty → "none"
# if not risk_flags:
#   risk_flags_str = "none"
# else:
#   risk_flags_str = ";".join(sorted(risk_flags))

# ============================================================
# STEP 9: Supporting image IDs
# ============================================================
# if verdict == "not_enough_information":
#   supporting = "none"
# elif verdict == "supported":
#   # All images that show the damage
#   supporting = [img["image_id"] for img in usable_images
#                 if img["damage_visible"] != "none" and img["damage_visible"] != "unknown"]
#   if not supporting:
#     supporting = [best_image["image_id"]]
# elif verdict == "contradicted":
#   # Image(s) showing the contradiction
#   supporting = [best_image["image_id"]]
#
# supporting_str = ";".join(sorted(supporting)) if isinstance(supporting, list) else supporting

# ============================================================
# STEP 10: Justifications
# ============================================================
# claim_status_justification = f"{verdict_summary}. {aggregate['notes']}"
#   where verdict_summary is derived from verdict + issue + part
# evidence_standard_met_reason = short reason (e.g. "Image quality insufficient",
#   "Rear bumper visible with visible dent in img_1")

# ============================================================
# STEP 11: Lint and write
# ============================================================
# - Drop risk_flags not in allowed list
# - Replace invalid issue_type with "unknown"
# - Replace invalid object_part with "unknown"
# - Replace invalid severity with "unknown"
# - Lowercase "true"/"false"
# - Sort multi-value lists alphabetically