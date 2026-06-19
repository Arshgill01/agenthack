from __future__ import annotations
import csv
import logging
from pathlib import Path
from config import DATA_DIR
from model_client import ModelClient
from extractor import ClaimExtractor
from auditor import ImageAuditor
from blind_auditor import BlindImageAuditor
from decision import DecisionEngine
from linter import OutputLinter

logger = logging.getLogger("pipeline")

class ClaimReviewPipeline:
    def __init__(self, client: ModelClient | None = None):
        self.client = client or ModelClient()
        self.extractor = ClaimExtractor(self.client)
        self.auditor = ImageAuditor(self.client)
        self.blind_auditor = BlindImageAuditor(self.client)
        self.decision_engine = DecisionEngine()
        self.linter = OutputLinter()
        self.last_run_extra = {}
        
        # Load datasets
        self.user_history_map = {}
        self.evidence_reqs = []
        self._load_user_history()
        self._load_evidence_requirements()

    def _load_user_history(self):
        csv_path = DATA_DIR / "user_history.csv"
        if not csv_path.exists():
            logger.warning(f"user_history.csv not found at {csv_path}")
            return
        try:
            with open(csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user_id = row.get("user_id", "").strip()
                    self.user_history_map[user_id] = row
            logger.info(f"Loaded {len(self.user_history_map)} user history entries.")
        except Exception as e:
            logger.error(f"Error loading user_history.csv: {e}")

    def _load_evidence_requirements(self):
        csv_path = DATA_DIR / "evidence_requirements.csv"
        if not csv_path.exists():
            logger.warning(f"evidence_requirements.csv not found at {csv_path}")
            return
        try:
            with open(csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                self.evidence_reqs = list(reader)
            logger.info(f"Loaded {len(self.evidence_reqs)} evidence requirements.")
        except Exception as e:
            logger.error(f"Error loading evidence_requirements.csv: {e}")

    def _match_evidence_requirements(self, claim_object: str, claimed_part: str, claimed_damage: str, num_images: int) -> list[dict[str, str]]:
        matched = []
        for req in self.evidence_reqs:
            req_obj = req.get("claim_object", "").strip().lower()
            applies_to = req.get("applies_to", "").strip().lower()
            
            # Check claim_object compatibility
            if req_obj != "all" and req_obj != claim_object:
                continue
                
            # Check applies_to condition
            is_match = False
            if req_obj == "all":
                if applies_to == "general claim review":
                    is_match = True
                elif applies_to == "multi-image rows" and num_images > 1:
                    is_match = True
                elif applies_to == "reviewability":
                    is_match = True
            elif claim_object == "car":
                if applies_to == "dent or scratch" and claimed_damage in ("dent", "scratch"):
                    is_match = True
                elif applies_to == "crack, broken, or missing part" and claimed_damage in ("crack", "broken_part", "missing_part", "glass_shatter"):
                    is_match = True
                elif applies_to == "vehicle identity or orientation":
                    is_match = True
            elif claim_object == "laptop":
                if applies_to == "screen, keyboard, or trackpad" and claimed_part in ("screen", "keyboard", "trackpad"):
                    is_match = True
                elif applies_to == "hinge, lid, corner, body, or port" and claimed_part in ("hinge", "lid", "corner", "body", "base", "port"):
                    is_match = True
            elif claim_object == "package":
                if applies_to == "crushed, torn, or seal damage" and claimed_damage in ("crushed_packaging", "torn_packaging", "broken_part", "missing_part"):
                    is_match = True
                elif applies_to == "water, stain, or label damage" and (claimed_damage in ("water_damage", "stain") or claimed_part == "label"):
                    is_match = True
                elif applies_to == "contents or inner item" and claimed_part in ("contents", "item"):
                    is_match = True
                    
            if is_match:
                matched.append(req)
        return matched

    def process_row(self, row: dict[str, str]) -> dict[str, str]:
        user_id = row.get("user_id", "").strip()
        image_paths_raw = row.get("image_paths", "").strip()
        user_claim = row.get("user_claim", "").strip()
        claim_object = row.get("claim_object", "").strip().lower()

        # Parse image paths
        image_paths = [p.strip() for p in image_paths_raw.split(";")] if image_paths_raw else []

        # Get user history fallback
        user_hist = self.user_history_map.get(user_id, {
            "user_id": user_id,
            "history_flags": "none",
            "history_summary": "New user with no history."
        })

        try:
            # 1. Text extraction
            claim_details = self.extractor.extract(user_claim, claim_object)
            logger.info(f"Row user={user_id} object={claim_object} | Extracted claimed_part={claim_details['claimed_part']} damage={claim_details['claimed_damage']}")

            # Match evidence requirements
            matched_reqs = self._match_evidence_requirements(
                claim_object=claim_object,
                claimed_part=claim_details["claimed_part"],
                claimed_damage=claim_details["claimed_damage"],
                num_images=len(image_paths)
            )

            # 2. Image auditing
            blind_result = self.blind_auditor.audit(image_paths=image_paths)
            audit_result = self.auditor.audit_images(
                image_paths=image_paths,
                claim_object=claim_object,
                claimed_part=claim_details["claimed_part"],
                claimed_damage=claim_details["claimed_damage"],
                matched_reqs=matched_reqs
            )

            # 3. Decision making
            decision = self.decision_engine.evaluate(
                claim_details=claim_details,
                user_history=user_hist,
                audit_result=audit_result,
                claim_object=claim_object,
                blind_result=blind_result,
                matched_reqs=matched_reqs
            )

            # 4. Strict Linting & Formatting
            decision["user_id"] = user_id
            decision["image_paths"] = image_paths_raw
            decision["user_claim"] = user_claim
            decision["claim_object"] = claim_object
            
            linted_row = self.linter.lint_row(decision, claim_object)
            self.last_run_extra = {
                "blind_aware_agreement": decision.get("blind_aware_agreement", "unknown")
            }
            return linted_row

        except Exception as e:
            logger.error(f"Pipeline error processing row user={user_id} object={claim_object}: {e}", exc_info=True)
            # Create a completely safe fallback row
            fallback = {
                "user_id": user_id,
                "image_paths": image_paths_raw,
                "user_claim": user_claim,
                "claim_object": claim_object,
                "evidence_standard_met": "false",
                "evidence_standard_met_reason": f"System error occurred during processing: {str(e)}",
                "risk_flags": "manual_review_required",
                "issue_type": "unknown",
                "object_part": "unknown",
                "claim_status": "not_enough_information",
                "claim_status_justification": f"Verification failed due to system error: {str(e)}",
                "supporting_image_ids": "none",
                "valid_image": "false",
                "severity": "unknown"
            }
            self.last_run_extra = {
                "blind_aware_agreement": "unknown"
            }
            return self.linter.lint_row(fallback, claim_object)
