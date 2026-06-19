"""Pass 2 — Deep data audit. Extract per-row ground truth patterns from sample_claims.csv.
This is reference material — do NOT use as hardcoded test labels (per problem requirements).
"""
import csv
from collections import Counter, defaultdict

SAMPLE_CSV = "/Users/arshdeepsingh/Developer/hackerrank-orchestrate-june26/dataset/sample_claims.csv"

# Patterns from reading sample_claims.csv
# Format: row index -> (claimed_part, claimed_damage, image_shows_part, image_shows_damage, claim_status, issue_type, object_part, severity, key_risk_flags, evidence_met)
SAMPLE_GT = {
    1: ("rear_bumper", "dent", "rear_bumper", "dent", "supported", "dent", "rear_bumper", "medium", [], True),
    2: ("front_bumper", "scratch", "front_bumper", "scratch", "supported", "scratch", "front_bumper", "low", [], True),
    3: ("windshield", "crack", "windshield", "crack", "supported", "crack", "windshield", "medium", [], True),
    4: ("side_mirror", "broken", "side_mirror", "broken", "supported", "broken_part", "side_mirror", "medium", [], True),
    5: ("rear_bumper", "damaged", "rear_bumper", "scratch", "contradicted", "scratch", "rear_bumper", "low",
        ["claim_mismatch", "user_history_risk", "manual_review_required"], True),
    6: ("headlight", "cracked", "unknown", "unknown", "not_enough_information", "unknown", "headlight", "unknown",
        ["wrong_angle", "damage_not_visible"], False),
    7: ("door", "dent", "door", "dent", "supported", "dent", "door", "medium", ["blurry_image"], True),
    8: ("hood", "scratch", "front_bumper", "broken", "contradicted", "broken_part", "front_bumper", "high",
        ["claim_mismatch", "non_original_image", "user_history_risk", "manual_review_required"], True),
    9: ("screen", "crack", "screen", "crack", "supported", "crack", "screen", "medium", [], True),
    10: ("hinge", "broken", "hinge", "broken", "supported", "broken_part", "hinge", "medium", [], True),
    11: ("keyboard", "stain", "keyboard", "stain", "supported", "stain", "keyboard", "medium", [], True),
    12: ("corner", "dent", "corner", "dent", "supported", "dent", "corner", "low", [], True),
    13: ("screen", "shattered", "screen", "crack", "supported", "crack", "screen", "medium", [], True),
    14: ("trackpad", "damaged", "trackpad", "none", "contradicted", "none", "trackpad", "none",
         ["damage_not_visible", "user_history_risk", "manual_review_required"], True),
    15: ("package_corner", "crushed", "package_corner", "crushed", "supported", "crushed_packaging", "package_corner", "medium", [], True),
    16: ("seal", "torn", "seal", "torn", "supported", "torn_packaging", "seal", "medium", [], True),
    17: ("package_side", "wet", "package_side", "wet", "supported", "water_damage", "package_side", "medium",
         ["user_history_risk", "manual_review_required"], True),
    18: ("contents", "missing", "unknown", "unknown", "not_enough_information", "unknown", "contents", "unknown",
         ["cropped_or_obstructed", "damage_not_visible", "manual_review_required"], False),
    19: ("box", "crushed", "unknown", "unknown", "contradicted", "unknown", "unknown", "low",
         ["wrong_object", "claim_mismatch", "user_history_risk", "manual_review_required"], True),
    20: ("seal", "torn", "seal", "none", "contradicted", "none", "seal", "none",
         ["damage_not_visible", "text_instruction_present", "user_history_risk", "manual_review_required"], True),
}

# Patterns observed across samples (for sanity checks, NOT hardcoded labels):
# 1. When claim is supported → issue_type matches claimed damage type, severity aligns with damage magnitude
# 2. When claim is contradicted → issue_type matches what the IMAGE shows, not what user said
#    - case_008: user said "scratch", image showed "broken_part" → issue_type=broken_part
#    - case_014: user said "damaged", image showed no damage → issue_type=none
#    - case_020: user said "torn", image showed no tear → issue_type=none
# 3. When not_enough_information → issue_type=unknown, object_part=claimed_part (preserve user intent),
#    severity=unknown, supporting_image_ids=none
# 4. evidence_standard_met false → supporting_image_ids=none, valid_image can still be true
# 5. severity=none when issue_type=none (logically correct)
# 6. severity=unknown when issue_type=unknown

# Object-part vs visible damage patterns (a heuristic, not hardcoded):
# - "scratch" → low or medium severity
# - "dent" → low (small) or medium (visible)
# - "crack" (screen) → medium
# - "broken_part" → medium (small part) or high (major)
# - "crushed_packaging" → medium typically
# - "torn_packaging" → medium typically
# - "water_damage" → medium typically
# - "stain" → medium typically
# - "none" → none
# - "unknown" → unknown

# User-history risk propagation:
# - user_history flag "user_history_risk" → risk_flags include "user_history_risk;manual_review_required"
# - user_history flag "manual_review_required" → risk_flags include "manual_review_required"
# - user_history flag "none" → risk_flags depends on visual evidence (may still add visual risks)

# supporting_image_ids logic:
# - lists IDs of images that actually support the decision
# - if contradicted: lists the image that shows the contradicting evidence
# - if not_enough_information and evidence not met: "none"
# - if supported: lists the relevant image(s)

# supporting_image_ids ordering:
# Looking at sample: img_1, img_2, img_3 (alphabetical by image number)
# Always sorted alphabetically

def main():
    print("=== SAMPLE GROUND TRUTH TABLE ===")
    with open(SAMPLE_CSV, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"Total rows: {len(rows)}")
    print()
    print(f"{'row':<4} {'obj':<8} {'status':<22} {'issue':<20} {'part':<20} {'sev':<8} {'risks'}")
    for i, r in enumerate(rows, 1):
        print(f"{i:<4} {r['claim_object']:<8} {r['claim_status']:<22} {r['issue_type']:<20} {r['object_part']:<20} {r['severity']:<8} {r['risk_flags']}")

    # Counts
    statuses = Counter(r["claim_status"] for r in rows)
    issues = Counter(r["issue_type"] for r in rows)
    severities = Counter(r["severity"] for r in rows)
    print()
    print(f"Statuses: {dict(statuses)}")
    print(f"Issues: {dict(issues)}")
    print(f"Severities: {dict(severities)}")

    # Risk flag frequency
    risk_counter = Counter()
    for r in rows:
        for flag in r["risk_flags"].split(";"):
            if flag.strip():
                risk_counter[flag] += 1
    print(f"Risk flags: {dict(risk_counter)}")

    # Object-part per object type
    print()
    print("=== object_part per claim_object ===")
    obj_parts = defaultdict(Counter)
    for r in rows:
        obj_parts[r["claim_object"]][r["object_part"]] += 1
    for obj, parts in obj_parts.items():
        print(f"  {obj}: {dict(parts)}")


if __name__ == "__main__":
    main()