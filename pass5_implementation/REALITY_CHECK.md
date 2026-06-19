# Pass 6: Environment Reality Check & Revised Strategy

## 6.1 The hard truth about this environment

Verified in shell on 2026-06-19:

| Resource | Status |
|---|---|
| Python 3.9.12 | ✓ Available |
| Pillow 11.3.0 | ✓ Installed (handles AVIF natively!) |
| `google-generativeai` 0.8.6 | ✓ Installed (deprecated but works) |
| `google-genai` | ✗ Not installed (can install) |
| `requests` | ✓ Installed |
| **GEMINI_API_KEY** env var | ✗ Not set |
| OPENAI_API_KEY env var | ✗ Not set |
| ANTHROPIC_API_KEY env var | ✗ Not set |
| Ollama | ✓ Installed but not running, no models downloaded |
| Local vision model | ✗ None available |
| Existing anti-gravity code | ✓ Present in repo |

**Implication**: At development time, the pipeline CANNOT make real VLM calls. We need:

1. **A robust text-only / fallback path** that produces defensible output without a VLM
2. **A VLM path** that activates when an API key is provided
3. **Self-documentation** that explains which path ran and why

## 6.2 What this means for winning strategy

Without a working VLM at runtime, our accuracy ceiling is ~30-40%. We will NOT win on raw
accuracy. We can still compete on:

1. **Engineering quality** (clean multi-stage pipeline)
2. **Documentation quality** (DESIGN.md, HARDENING_NOTES.md, OPERATIONAL.md)
3. **Testing rigor** (robustness suite, metamorphic tests, output audit)
4. **AI Judge interview** (we can explain the architecture deeply, show we thought about
   cost/latency, show we considered failure modes)
5. **Code craftsmanship** (separation of concerns, deterministic reasoning)

If the user has API keys they'll plug in at submission time, the VLM path will activate and
accuracy jumps to ~80%. The code is ready for that.

## 6.3 The realistic deliverable scope

Given the constraints, here's what we can confidently build in ~6 hours:

### Tier A: must-have (always achievable)
- [x] Multi-stage pipeline skeleton (already from anti-gravity, restructure)
- [x] Text extractor with full taxonomy + romanized language support
- [x] Image loader with AVIF/JPEG/PNG/WEBP support (PIL works)
- [x] Fallback path: when no API key, produce best-guess output from text + heuristics
- [x] Decision engine with rule-based aggregation (works without VLM)
- [x] Linter with strict taxonomy enforcement
- [x] Sample evaluator that runs against sample_claims.csv
- [x] Robustness suite (21+ synthetic tests)
- [x] Output audit script (schema + hallucination phrases)
- [x] DESIGN.md, HARDENING_NOTES.md, OPERATIONAL.md, EVALUATION.md, README.md
- [x] Per-row cost/latency tracking (zeros for fallback path)
- [x] Caching layer (useful even for fallback — caches text extractions)

### Tier B: high-value if achievable
- [ ] Real Gemini VLM call when API key is provided
- [ ] Per-image VLM audit
- [ ] Two-model reconciliation (if budget allows)
- [ ] Metamorphic test suite (order, casing, paraphrase)
- [ ] Confidence calibration per-decision

### Tier C: nice-to-have
- [ ] Custom severity regression model
- [ ] Per-row log files for debugging
- [ ] Output diff tool (compare two runs)

## 6.4 What we will NOT do (out of scope)

- Live web scraping or external API calls beyond Gemini (forbidden)
- Hardcoded test labels (disqualifying)
- Multi-agent debate framework (too expensive, too slow)
- Custom-trained neural net from scratch (no training data, no time)
- GUI / dashboard (terminal-only per spec)

## 6.5 The "fallback path" is actually a feature

The text-only fallback path is what runs when no API key is available. It should:

1. Extract claimed_part, claimed_damage from user_claim using regex + lookup tables
2. Load user_history and apply risk flag inheritance
3. Try to load images — if all images fail to load, mark valid_image=false
4. Apply heuristics:
   - If claimed_part mentions color (blue car) → keep it, note color in justification
   - If multi_part claim → pick the first mentioned part for object_part
   - If prompt_injection → set text_instruction_present risk flag
5. Set defaults:
   - claim_status: "not_enough_information" (conservative)
   - issue_type: "unknown"
   - object_part: claimed_part
   - severity: "unknown"
   - evidence_standard_met: false (we couldn't verify without VLM)
   - valid_image: depends on image load success
6. Apply user_history risk flags
7. Add manual_review_required if user history says so or if injection detected

This is honest, defensible, and won't get us disqualified. It clearly says "we couldn't
verify without vision, escalating to manual review."

## 6.6 The "happy path" when API key is present

The VLM path is layered on top:

1. Per image: call Gemini Flash with image_auditor_v1_prompt
2. Parse JSON response (with fallback parser for malformed)
3. Cache response by image hash
4. Aggregate findings (best image wins)
5. Decision engine uses real visual evidence
6. Higher accuracy (~80%)

## 6.7 The architecture supports both paths cleanly

```
INPUT ROW
    │
    ├──► [Stage 1] Text Extractor (always)
    │
    ├──► [Stage 2] User History Loader (always)
    │
    ├──► [Stage 3] Image Loader (always) — just confirms files exist + readable
    │
    ├──► [Stage 3.5] VLM Auditor (only if API key)
    │    if no API key: skip, set visual evidence = unknown
    │
    ├──► [Stage 4] Decision Engine (always, but uses different inputs)
    │    if VLM available: use visual evidence
    │    if not: use heuristics + text only
    │
    ├──► [Stage 5] Linter (always)
    │
    ▼
OUTPUT ROW
```

## 6.8 The user's options

After this research, the user has 3 paths:

### Path A: Build Tier A only (4-6 hours)
- Clean, defensible, well-documented
- Fallback-only accuracy (~30-40%)
- Top 30-40% placement likely
- No API key needed at runtime

### Path B: Build Tier A + VLM-ready Tier B (8-10 hours)
- Same as Path A + the VLM path that activates if API key is provided
- With API key: 70-85% accuracy
- Without API key: same as Path A
- Top 10-20% placement if key is used at submission

### Path C: Build Tier A + B + C (14-16 hours)
- Everything including metamorphic + two-model reconciliation
- Top 5-10% placement
- Requires API key for best results

**Recommendation**: Path B is the sweet spot. Build the foundation robustly so it works
without an API key, but be ready to plug one in if available.

## 6.9 The "winning-worthy" differentiators we WILL achieve

Even with Path A only, we will have:

1. **Multi-stage pipeline with deterministic decision logic** — better than most participants
2. **Comprehensive taxonomy handling** — including romanized multilingual
3. **Prompt-injection detection** — explicitly called out in sample outputs
4. **Robustness suite with 21+ invariant tests** — May 2026 champion pattern
5. **Output audit with hallucination detection** — top 5% pattern
6. **DESIGN.md + HARDENING_NOTES.md + OPERATIONAL.md** — Judge reads these
7. **Caching layer with image hashing** — fast iteration, deterministic
8. **Per-row cost/latency tracking** — Judge asks about this
9. **Graceful fallback path** — when no API key, doesn't crash

## 6.10 The minimum bar to clear

To be competitive (top 30%), we need:

- [ ] Pipeline runs end-to-end on sample_claims.csv producing valid output
- [ ] All 64 rows (20 sample + 44 test) produce schema-valid output
- [ ] At least 5/20 sample rows match expected output on claim_status
- [ ] Zero severe audit warnings
- [ ] Robustness suite passes all tests
- [ ] DESIGN.md, HARDENING_NOTES.md, README.md present and substantive

To be strong (top 10%), we add:

- [ ] 12/20 sample rows match on claim_status
- [ ] 8/20 sample rows match on issue_type
- [ ] 10/20 sample rows match on object_part
- [ ] Per-row cost report generated
- [ ] VLM path activates when API key provided

To be winning-worthy (top 5%), we add:

- [ ] 17/20 sample rows match on claim_status
- [ ] 14/20 sample rows match on issue_type
- [ ] Two-model reconciliation implemented
- [ ] Confidence calibration per-decision
- [ ] Hallucination audit catches real issues

## 6.11 The honest final assessment

If we execute Path B well (10 hours of focused work), we have a real chance at top 10-15%.
This requires:

- Strict focus on schema correctness (linter is bulletproof)
- Solid text extraction (handles all the romanized multilingual cases)
- Working fallback path (defensible when no API key)
- Robustness + audit + docs (the "we thought about this" signal)
- Clean multi-stage architecture (the "we designed this well" signal)

If we want top 5%, we need:
- Working VLM at runtime (so user must provide key at submission)
- Two-model consensus (catches edge cases single-model misses)
- Sample accuracy ≥85% (which requires the VLM to be working well)

**This is achievable if the user is willing to provide an API key at runtime.** Otherwise,
we compete on architecture + docs + testing + AI Judge interview, which gets us top 20-30%.