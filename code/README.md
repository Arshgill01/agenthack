# Evidence-Grounded Damage Claims Agent (EGDCA) Pipeline

This package implements a multi-stage, multi-modal verification agent designed for the HackerRank Orchestrate June 2026 challenge. It analyzes visual evidence alongside user conversations and claims history to determine the validity of damage claims for cars, laptops, and packages.

## Architecture

Rather than using a single monolithic prompt, this system implements a multi-stage decoupled pipeline for high reliability, precision, and verifiability:

1. **Text Extraction (`extractor.py`):** Uses an LLM to parse the claim conversation transcript, extracting the claimed object part, damage type, and stated severity. Features a robust regex fallback parser.
2. **User History & Rules Mapper (`pipeline.py`):** Looks up the user's historical risk flags from `user_history.csv` and pulls minimum evidence checklist requirements from `evidence_requirements.csv`.
3. **Multi-Image Auditor VLM (`auditor.py`):** Inspects each image independently to detect visible object parts, visible damage types, and security/quality flags (e.g. blur, glares, crop/obstructions, possible manipulation, non-original images).
4. **Claims Decision Engine (`decision.py`):** Executes deterministic business logic comparing extracted text claims to visual auditing findings to determine the final claim status, consolidated risk flags, and severity.
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
