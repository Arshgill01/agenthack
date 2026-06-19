# HackerRank Orchestrate

Starter repository for the **HackerRank Orchestrate** 24-hour hackathon.

Build a system that verifies visual evidence for damage claims across three object types: **cars**, **laptops**, and **packages**.

Your system will receive claim conversations, one or more submitted images, user claim history, and minimum evidence requirements. It must decide whether the submitted images support the claim, contradict it, or do not provide enough information.

Read [`problem_statement.md`](./problem_statement.md) for the full task spec, input/output schema, and allowed values.

---

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

---

## Contents

1. [Architecture & Innovation](#architecture--innovation)
2. [Repository layout](#repository-layout)
3. [What you need to build](#what-you-need-to-build)
4. [Where your code goes](#where-your-code-goes)
5. [Quickstart](#quickstart)
6. [Evaluation](#evaluation)
7. [Chat transcript logging](#chat-transcript-logging)
8. [Submission](#submission)
9. [Judge interview](#judge-interview)

---

## Repository layout

```text
.
├── AGENTS.md                         # Rules for AI coding tools + transcript logging
├── problem_statement.md              # Full task description and I/O schema
├── README.md                         # You are here
├── code/                             # Build your solution here
│   ├── main.py                       # Suggested terminal entry point
│   └── evaluation/
│       └── main.py                   # Suggested evaluation entry point
└── dataset/
    ├── sample_claims.csv             # Inputs + expected outputs for development
    ├── claims.csv                    # Inputs only; run your system on these rows
    ├── user_history.csv              # Historical claim counts and risk context
    ├── evidence_requirements.csv     # Minimum image evidence requirements
    └── images/
        ├── sample/                   # Images referenced by sample_claims.csv
        └── test/                     # Images referenced by claims.csv
```

---

## What you need to build

A system that, for each row in `dataset/claims.csv`, produces one row in `output.csv`.

Input fields:

| Column | Meaning |
|---|---|
| `user_id` | User submitting the claim; use this to look up `dataset/user_history.csv` |
| `image_paths` | One or more submitted image paths, separated by semicolons |
| `user_claim` | Chat transcript describing the issue |
| `claim_object` | `car`, `laptop`, or `package` |

Required output fields:

| Column | Meaning |
|---|---|
| `evidence_standard_met` | Whether the image set is sufficient to evaluate the claim |
| `evidence_standard_met_reason` | Short reason for the evidence decision |
| `risk_flags` | Semicolon-separated risk flags, or `none` |
| `issue_type` | Visible issue type |
| `object_part` | Relevant object part |
| `claim_status` | `supported`, `contradicted`, or `not_enough_information` |
| `claim_status_justification` | Concise explanation grounded in the image evidence |
| `supporting_image_ids` | Image IDs supporting the decision, or `none` |
| `valid_image` | Whether the image set is usable for automated review |
| `severity` | `none`, `low`, `medium`, `high`, or `unknown` |

Hard requirements:

- Must read the provided CSV files and local images.
- Must produce `output.csv` with the exact schema in `problem_statement.md`.
- Must include an evaluation workflow
- Must avoid hardcoded test labels or file-specific answers.

Beyond that you are free to bring your own approach: VLMs, LLMs, structured prompting, rule layers, batching, caching, evaluation pipelines, model comparison, or anything else.

---

## Where your code goes

All of your work belongs in [`code/`](./code/). The repo ships with empty starter files that you can grow into your full solution.

### Architecture & Innovation

Rather than using a single monolithic prompt, this system implements a multi-stage decoupled pipeline for high reliability, precision, and verifiability:

1. **Text Extraction (`extractor.py`):** Uses an LLM to parse the claim conversation transcript, extracting the claimed object part, damage type, and stated severity. Features a robust regex fallback parser.
2. **Evidence Requirements Checklist (`pipeline.py`):** Dynamically loads `evidence_requirements.csv` and matches applicable requirements based on the claim's object type and damage family to construct a custom inspectability rubric.
3. **Blind-First Dual Audit (Pass 1 & Pass 2 VLMs):**
   - **Pass 1 - Blind Audit (`blind_auditor.py`):** Audits the images with *zero* claim context to eliminate VLM anchoring bias (replicating a real human insurance adjuster).
   - **Pass 2 - Aware Audit (`auditor.py`):** Audits the images with full claim context + the matched evidence requirement checklist injected as an inspectability rubric.
4. **Reconciliation & Decision Engine (`decision.py`):** Compares the blind audit against the claim-aware audit. Disagreements in damage type or part serve as a strong visual discrepancy signal, automatically triggering risk flags (`claim_mismatch`) and overriding to unbiased blind observations. Checks requirement checklist satisfaction to determine `evidence_standard_met`.
5. **Output Formatter & Linter (`linter.py`):** Validates and cleans output fields, aligning them strictly with permitted values and formatting constraints.
6. **SQLite Response Caching (`cache.py`):** Caches API outputs in a local SQLite database to prevent redundant API charges and allow instant local dry-runs.

Suggested conventions:

- Put your main runnable solution in `code/main.py`, or document your own entry point clearly.
- Put evaluation code under `code/evaluation/` or an `evaluation/` folder included in your final `code.zip`.
- Write final predictions to `output.csv`.

---

## Quickstart

Clone this repository:

```bash
git clone git@github.com:interviewstreet/hackerrank-orchestrate-june26.git
cd hackerrank-orchestrate-june26
```

You are free to use any language or runtime. Python, JavaScript, and TypeScript are all reasonable choices.

---

## Evaluation

The evaluation report should include:

- metrics on `dataset/sample_claims.csv`
- at least two strategies, prompts, or model configurations compared
- the final strategy used for `output.csv`
- operational analysis covering model calls, token usage, image usage, approximate cost, runtime, and TPM/RPM considerations

---

## Chat transcript logging

This repo ships with an `AGENTS.md` that modern AI coding tools may read. It instructs the tool to append conversation turns to a shared log file:

| Platform | Path |
|---|---|
| macOS / Linux | `$HOME/hackerrank_orchestrate/log.txt` |
| Windows | `%USERPROFILE%\hackerrank_orchestrate\log.txt` |

You will upload this log as your chat transcript at submission time. The chat transcript means your conversation with the AI coding tool you used to build the system. It is not the runtime logs, reasoning trace, or conversation history produced by the claim-verification agent you are building.

If you use multiple AI tools, include the relevant conversation logs from all of them in the same transcript file. Separate each tool's section with a clear divider and label it with the tool name.

Never paste secrets into the chat. If secrets are needed, use environment variables.

---

## Submission

Submit the following files as instructed by HackerRank:

1. **Code zip**: zip your runnable solution, README, prompts/configs, and evaluation folder. Exclude virtualenvs, `node_modules`, build artifacts, and unnecessary generated files.
2. **Predictions CSV**: your final `output.csv` for all rows in `dataset/claims.csv`.
3. **Chat transcript**: the `log.txt` from the path in [Chat transcript logging](#chat-transcript-logging).

Before submitting, confirm:

- `output.csv` has one row per row in `dataset/claims.csv`.
- `output.csv` has the exact required columns in the exact required order.
- Your evaluation files are included in `code.zip`.

---

## Judge interview

After submission, the AI Judge may ask about your approach, implementation decisions, model usage, evaluation strategy, and how you used AI while building the solution.

Be prepared to explain your solution in detail.
