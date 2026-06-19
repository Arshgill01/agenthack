import sys
from pathlib import Path

# Insert code directory into sys.path
EVAL_DIR = Path(__file__).resolve().parent
CODE_DIR = EVAL_DIR.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from decision import DecisionEngine

def run_tests():
    engine = DecisionEngine()
    failures = []

    def assert_eq(name, actual, expected):
        if actual != expected:
            failures.append(f"{name}: expected {expected}, got {actual}")

    # Case 1: Claimed scratch, visible broken_part on same part
    # Expected: contradicted (scratch is not broken_part)
    claim_details = {"claimed_part": "front_bumper", "claimed_damage": "scratch", "stated_severity": "low"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "front_bumper", "visible_damage": "broken_part", "severity": "medium", "is_original_photo": True, "detected_risks": ["none"]}
        ]
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "car")
    assert_eq("Case 1 - status", res["claim_status"], "contradicted")
    assert_eq("Case 1 - issue_type", res["issue_type"], "broken_part")

    # Case 2: Claimed dent, visible missing_part on same part
    # Expected: contradicted (dent is not missing_part)
    claim_details = {"claimed_part": "rear_bumper", "claimed_damage": "dent", "stated_severity": "medium"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "rear_bumper", "visible_damage": "missing_part", "severity": "medium", "is_original_photo": True, "detected_risks": ["none"]}
        ]
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "car")
    assert_eq("Case 2 - status", res["claim_status"], "contradicted")
    assert_eq("Case 2 - issue_type", res["issue_type"], "missing_part")

    # Case 3: Claimed scratch, visible dent on same part (surface ambiguity)
    # Expected: supported, but issue_type must be visually grounded (dent), not claimed (scratch)
    claim_details = {"claimed_part": "door", "claimed_damage": "scratch", "stated_severity": "low"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "door", "visible_damage": "dent", "severity": "low", "is_original_photo": True, "detected_risks": ["none"]}
        ]
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "car")
    assert_eq("Case 3 - status", res["claim_status"], "supported")
    assert_eq("Case 3 - issue_type", res["issue_type"], "dent")

    # Case 4: Claimed damage, visible none on same part, user history says exaggerated
    # Expected: contradicted, issue_type=none, severity=none (no fabricating scratches)
    claim_details = {"claimed_part": "rear_bumper", "claimed_damage": "dent", "stated_severity": "high"}
    user_history = {"history_flags": "user_history_risk;manual_review_required", "history_summary": "Several exaggerated vehicle claims"}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "rear_bumper", "visible_damage": "none", "severity": "none", "is_original_photo": True, "detected_risks": ["none"]}
        ]
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "car")
    assert_eq("Case 4 - status", res["claim_status"], "contradicted")
    assert_eq("Case 4 - issue_type", res["issue_type"], "none")
    assert_eq("Case 4 - severity", res["severity"], "none")

    # Case 5: Claimed package contents missing, image does not show contents clearly (poor quality / wrong angle)
    # Expected: not_enough_information
    claim_details = {"claimed_part": "contents", "claimed_damage": "missing_part", "stated_severity": "high"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "package", "detected_part": "contents", "visible_damage": "none", "severity": "none", "is_original_photo": True, "detected_risks": ["cropped_or_obstructed"]}
        ]
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "package")
    assert_eq("Case 5 - status", res["claim_status"], "not_enough_information")

    # Case 6: Wrong object visible
    # Expected: contradicted, wrong_object risk flag, no fabricated visual issue
    claim_details = {"claimed_part": "box", "claimed_damage": "crushed_packaging", "stated_severity": "medium"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "other", "detected_part": "item", "visible_damage": "none", "severity": "none", "is_original_photo": True, "detected_risks": ["wrong_object"]}
        ]
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "package")
    assert_eq("Case 6 - status", res["claim_status"], "contradicted")
    assert_eq("Case 6 - issue_type", res["issue_type"], "unknown")
    assert_eq("Case 6 - object_part", res["object_part"], "unknown")
    assert_eq("Case 6 - wrong_object in risk_flags", "wrong_object" in res["risk_flags"], True)

    # Case 7: Text instruction present with no real damage
    # Expected: issue_type=none, severity=none
    claim_details = {"claimed_part": "seal", "claimed_damage": "torn_packaging", "stated_severity": "medium"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "package", "detected_part": "seal", "visible_damage": "none", "severity": "none", "is_original_photo": True, "detected_risks": ["text_instruction_present"]}
        ]
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "package")
    assert_eq("Case 7 - status", res["claim_status"], "contradicted")
    assert_eq("Case 7 - issue_type", res["issue_type"], "none")
    assert_eq("Case 7 - severity", res["severity"], "none")

    # Case 8: Blind-First Dual Audit - blind says no damage, aware says scratch
    # Expected: manual_review_required flagged, claim status/issue type evaluates but risk flags include manual_review_required
    claim_details = {"claimed_part": "door", "claimed_damage": "scratch", "stated_severity": "low"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "door", "visible_damage": "scratch", "severity": "low", "is_original_photo": True, "detected_risks": ["none"]}
        ],
        "consensus": {"primary_object": "car", "primary_part": "door", "primary_damage": "scratch", "primary_severity": "low", "consensus_justification": "Scratch visible.", "supporting_image_ids": ["img_1"]}
    }
    blind_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "door", "visible_damage": "none", "severity": "none", "is_original_photo": True, "detected_risks": ["none"]}
        ],
        "consensus": {"primary_object": "car", "primary_part": "door", "primary_damage": "none", "primary_severity": "none", "consensus_justification": "No damage visible.", "supporting_image_ids": []}
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "car", blind_result)
    assert_eq("Case 8 - status", res["claim_status"], "supported")
    assert_eq("Case 8 - manual review risk flag", "manual_review_required" in res["risk_flags"], True)

    # Case 9: Blind-First Dual Audit - blind says dent, aware says dent
    # Expected: agree, supported dent
    claim_details = {"claimed_part": "door", "claimed_damage": "dent", "stated_severity": "medium"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "door", "visible_damage": "dent", "severity": "medium", "is_original_photo": True, "detected_risks": ["none"]}
        ],
        "consensus": {"primary_object": "car", "primary_part": "door", "primary_damage": "dent", "primary_severity": "medium", "consensus_justification": "Dent visible.", "supporting_image_ids": ["img_1"]}
    }
    blind_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "door", "visible_damage": "dent", "severity": "medium", "is_original_photo": True, "detected_risks": ["none"]}
        ],
        "consensus": {"primary_object": "car", "primary_part": "door", "primary_damage": "dent", "primary_severity": "medium", "consensus_justification": "Dent visible.", "supporting_image_ids": ["img_1"]}
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "car", blind_result)
    assert_eq("Case 9 - status", res["claim_status"], "supported")
    assert_eq("Case 9 - issue_type", res["issue_type"], "dent")
    assert_eq("Case 9 - agreement", res["blind_aware_agreement"], "agree")

    # Case 10: Blind-First Dual Audit - blind says scratch, aware says broken_part
    # Expected: trust blind (scratch), contradicted (since claimed door broken_part but blind says scratch)
    claim_details = {"claimed_part": "door", "claimed_damage": "broken_part", "stated_severity": "medium"}
    user_history = {"history_flags": "none", "history_summary": ""}
    audit_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "door", "visible_damage": "broken_part", "severity": "medium", "is_original_photo": True, "detected_risks": ["none"]}
        ],
        "consensus": {"primary_object": "car", "primary_part": "door", "primary_damage": "broken_part", "primary_severity": "medium", "consensus_justification": "Broken part visible.", "supporting_image_ids": ["img_1"]}
    }
    blind_result = {
        "valid_call": True,
        "images": [
            {"image_id": "img_1", "detected_object": "car", "detected_part": "door", "visible_damage": "scratch", "severity": "low", "is_original_photo": True, "detected_risks": ["none"]}
        ],
        "consensus": {"primary_object": "car", "primary_part": "door", "primary_damage": "scratch", "primary_severity": "low", "consensus_justification": "Scratch visible.", "supporting_image_ids": ["img_1"]}
    }
    res = engine.evaluate(claim_details, user_history, audit_result, "car", blind_result)
    assert_eq("Case 10 - status", res["claim_status"], "contradicted")
    assert_eq("Case 10 - issue_type", res["issue_type"], "scratch")
    assert_eq("Case 10 - agreement", res["blind_aware_agreement"], "disagree_different_damage")

    if failures:
        print("FAILURES DETECTED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL ANTI-OVERFIT CHECKS PASSED SUCCESSFULLY.")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
