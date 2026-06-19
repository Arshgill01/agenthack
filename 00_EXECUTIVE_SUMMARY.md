# Multi-Modal Evidence Review — Research Executive Summary

## What this competition actually evaluates

Per the May 2026 evaluation_criteria.md (only public criteria we have):

1. **Agent Design** (architecture, separation of concerns, determinism)
2. **AI Judge Interview** (depth, trade-offs, failure-mode reasoning)
3. **Output CSV** (per-row column accuracy, no hallucination)
4. **AI Fluency (chat transcript)** (clear scoped prompts, critiqued AI output)

Top finishers balance all four. Pure accuracy alone won't win; pure elegance alone won't win.

## What the problem actually requires

Per `problem_statement.md`:

For each row in `dataset/claims.csv`, produce one row in `output.csv` with 10 specific
columns that fall into two categories:

**Categorical (strict taxonomy, exact match):**
- `claim_status`: supported / contradicted / not_enough_information
- `issue_type`: dent, scratch, crack, glass_shatter, broken_part, missing_part,
  torn_packaging, crushed_packaging, water_damage, stain, none, unknown
- `object_part`: car/laptop/package-specific lists + unknown
- `severity`: none, low, medium, high, unknown
- `evidence_standard_met`, `valid_image`: true / false

**Free-text (likely fuzzy matched):**
- `evidence_standard_met_reason`, `claim_status_justification`, `risk_flags`,
  `supporting_image_ids`

The **ground truth comes from the image**, not from what the user claimed. Looking at
sample_claims.csv, when the user's claim mismatches the image, the output reports what
the IMAGE shows (e.g. case_008: user says "hood scratch", image shows broken bumper →
issue_type=broken_part, object_part=front_bumper, claim_status=contradicted).

## The fundamental challenge

This is a **computer vision classification problem** wrapped in a text-extraction envelope.

The hard part is identifying from each image:
- what object is shown
- what part is visible
- what damage (if any) is present
- image quality (blurry, cropped, wrong angle)
- whether the photo is original or manipulated

Without a VLM (vision-language model), this problem is unsolvable beyond ~30% accuracy.

## Realistic accuracy expectations

| Approach | claim_status | issue_type | object_part | severity |
|---|---|---|---|---|
| Random | 33% | 8% | 8% | 20% |
| Text-only (regex + lookup) | 25-35% | 10-20% | 30-40% | 15-25% |
| Single monolithic VLM call | 50-65% | 45-55% | 55-65% | 45-55% |
| Multi-stage pipeline + good VLM | 75-85% | 70-80% | 80-90% | 65-75% |
| Two-VLM consensus + pipeline | 80-90% | 75-85% | 85-92% | 70-80% |

Top finishers likely hit 85-92%. Our target: 80%+ on most columns.

## Our recommended architecture

**Multi-stage pipeline (Vision-Augmented)**:

```
INPUT ROW
    │
    ├──► [Stage 1] Text Extractor (regex + taxonomy)
    │    - extracts claimed_part, claimed_damage, multi_part, is_injection
    │    - handles romanized Hindi/Spanish/Chinese
    │
    ├──► [Stage 2] User History & Rules Loader
    │    - inherits risk flags from user_history.csv
    │    - maps evidence_requirements.csv rules
    │
    ├──► [Stage 3] Multi-Image VLM Auditor (Gemini Flash primary)
    │    - per-image VLM call (parallelizable)
    │    - extracts: object, part, damage, quality, is_original
    │
    ├──► [Stage 4] Decision Engine (deterministic rule-based)
    │    - aggregates visual findings
    │    - matches against claimed → supported/contradicted/not_enough_info
    │    - computes risk_flags (union of visual + history + claim_mismatch)
    │    - picks supporting_image_ids
    │    - infers severity from issue_type + magnitude
    │
    ├──► [Stage 5] Output Linter
    │    - enforces strict taxonomy
    │    - normalizes booleans, sorts lists
    │
    ▼
OUTPUT ROW (exact schema)
```

**Why this wins:**

1. **Deterministic reasoning** — the VLM acts purely as a feature extractor. All
   categorical decisions (status, severity, part) are made by auditable code, not VLM
   hallucination.
2. **Modular** — each stage can be improved independently. Can swap VLMs without touching
   decision logic.
3. **Testable** — each stage can be unit-tested with synthetic inputs.
4. **Cost-efficient** — text stages cost nothing, VLM stage caches aggressively.

## The three "winning-worthy" differentiators

(per the May 2026 champion 6c5ef1e + challenger f5ae46d patterns)

### 1. Robustness suite with synthetic + metamorphic tests
- 21+ adversarial cases (prompt injection, missing images, garbage input)
- Metamorphic invariants (swap image order, casing differences, etc.)
- All must pass before submission

### 2. Output audit script
- Schema validation (already in linter)
- Hallucination phrase detection ("I have approved", "guaranteed", etc.)
- Distribution sanity (no column is 100% one value)
- Documented in audit_report.md

### 3. Documentation stack (DESIGN.md + HARDENING_NOTES.md + OPERATIONAL.md)
- DESIGN.md: architecture explanation + trade-offs
- HARDENING_NOTES.md: hidden-test risks + mitigations
- OPERATIONAL.md: cost / latency / rate-limit analysis
- All three are read by the AI Judge

## What we cannot do without an API key

If no Gemini/OpenAI/Anthropic key is available at runtime:
- All visual stages must fall back to text-only heuristics
- Expected accuracy drops to ~30-40%
- Cannot win, but can produce a defensible submission
- **MUST** clearly document this in HARDENING_NOTES.md

If a key IS available (and we expect one for the actual run):
- Use Gemini 2.5 Flash as primary (cheap, fast, vision-capable)
- Cache aggressively by image hash
- Run with temperature=0 for determinism

## Our honest assessment vs top-tier competitors

**Disadvantages:**
- We use MiniMax-M3 (mid-tier reasoning model) for development
- Top competitors might use Opus 4.8 / GPT-5 via Claude Code / Cursor

**Advantages:**
- We will do multiple passes of design (this document is 5 passes)
- We will build robustness + audit + metamorphic tests (top 5% signal)
- We will write DESIGN + HARDENING + OPERATIONAL docs (top 5% signal)
- We will use deterministic reasoning where possible (no hallucination in decisions)

**Net assessment:** Top 10-15% is achievable. Top 5% requires:
- A working VLM at runtime
- Two-model reconciliation
- ≥85% sample accuracy
- 100% robustness pass rate

## What's in this research folder

```
agenthack_research/
├── 00_EXECUTIVE_SUMMARY.md                (this file)
├── pass1_problem/PROBLEM_DEEP_READ.md     (what the eval really scores)
├── pass2_data/DATA_AUDIT.md               (sample/test set characteristics)
├── pass2_data/audit_sample.py             (verifies sample ground truth)
├── pass3_architecture/ARCHITECTURE.md     (design options + chosen arch)
├── pass4_strategy/STRATEGY.md             (competitive landscape + differentiators)
├── pass5_implementation/ROADMAP.md        (concrete 1-day build plan)
└── artifacts/                             (concrete code/data to build)
```

## Next steps (after this research)

1. Read all 5 pass files (~30 minutes)
2. Agree on architecture
3. Begin Pass 5 implementation following the file structure
4. Build, test, audit, iterate

## The single-sentence pitch to the AI Judge

> "We built a multi-stage pipeline that separates visual feature extraction (VLM) from
> deterministic decision logic (rule engine), backed by a robustness suite that tests
> invariants, an output audit that catches hallucinations, and full DESIGN + HARDENING +
> OPERATIONAL documentation. Every categorical output is auditable in code, every model
> call is cached, every prompt is versioned, and every failure mode has a mitigation."