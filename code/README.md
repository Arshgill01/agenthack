# Evidence-Grounded Damage Claims Agent (EGDCA) Pipeline

This package implements a multi-stage, multi-modal verification agent designed for the HackerRank Orchestrate June 2026 challenge. It analyzes visual evidence alongside user conversations and claims history to determine the validity of damage claims for cars, laptops, and packages.

## Architecture & Innovation

Rather than using a single monolithic prompt, this system implements a **3-pass VLM pipeline with confidence-gated self-correction** for high reliability, precision, and verifiability:

1. **Text Extraction (`extractor.py`):** Uses an LLM to parse the claim conversation transcript, extracting the claimed object part, damage type, and stated severity. Features a robust regex fallback parser.
2. **Evidence Requirements Checklist (`pipeline.py`):** Dynamically loads `evidence_requirements.csv` and matches applicable requirements based on the claim's object type and damage family to construct a custom inspectability rubric.
3. **Blind-First Dual Audit (Pass 1 & Pass 2 VLMs):**
   - **Pass 1 — Blind Audit (`blind_auditor.py`):** Audits the images with *zero* claim context to eliminate VLM anchoring bias (replicating a real human insurance adjuster).
   - **Pass 2 — Aware Audit (`auditor.py`):** Audits the images with full claim context + the matched evidence requirement checklist injected as an inspectability rubric.
4. **Confidence-Gated CoT Reconciler (Pass 3 — `self_corrector.py`):** When Pass 1 and Pass 2 disagree on damage type, part, or severity (delta ≥ 2 levels), a Chain-of-Thought reconciler fires. It presents both pass results in randomized order (anti-anchoring via deterministic hash-based shuffle) and asks the VLM for 3-stage structured reasoning: (1) raw visual re-read, (2) prior pass review, (3) reconciliation synthesis. Only triggers on ~15-25% of claims.
5. **Decision Engine (`decision.py`):** Calibrates and normalizes VLM output: taxonomy mapping (e.g. glass_shatter→crack on laptops), severity capping, part compatibility checks, evidence requirement satisfaction, risk flag aggregation.
6. **Output Linter (`linter.py`):** Validates and cleans output fields against the required schema and taxonomy.
7. **SQLite Response Caching (`cache.py`):** Caches API outputs keyed on prompt+image hash to prevent redundant API calls. Tracks actual token usage from API metadata.

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
