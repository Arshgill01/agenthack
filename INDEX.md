# Research Pass Artifacts Index

All artifacts here are **research output**, not production code. The actual implementation
should reuse these as references, not as a hard dependency.

## Files

### Pass 1 — Problem Understanding
- `pass1_problem/PROBLEM_DEEP_READ.md` — what the eval actually scores, the 10 output columns,
  truth-from-sample-claims.csv patterns, hard constraints, what winning looks like.

### Pass 2 — Data Audit
- `pass2_data/DATA_AUDIT.md` — sample + test set characteristics, ground truth patterns,
  user history inheritance rule, evidence requirements context, prompt-injection patterns,
  multi-part claim handling, cost envelope.
- `pass2_data/audit_sample.py` — script that verifies sample ground truth table.

### Pass 3 — Architecture
- `pass3_architecture/ARCHITECTURE.md` — multi-stage pipeline design, decision engine stages,
  two-model strategy, caching, robustness suite, output audit, risk register.

### Pass 4 — Strategy
- `pass4_strategy/STRATEGY.md` — competitive landscape, what May 2026 winner did, what we
  can/cannot compete on, AI Judge interview prep, killshot pitch.

### Pass 5 — Implementation Roadmap
- `pass5_implementation/ROADMAP.md` — concrete 1-day build plan, file structure, success
  metrics, risk register, definition of done, deliverable artifacts.

### Concrete Artifacts (for use during implementation)
- `artifacts/taxonomy.json` — single source of truth for categorical allowed values.
- `artifacts/text_extraction_tables.json` — keyword → taxonomy mappings for the text
  extractor (handles romanized Hindi/Spanish/Chinese).
- `artifacts/image_auditor_v1_prompt.txt` — primary VLM prompt (feature extraction mode).
- `artifacts/image_auditor_v2_prompt.txt` — alternative VLM prompt (verdict mode, for
  two-model reconciliation).
- `artifacts/decision_engine_rules.py` — formal pseudocode of Stage 4 rules.

## How to use this during implementation

1. Read `00_EXECUTIVE_SUMMARY.md` first
2. Read Pass 1 + Pass 2 to understand the data
3. Read Pass 3 to understand the architecture
4. Use `artifacts/` as the starting point for code
5. Follow Pass 5 roadmap for the build order
6. Reference Pass 4 for AI Judge interview prep

## What NOT to copy verbatim

The text_extraction_tables.json contains **patterns learned from sample_claims.csv**. These
are guidelines, not hardcoded labels. The implementation should use them as regex/keyword
fallbacks, not as exact-match answers to specific rows.

The decision_engine_rules.py is **pseudocode**. Implementation should translate it to
proper Python with type hints, error handling, and tests.

## Confidence levels

- Pass 1 (problem understanding): 95% confident. Direct read of problem_statement.md +
  sample_claims.csv.
- Pass 2 (data audit): 90% confident. Verified with Python scripts.
- Pass 3 (architecture): 80% confident. Inferred from May 2026 pattern + general best
  practices. Could be off if hidden eval criteria differ.
- Pass 4 (strategy): 70% confident. Speculative on competitive landscape.
- Pass 5 (implementation): 85% confident. Standard Python patterns.

## Open questions to resolve during implementation

1. Does Gemini API key work in this environment? (Need to test.)
2. Does Pillow + pillow-avif-plugin handle AVIF? (Need to test.)
3. Does Gemini 2.5 Flash reliably return JSON for our prompts? (Need to test.)
4. What's the actual test set distribution for object types? (44 rows, 18 car/13 laptop/13
   package per Pass 2 audit.)
5. What hidden-test rows look like? (Unknown; the 6 injection rows in test give hints.)