from __future__ import annotations
import argparse
import csv
import logging
import os
import sys
from pathlib import Path

# Insert code directory into sys.path
CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

# Load .env file manually if it exists in the repo root
def load_dotenv():
    env_path = CODE_DIR.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    os.environ[key] = val

load_dotenv()

from pipeline import ClaimReviewPipeline
from config import OUTPUT_COLUMNS, ALLOWED_CLAIM_STATUS, ALLOWED_ISSUE_TYPES, ALLOWED_SEVERITIES, OBJECT_PARTS_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Modal Claim Evidence Review Agent")
    parser.add_argument(
        "--input", 
        default=str(CODE_DIR.parent / "dataset" / "claims.csv"),
        help="Path to the input claims CSV file"
    )
    parser.add_argument(
        "--output", 
        default=str(CODE_DIR.parent / "output.csv"),
        help="Path to write the output CSV predictions"
    )
    parser.add_argument(
        "--cache-disable",
        action="store_true",
        help="Disable local caching of API responses"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the output CSV schema and allowed values"
    )
    return parser.parse_args()

def validate_csv(output_path: str) -> bool:
    path = Path(output_path)
    if not path.exists():
        logger.error(f"Validation failed: output file '{output_path}' does not exist.")
        return False

    problems = []
    try:
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
        
        if not reader:
            logger.error("Validation failed: output CSV is empty.")
            return False

        # Verify columns
        headers = reader[0].keys()
        if list(headers) != OUTPUT_COLUMNS:
            problems.append(f"Header mismatch.\nExpected: {OUTPUT_COLUMNS}\nFound: {list(headers)}")

        for idx, row in enumerate(reader, start=1):
            # Check for allowed values
            status = row.get("claim_status")
            issue = row.get("issue_type")
            part = row.get("object_part")
            sev = row.get("severity")
            obj = row.get("claim_object")
            ev_std = row.get("evidence_standard_met")
            val_img = row.get("valid_image")

            if status not in ALLOWED_CLAIM_STATUS:
                problems.append(f"Row {idx}: claim_status '{status}' is not in allowed list {ALLOWED_CLAIM_STATUS}")
            if issue not in ALLOWED_ISSUE_TYPES:
                problems.append(f"Row {idx}: issue_type '{issue}' is not in allowed list {ALLOWED_ISSUE_TYPES}")
            if sev not in ALLOWED_SEVERITIES:
                problems.append(f"Row {idx}: severity '{sev}' is not in allowed list {ALLOWED_SEVERITIES}")
            
            allowed_parts = OBJECT_PARTS_MAP.get(obj, {"unknown"})
            if part not in allowed_parts:
                problems.append(f"Row {idx}: object_part '{part}' is not valid for claim_object '{obj}'. Allowed: {allowed_parts}")
            
            if ev_std not in ["true", "false"]:
                problems.append(f"Row {idx}: evidence_standard_met '{ev_std}' must be lowercase 'true' or 'false'")
            if val_img not in ["true", "false"]:
                problems.append(f"Row {idx}: valid_image '{val_img}' must be lowercase 'true' or 'false'")

    except Exception as e:
        logger.error(f"Error reading CSV during validation: {e}")
        return False

    if problems:
        logger.error("Validation failed with the following problems:")
        for p in problems[:20]:
            print(f"  - {p}")
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more problems.")
        return False

    logger.info("Validation passed successfully! No schema or constraint problems found.")
    return True

def main() -> int:
    args = parse_args()

    if args.validate_only:
        logger.info(f"Running validation only on output file: {args.output}")
        ok = validate_csv(args.output)
        return 0 if ok else 1

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error(f"Input file '{args.input}' does not exist.")
        return 1

    logger.info(f"Loading claims from {input_path}")
    claims = []
    with open(input_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            claims.append(row)

    logger.info(f"Loaded {len(claims)} rows to process.")
    
    # Initialize pipeline
    from model_client import ModelClient
    client = ModelClient(cache_enabled=not args.cache_disable)
    pipeline = ClaimReviewPipeline(client)

    # Process rows
    processed_rows = []
    for idx, claim in enumerate(claims, start=1):
        user_id = claim.get("user_id", "unknown")
        logger.info(f"[{idx}/{len(claims)}] Processing claim for user {user_id}...")
        processed = pipeline.process_row(claim)
        processed_rows.append(processed)

    # Write output
    logger.info(f"Writing output to {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(processed_rows)

    logger.info(f"Successfully processed and wrote {len(processed_rows)} rows.")

    # Validate output
    ok = validate_csv(args.output)
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
