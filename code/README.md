# Evidence-Grounded Damage Claims Agent (EGDCA) Pipeline

This package implements a multi-stage, multi-modal verification agent designed for the HackerRank Orchestrate June 2026 challenge. It analyzes visual evidence alongside user conversations and claims history to determine the validity of damage claims for cars, laptops, and packages.

## Architecture & Innovation

Rather than using a single monolithic prompt, this system implements a multi-stage decoupled pipeline for high reliability, precision, and verifiability:

1. **Text Extraction (`extractor.py`):** Uses an LLM to parse the claim conversation transcript, extracting the claimed object part, damage type, and stated severity. Features a robust regex fallback parser.
2. **Evidence Requirements Checklist (`pipeline.py`):** Dynamically loads `evidence_requirements.csv` and matches applicable requirements based on the claim's object type and damage family to construct a custom inspectability rubric.
3. **Blind-First Dual Audit (Pass 1 & Pass 2 VLMs):**
   - **Pass 1 - Blind Audit (`blind_auditor.py`):** Audits the images with *zero* claim context to eliminate VLM anchoring bias (replicating a real human insurance adjuster).
   - **Pass 2 - Aware Audit (`auditor.py`):** Audits the images with full claim context + the matched evidence requirement checklist injected as an inspectability rubric.
4. **Reconciliation & Decision Engine (`decision.py`):** Compares the blind audit against the claim-aware audit. Disagreements in damage type or part serve as a strong visual discrepancy signal, automatically triggering risk flags (`claim_mismatch`) and overriding to unbiased blind observations. Checks requirement checklist satisfaction to determine `evidence_standard_met`.
5. **Output Formatter & Linter (`linter.py`):** Validates and cleans output fields, aligning them strictly with permitted values and formatting constraints.
6. **SQLite Response Caching (`cache.py`):** Caches API outputs in a local SQLite database to prevent redundant API charges and allow instant local dry-runs.

## Installation

Ensure Pillow and pandas are installed in your Python environment:
```bash
pip install Pillow pandas requests
```

If you plan to use the native Google Generative AI SDK, install it:
```bash
pip install google-generativeai
```

## Running the Pipeline

To run the pipeline and generate predictions for `dataset/claims.csv` (writing the results to `output.csv`):

```bash
# Set your model API keys
export GEMINI_API_KEY="your-api-key"

# Run the agent
python3 code/main.py
```

### Options

- `--input`: Path to input claims CSV (default: `dataset/claims.csv`).
- `--output`: Path to write the output CSV (default: `output.csv`).
- `--cache-disable`: Disable reading/writing to the local SQLite database cache.
- `--validate-only`: Only validate the structure and taxonomy of an existing output CSV.

## Evaluation

To run evaluations on the labeled development dataset `dataset/sample_claims.csv`:

```bash
python3 code/evaluation/main.py
```

This script evaluates accuracies for claim status, object parts, issue types, and severities, producing:
- `code/evaluation/eval_results.json`: Raw evaluation metrics.
- `code/evaluation/evaluation_report.md`: Markdown summary of metrics, cost estimations, and operational details.
