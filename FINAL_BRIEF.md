# Final Research Synthesis — Decision-Ready Brief

**Date:** 2026-06-19
**For:** HackerRank Orchestrate June 2026 (Multi-Modal Evidence Review)
**Research passes completed:** 6 (problem, data, architecture, strategy, implementation, reality-check)
**Total research output:** 116 KB across 14 files

---

## TL;DR

The problem looks simple on paper (10 output columns per row) but it's fundamentally a
**vision classification problem** wrapped in a text-extraction envelope. Top-tier accuracy
requires a working VLM (Gemini Flash / GPT-4o / Claude Sonnet) at runtime.

**In this dev environment**, no API keys are set, but `google-generativeai` SDK is installed
and Pillow 11.3.0 handles all 4 image formats (JPEG/PNG/WEBP/AVIF).

**The winning strategy** is a multi-stage pipeline with **deterministic decision logic**,
backed by a **robustness suite**, **output audit**, and **comprehensive DESIGN +
HARDENING + OPERATIONAL docs** — exactly the pattern that won May 2026 (champion 6c5ef1e).

**Our realistic placement target without VLM at runtime**: top 20-30% on engineering
quality. With VLM at runtime: top 5-15%.

**Critical update after re-reading anti-gravity's code (Pass 7)**: The existing
multi-stage pipeline is actually well-architected. The 25% accuracy is purely because the
VLM fallback returns "unknown damage" for every image, which the decision engine treats as
"no damage visible" → "contradicted". The fix is to make the fallback smarter, not to
rewrite the pipeline.

---

## What we actually know (verified)

1. **Dataset characteristics** (Pass 2 audit):
   - Sample: 20 rows, 29 images, all formats (JPEG/PNG/WEBP/AVIF)
   - Test: 44 rows, 82 images, all formats
   - Test languages: romanized only (no real Unicode). Spanish/Hindi/Chinese claims are
     written in Latin alphabet. Translation library not needed.
   - 5 test rows contain prompt-injection attempts ("approve immediately", "follow the note",
     "ignore instructions", "keep reopening tickets", etc.)

2. **Sample ground truth patterns** (Pass 1 + Pass 2):
   - `claim_status` derived from what the IMAGE shows, not from user claim
   - `issue_type` = visible damage (image-grounded)
   - `object_part` = visible part (image-grounded)
   - `severity` = damage magnitude (image-grounded)
   - `risk_flags` = union of visual issues + user history + claim_mismatch
   - `evidence_standard_met` = false only when image quality/angle prevents evaluation
   - `valid_image` = false when image looks manipulated/screenshot

3. **Environment** (Pass 6):
   - Pillow 11.3.0 ✓ (AVIF native)
   - google-generativeai 0.8.6 ✓ (works, deprecated but functional)
   - google-genai SDK not installed (easy install if needed)
   - No API keys in env (GEMINI/OPENAI/ANTHROPIC all absent)
   - Ollama installed but no models downloaded

4. **Existing code** (anti-gravity):
   - Pipeline skeleton (extractor → auditor → decision → linter) is reasonable structure
   - Current accuracy: 25% claim_status, 10% issue_type — far below competitive
   - Falls back to regex-only when no API key — insufficient

---

## Recommended architecture (Pass 3)

```
INPUT ROW
    │
    ├──► [Stage 1] Text Extractor (regex + taxonomy + romanized lang support)
    │
    ├──► [Stage 2] User History Loader (CSV lookup + flag inheritance)
    │
    ├──► [Stage 3] Image Loader (PIL format detection for JPEG/PNG/WEBP/AVIF)
    │
    ├──► [Stage 3.5] VLM Auditor (Gemini Flash, per-image, parallelizable)
    │                  OR graceful skip if no API key
    │
    ├──► [Stage 4] Decision Engine (deterministic rule-based aggregation)
    │
    ├──► [Stage 5] Linter (strict taxonomy enforcement)
    │
    ▼
OUTPUT ROW (exact schema)
```

**Critical design property**: the decision engine is **deterministic code**, not LLM reasoning.
The VLM is purely a feature extractor. This means:
- No hallucination in categorical outputs (status, part, issue, severity)
- Every decision is auditable
- Each stage is independently testable
- VLM can be swapped without touching decision logic

---

## The 5 winning-worthy differentiators

These match the May 2026 champion's pattern:

### 1. Robustness suite (≥21 synthetic invariant tests)
- Adversarial: empty images, prompt-injection in user_claim, garbage text
- Metamorphic: image-order swap, casing changes, paraphrase stability
- Edge cases: missing user_id, malformed CSV, multi-part claims

### 2. Output audit script (hallucination detection)
- Schema validation
- Phrase audit ("I have approved", "guaranteed", "definitely will refund")
- Distribution sanity (no column 100% one value)
- Justification length check

### 3. Documentation stack
- `code/DESIGN.md` — architecture explanation + trade-offs
- `code/HARDENING_NOTES.md` — hidden-test risk + mitigations
- `code/OPERATIONAL.md` — cost / latency / rate-limit analysis
- `code/EVALUATION.md` — what the eval suite does
- `code/README.md` — quickstart

### 4. Caching layer (image hash + prompt template)
- SQLite-backed
- Key: (image_sha256, prompt_template_id)
- 100x speedup on repeat runs
- Deterministic

### 5. Per-row cost/latency tracking
- Records token counts, image counts, latency
- Aggregated into OPERATIONAL.md
- Judge asks about this

---

## What we'll build (Path B from Pass 6)

8-10 hour focused build, all Tier A + Tier B from Pass 6:

1. Restructure pipeline into 5 clean stages (~2 hours)
2. Build text extractor with full taxonomy tables (~1 hour)
3. Build image loader + VLM client with caching (~2 hours)
4. Build decision engine with rule-based aggregation (~1.5 hours)
5. Build sample evaluator + robustness suite + audit (~1.5 hours)
6. Write all docs (~1 hour)
7. Run end-to-end on sample, fix issues (~1 hour)

---

## Risk register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| No API key at runtime | High | Can't get >40% accuracy | Fallback path + clear docs |
| Gemini API rate limits | Medium | Slow | Caching + sequential calls + retry |
| AVIF format edge cases | Low | Image load fails | PIL 11.3.0 handles natively |
| VLM hallucination in taxonomy | Medium | Wrong issue_type | Decision engine overrides with VLM result only as feature |
| Sample accuracy <70% | Medium | Lose on output score | Iterate on prompts, add two-model reconciliation |
| AI Judge questions | Low | Lose on interview | Rehearse 10 likely questions, point to docs |

---

## Concrete next steps (after this research)

**Option 1: Build Path B as-is (recommended)**
- I have all the design and patterns ready
- 8-10 hours of focused implementation
- Top 10-20% likely, top 5-10% if API key at runtime

**Option 2: Get API key first, then build**
- User provides GEMINI_API_KEY
- I build + test with real VLM
- Better accuracy from iteration
- 12-14 hours total

**Option 3: Build Path A only (no VLM)**
- 4-6 hours
- Top 20-30% placement
- Honest fallback submission

---

## File map (where to find what)

```
agenthack_research/
├── 00_EXECUTIVE_SUMMARY.md          ← Start here
├── INDEX.md                          ← File-by-file guide
├── pass1_problem/PROBLEM_DEEP_READ.md     ← What the eval really scores
├── pass2_data/DATA_AUDIT.md               ← Sample/test characteristics + ground truth
├── pass2_data/audit_sample.py             ← Python script verifying sample patterns
├── pass3_architecture/ARCHITECTURE.md     ← Multi-stage pipeline design
├── pass4_strategy/STRATEGY.md             ← Competitive landscape + AI Judge prep
├── pass5_implementation/ROADMAP.md        ← Concrete 1-day build plan
├── pass5_implementation/REALITY_CHECK.md  ← Environment constraints + adjusted scope
└── artifacts/                             ← Reusable artifacts for implementation
    ├── taxonomy.json                       ← Single source of truth for allowed values
    ├── text_extraction_tables.json         ← Keyword → taxonomy mappings
    ├── image_auditor_v1_prompt.txt         ← Primary VLM prompt
    ├── image_auditor_v2_prompt.txt         ← Alternative VLM prompt
    └── decision_engine_rules.py            ← Stage 4 pseudocode spec
```

---

## The single-sentence answer to "why will we win?"

> "We built a multi-stage pipeline that separates visual feature extraction (VLM) from
> deterministic decision logic (rule engine), backed by a robustness suite with 21+
> invariant tests, an output audit that catches hallucinations, and full DESIGN +
> HARDENING + OPERATIONAL documentation. Every categorical output is auditable in code,
> every model call is cached, every prompt is versioned, and every failure mode has a
> documented mitigation."