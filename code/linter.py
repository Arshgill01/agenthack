from __future__ import annotations
import logging
from config import (
    ALLOWED_CLAIM_STATUS, ALLOWED_ISSUE_TYPES, OBJECT_PARTS_MAP,
    ALLOWED_SEVERITIES, ALLOWED_RISK_FLAGS, OUTPUT_COLUMNS
)

logger = logging.getLogger("linter")

class OutputLinter:
    def __init__(self):
        pass

    def lint_row(self, row: dict[str, str], claim_object: str) -> dict[str, str]:
        linted = {}
        
        # Preserve input columns
        linted["user_id"] = str(row.get("user_id", "")).strip()
        linted["image_paths"] = str(row.get("image_paths", "")).strip()
        linted["user_claim"] = str(row.get("user_claim", "")).strip()
        linted["claim_object"] = str(row.get("claim_object", claim_object)).strip()

        # 1. evidence_standard_met
        val = str(row.get("evidence_standard_met", "false")).lower().strip()
        linted["evidence_standard_met"] = "true" if val in ["true", "1", "yes"] else "false"

        # 2. evidence_standard_met_reason
        linted["evidence_standard_met_reason"] = str(row.get("evidence_standard_met_reason", "No reason provided.")).strip()

        # 3. risk_flags
        flags_str = str(row.get("risk_flags", "none")).lower().strip()
        if not flags_str or flags_str == "":
            flags_str = "none"
        
        # Parse and filter risk flags
        flags_list = [f.strip() for f in flags_str.split(";")]
        valid_flags = []
        for f in flags_list:
            if f in ALLOWED_RISK_FLAGS:
                valid_flags.append(f)
            else:
                logger.warning(f"Linter removed invalid risk flag: {f}")
        
        if not valid_flags:
            valid_flags = ["none"]
        elif "none" in valid_flags and len(valid_flags) > 1:
            valid_flags.remove("none")
        
        # Ensure user_history_risk or visual flags imply manual_review_required
        if any(f in valid_flags for f in ["user_history_risk", "claim_mismatch", "possible_manipulation", "non_original_image", "text_instruction_present", "wrong_object"]):
            if "manual_review_required" not in valid_flags:
                valid_flags.append("manual_review_required")
                
        linted["risk_flags"] = ";".join(sorted(valid_flags))

        # 4. issue_type
        issue = str(row.get("issue_type", "unknown")).lower().strip()
        if issue not in ALLOWED_ISSUE_TYPES:
            logger.warning(f"Linter mapped invalid issue_type '{issue}' to 'unknown'")
            issue = "unknown"
        linted["issue_type"] = issue

        # 5. object_part
        part = str(row.get("object_part", "unknown")).lower().strip().replace(" ", "_")
        allowed_parts = OBJECT_PARTS_MAP.get(claim_object, {"unknown"})
        if part not in allowed_parts:
            logger.warning(f"Linter mapped invalid object_part '{part}' for {claim_object} to 'unknown'")
            part = "unknown"
        linted["object_part"] = part

        # 6. claim_status
        status = str(row.get("claim_status", "not_enough_information")).lower().strip()
        if status not in ALLOWED_CLAIM_STATUS:
            logger.warning(f"Linter mapped invalid claim_status '{status}' to 'not_enough_information'")
            status = "not_enough_information"
        linted["claim_status"] = status

        # 7. claim_status_justification
        linted["claim_status_justification"] = str(row.get("claim_status_justification", "No justification provided.")).strip()

        # 8. supporting_image_ids
        supporting = str(row.get("supporting_image_ids", "none")).strip()
        if not supporting or supporting == "":
            supporting = "none"
        linted["supporting_image_ids"] = supporting

        # 9. valid_image
        val_img = str(row.get("valid_image", "true")).lower().strip()
        linted["valid_image"] = "true" if val_img in ["true", "1", "yes"] else "false"

        # 10. severity
        sev = str(row.get("severity", "unknown")).lower().strip()
        if sev not in ALLOWED_SEVERITIES:
            logger.warning(f"Linter mapped invalid severity '{sev}' to 'unknown'")
            sev = "unknown"
        linted["severity"] = sev

        # Ensure order matches OUTPUT_COLUMNS
        final_row = {}
        for col in OUTPUT_COLUMNS:
            final_row[col] = linted.get(col, "")

        return final_row
