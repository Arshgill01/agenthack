# Pass 4: Strategy & Winning Differentiators

## 4.1 What we know about evaluation

From the May 2026 evaluation_criteria.md (the only public criteria we have):

1. **Agent Design (architectural)** — clean separation, corpus use, escalation, determinism,
   hygiene
2. **AI Judge Interview** — depth, trade-offs, failure modes, honesty about AI
3. **Output CSV** — per-row column accuracy, no hallucination
4. **AI Fluency (chat transcript)** — clear scoped prompts, critiquing, driving the AI

The eval criteria probably carries over: design + interview + output + transcript.

This means winning is a multi-dimensional game:
- A clever architecture alone won't win (output matters most)
- High accuracy alone won't win (interview + design matter)
- Beautiful code alone won't win (output matters)

## 4.2 The realistic win conditions

We can't actually predict the hidden test labels. The grader runs our CSV against ground
truth and scores. So we need to maximize expected per-column accuracy.

Given the 44 test rows:
- Random baseline accuracy: ~3-10% per categorical column
- Text-only (regex + lookup) baseline: ~30-40% on easy fields (object_part),
  ~20% on claim_status, ~10% on issue_type
- Single-VLM-prompt-per-row: ~50-65% on most fields
- Multi-stage pipeline + good VLM: ~75-85% on most fields
- Two-VLM consensus + good pipeline: ~80-90%
- Top 5 finishers: probably 85-92%

## 4.3 What the prior winners did right (champion 6c5ef1e)

From the May 2026 champion checklist:
- 100% accuracy on sample (10/10 rows)
- 21/21 robustness invariants passed
- 5/5 pytest tests passed
- 0 severe audit warnings
- HARDENING_NOTES.md explicitly addressing hidden-test risk
- DESIGN.md with architecture explanation
- README.md with reproducible commands

The champion's score: top tier. Their approach was conservative and well-tested.

## 4.4 What the challenger (f5ae46d) added

The challenger had multi-view retrieval + metamorphic testing:
- 44/44 metamorphic cases passed
- Same final output (status, request_type, product_area) but better retrieval evidence
- More thorough than the champion in retrieval coverage

## 4.5 What the june challenge specifically rewards

Reading problem_statement.md + May eval criteria together:

The June challenge is a vision task, but the *evaluation framework* is the same:
- Architecture + design quality (40%?)
- Output accuracy (40%?)
- AI Judge interview (10%?)
- Chat transcript (10%?)

So we need both architecture AND accuracy.

## 4.6 The differentiation strategy

Three layers of differentiation:

### Layer 1: Solid baseline (everyone will do this)
- Multi-stage pipeline
- VLM call per image
- Rule-based decision engine
- Schema linter

### Layer 2: Above-and-beyond (top 20%)
- Two-model reconciliation
- Caching layer with deterministic re-runs
- Robustness suite with synthetic + metamorphic tests
- Output audit script

### Layer 3: Winning-worthy (top 5%)
- Custom-trained classifier for issue_type (use sklearn on extracted features)
- Vision-language ensemble (different prompts, different temperatures)
- Severity calibration (trained regression on visual features)
- Comprehensive DESIGN + HARDENING + AUDIT docs

I think for the June challenge, we can land at Layer 2 with strong Layer 3 elements, which
should put us in top 10%. To get top 5%, we need Layer 3 fully.

## 4.7 Cost / latency optimization for the AI Judge

The AI Judge will ask: "Did you think about cost? Latency? Rate limits?"

Answers we can give:
- "Per-row token usage: 2 images × ~500 tokens input + 200 output = 1400 tokens/row.
  Total: 44 rows × 1400 tokens = ~62K tokens.
- Cost: at Gemini Flash pricing ($0.075/1M input, $0.30/1M output), ~$0.005 per row,
  ~$0.22 total for test set.
- Sample set: 20 rows × 1400 = 28K tokens, ~$0.10.
- Latency: parallel calls per image (8-16 concurrent) → ~2-3 minutes for test set.
- Caching: SQLite keyed by image hash, gives 100x speedup on repeat runs.
- Rate limits: 15 RPM on Gemini free tier, easily within bounds for our 44-row test.
  For higher volume we'd use exponential backoff and request batching."

## 4.8 What we'd specifically AVOID

- Hardcoding any test labels (disqualifying)
- Single monolithic VLM call (hard to debug, hard to test, prone to hallucination)
- Live web scraping (forbidden)
- Open-ended multi-agent debate (expensive, slow)
- Using API keys in source code (disqualifying)
- Skipping the eval/audit/hardening docs (loses points on AI Judge interview)

## 4.9 The "winning path" execution order

Assuming 24-hour hackathon, prioritized:

| Hour | Activity | Output |
|---|---|---|
| 0-2 | Read problem, audit data, design (THIS PASS) | DESIGN.md v0 |
| 2-4 | Implement Stage 1-5 skeleton with fallback | code/ directory |
| 4-6 | Wire VLM, iterate on prompt engineering | output.csv v1, ~50% accuracy |
| 6-8 | Tune decision engine rules, fix taxonomy issues | output.csv v2, ~65% accuracy |
| 8-10 | Build robustness + audit + tests | code/evaluation/ |
| 10-12 | Two-model reconciliation (optional) | output.csv v3, ~75% |
| 12-14 | Run on full test set, fix any issues | output.csv v4 |
| 14-16 | Polish DESIGN + HARDENING + AUDIT docs | docs/ |
| 16-18 | Self-review, simulated AI Judge questions | notes for interview |
| 18-20 | Final dry-run, package code.zip | submission_artifacts/ |
| 20-22 | Buffer for issues, final QA | |
| 22-24 | Rest before interview | |

If we have 24 hours, we can land in Layer 2 with strong Layer 3. Top 5% should be possible.

## 4.10 The AI Judge interview prep

Likely questions:
1. Why multi-stage vs single VLM call?
2. How did you handle the format discrepancies (AVIF/WEBP)?
3. How do you handle the no-API-key case?
4. Why these risk_flags? Show your taxonomy mapping.
5. How did you avoid hardcoding test labels?
6. What would you improve with more time?
7. What failure modes did you consider?
8. How do you handle prompt injection?
9. Walk me through a specific row.
10. What does your decision engine do that the VLM alone can't?

We need concise answers backed by code/docs. The HARDENING_NOTES.md + DESIGN.md + AUDIT.md
give the Judge material to read, then they ask follow-ups.

## 4.11 The "secret" differentiator

What most participants WON'T do:
- Build a synthetic test set that mimics the real test distribution
- Run metamorphic tests (invariants) on every change
- Audit output for hallucinated phrases
- Document hidden-test risk explicitly
- Two-model reconciliation
- Per-row cost/latency tracking

These are all cheap to do and signal "I drove the AI" to the Judge.

## 4.12 The honest truth about our position

We are using MiniMax-M3, which is a moderate-tier model. Top-tier participants might use
Opus 4.8 / GPT-5 via Claude Code. We CANNOT match raw VLM accuracy.

BUT: VLM accuracy depends mostly on:
- Prompt quality (we control this)
- Stage decomposition (we control this)
- Decision logic (we control this, deterministic)

The model matters less than the prompt + pipeline + logic. A multi-stage pipeline with
clear prompts will outperform a single huge prompt even with a weaker model.

Our differentiator must be: **smarter decomposition, better prompts, better logic, better
testing**. Not raw model power.

## 4.13 Concrete proposal

Implement these in priority order:

1. **Stage 1-5 skeleton** with anti-gravity's structure as starting point
2. **Robustness suite** that mimics the May 2026 champion's pattern
3. **Output audit script** with hallucination checks
4. **DESIGN.md** explaining architecture and trade-offs
5. **HARDENING_NOTES.md** explaining hidden-test risk
6. **Per-stage prompt files** in code/prompts/
7. **Caching layer** for repeatability
8. **Two-model reconciliation** if budget allows
9. **Per-row cost/latency log** as part of evaluation

## 4.14 The killshot for AI Judge interview

If asked "what makes this winning-worthy?":

> "We built a multi-stage pipeline that separates visual feature extraction from decision
> logic. The VLM acts purely as a per-image feature extractor; a deterministic rule engine
> makes the final call. This means no hallucinations in the categorical outputs — every
> decision is auditable in code. We have a 21+ case robustness suite that tests invariants
> (image-order swap, prompt-injection resistance, empty-image handling) and a hallucination
> audit that scans output for unsupported phrases. We document hidden-test risk in
> HARDENING_NOTES.md. We cache VLM outputs by image hash, so iteration is fast and
> deterministic. And we explicitly consider cost, latency, and rate limits in DESIGN.md."

That's the killer pitch. It works whether or not our raw accuracy is top-tier.