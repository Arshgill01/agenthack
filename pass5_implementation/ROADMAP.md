# Pass 5: Implementation Roadmap

## 5.1 Starting state

We have:
- `/Users/arshdeepsingh/Developer/hackerrank-orchestrate-june26/` — the cloned repo with
  anti-gravity's existing implementation (extractor.py, auditor.py, decision.py, etc.)
- `/Users/arshdeepsingh/Developer/agenthack_research/` — this research directory
- No API keys in environment

## 5.2 What we keep from anti-gravity

- `pipeline.py` — the orchestrator (clean structure)
- `linter.py` — schema enforcement (correct concept)
- `main.py` — CLI entry point (good)
- `evaluation/main.py` — evaluation runner (works)
- The overall multi-stage structure (extractor → auditor → decision → linter)

## 5.3 What we replace

- `extractor.py` — anti-gravity's regex is too thin. Add full taxonomy tables + multi-language
  romanized support + prompt-injection detection.
- `auditor.py` — replace regex fallback with a real VLM call (or graceful degradation when
  no API key). Needs AVIF support verified.
- `decision.py` — add the rule-based aggregation logic from Pass 3 §3.4.
- `model_client.py` — make it actually call VLMs (Gemini is installed!), with caching.
- `cache.py` — verify it works; add image-hash keying.

## 5.4 What we add (NEW)

### In code/
- `code/prompts/image_auditor_v1.txt` — VLM prompt template
- `code/prompts/image_auditor_v2.txt` — alternative prompt for two-model reconciliation
- `code/extraction/text_extractor.py` — full taxonomy + romanized language support
- `code/extraction/prompt_injection.py` — detect adversarial text
- `code/extraction/multi_part.py` — detect multi-part claims
- `code/vision/image_loader.py` — format detection (PIL + AVIF)
- `code/vision/feature_extractor.py` — VLM call wrapper
- `code/vision/feature_aggregator.py` — multi-image aggregation
- `code/decision/aggregator.py` — visual→claim match
- `code/decision/severity.py` — severity calibration
- `code/decision/risk_flags.py` — risk flag union logic
- `code/decision/supporting_images.py` — pick supporting_image_ids
- `code/audit/hallucination_check.py` — output phrase audit
- `code/audit/distribution_check.py` — distribution sanity
- `code/audit/schema_check.py` — already in linter, keep
- `code/audit/output_audit.py` — main audit runner

### In code/evaluation/
- `code/evaluation/sample_eval.py` — accuracy metrics on sample_claims.csv
- `code/evaluation/robustness_suite.py` — 21+ synthetic invariant tests
- `code/evaluation/metamorphic_suite.py` — order/casing/paraphrase invariants
- `code/evaluation/per_row_cost.py` — token + cost log

### Docs (in code/ or root)
- `code/DESIGN.md` — architecture explanation
- `code/HARDENING_NOTES.md` — hidden-test risk + how we addressed it
- `code/EVALUATION.md` — what the eval suite does and why
- `code/OPERATIONAL.md` — cost/latency analysis
- `code/README.md` — quickstart

### Logs (for AI Judge)
- The conversation log gets written to `~/hackerrank_orchestrate/log.txt`

## 5.5 Implementation order (1-day plan)

| Hour | Task | Owner |
|---|---|---|
| 1 | Verify Pillow+AVIF, install missing deps | |
| 1-2 | Build text_extractor with full taxonomy | |
| 2-3 | Build image_loader with format detection | |
| 3-4 | Build VLM feature extractor (Gemini Flash) with caching | |
| 4-5 | Build decision engine (aggregator + severity + risk flags) | |
| 5-6 | Build sample eval, run against sample_claims.csv | |
| 6-7 | Build robustness suite, fix issues | |
| 7-8 | Run on test set, audit output | |
| 8-9 | Write DESIGN.md, HARDENING_NOTES.md, README.md | |
| 9-10 | Final QA, package code.zip, generate output.csv | |

## 5.6 Verification gates

After each stage, we must pass:

1. After Stage 1: text_extractor outputs valid JSON for all 64 rows (sample + test)
2. After Stage 3: VLM returns valid JSON for at least 80% of images
3. After Stage 4: sample eval shows ≥70% accuracy on claim_status, ≥60% on issue_type
4. After audit: 0 severe warnings, schema valid

## 5.7 Failure modes to plan for

1. **No API key at runtime** → must degrade gracefully to text-only mode with disclaimer
2. **AVIF unsupported** → fall back to first-frame extraction or mark as valid_image=false
3. **VLM hallucinates damage** → decision engine cross-checks against claimed
4. **VLM refuses to answer** → mark as not_enough_information, manual_review_required
5. **Empty/missing image files** → mark as valid_image=false, not_enough_information
6. **Multi-part claim** → pick the part with strongest evidence

## 5.8 What success looks like

Concrete numbers we'd want to see:

| Metric | Target | Stretch |
|---|---|---|
| Sample claim_status accuracy | ≥80% | ≥90% |
| Sample issue_type accuracy | ≥75% | ≥85% |
| Sample object_part accuracy | ≥80% | ≥90% |
| Sample severity accuracy | ≥70% | ≥80% |
| Robustness suite pass rate | 100% | 100% |
| Metamorphic invariants | ≥90% | 100% |
| Audit severe warnings | 0 | 0 |
| Hallucinated phrases | 0 | 0 |
| Cost per test run | ≤$0.30 | ≤$0.15 |
| Latency per test run | ≤5 min | ≤2 min |

## 5.9 Risk to timeline

Most likely blockers:
- AVIF support missing from Pillow → 30 min to install pillow-avif-plugin
- No API key → entire pipeline needs fallback path (2 hrs)
- VLM returns non-JSON → robust parser needed (1 hr)
- VLM hallucinates taxonomy values → linter must normalize (30 min)

## 5.10 Definition of done

- [ ] `output.csv` has 44 rows + header, exact schema, exact column order
- [ ] `code/main.py` runs end-to-end without errors
- [ ] `code/evaluation/sample_eval.py` shows ≥70% accuracy on most columns
- [ ] `code/evaluation/robustness_suite.py` passes all synthetic tests
- [ ] `code/audit/output_audit.py` shows 0 severe warnings
- [ ] `code/DESIGN.md` explains architecture
- [ ] `code/HARDENING_NOTES.md` addresses hidden-test risks
- [ ] `code/README.md` explains quickstart
- [ ] `code.zip` packages only code/ (not data/, not __pycache__)
- [ ] `~/hackerrank_orchestrate/log.txt` has all conversation turns
- [ ] No hardcoded labels anywhere
- [ ] No secrets in source

## 5.11 What I'd skip if low on time

In order of skip priority:
1. Two-model reconciliation (Layer 3 feature, can drop)
2. Metamorphic suite (nice-to-have, robustness is critical)
3. Per-row cost tracking (nice-to-have, OPERATIONAL.md can be approximate)
4. Custom severity calibration (use simple rule)
5. Multi-language romanized dictionary (use generic tokenizer + fuzzy match)

Things we CANNOT skip:
1. Schema linter (validation will fail)
2. Robustness suite core (Judge looks for it)
3. DESIGN.md + HARDENING_NOTES.md (Judge reads these)
4. Output audit (Judge looks for it)
5. Caching (iteration speed)

## 5.12 The "wow factor" items

If we have spare cycles, these would impress the AI Judge:
1. `code/decision/confidence.py` — track per-decision confidence, low-confidence → escalate
2. `code/decision/explanation.py` — generate explanation graphs of why a decision was made
3. `code/eval/error_analysis.py` — categorize failure modes (visual mismatch, taxonomy
   mismatch, partial evidence, etc.)
4. `code/audit/diff_report.py` — compare two runs of output.csv, highlight differences
5. `code/prompts/prompt_versions.md` — track prompt iteration history

## 5.13 The integration test

Once everything is built, the integration test should:
1. Run `python3 code/main.py` end-to-end on sample_claims.csv → output_sample.csv
2. Run `python3 code/evaluation/sample_eval.py` → 70%+ accuracy, no failures
3. Run `python3 code/evaluation/robustness_suite.py` → 100% pass
4. Run `python3 code/audit/output_audit.py` → 0 severe warnings
5. Run `python3 code/main.py` end-to-end on claims.csv → output.csv (test)
6. Run `python3 code/audit/output_audit.py` on output.csv → 0 severe warnings

All in <5 minutes.

## 5.14 The deliverable artifact summary

```
code/
├── README.md                  # quickstart
├── DESIGN.md                  # architecture explanation
├── HARDENING_NOTES.md         # hidden-test risk + mitigation
├── OPERATIONAL.md             # cost/latency analysis
├── EVALUATION.md              # eval suite description
├── main.py                    # CLI entry point
├── pipeline.py                # orchestrator
├── extraction/
│   ├── __init__.py
│   ├── text_extractor.py      # regex + taxonomy
│   ├── prompt_injection.py    # adversarial text detector
│   └── multi_part.py          # multi-part claim detector
├── vision/
│   ├── __init__.py
│   ├── image_loader.py        # format detection
│   ├── feature_extractor.py   # VLM call wrapper
│   └── feature_aggregator.py  # multi-image aggregation
├── decision/
│   ├── __init__.py
│   ├── aggregator.py          # visual→claim match
│   ├── severity.py            # severity calibration
│   ├── risk_flags.py          # risk flag union
│   └── supporting_images.py   # pick supporting IDs
├── audit/
│   ├── __init__.py
│   ├── linter.py              # schema enforcement
│   ├── hallucination_check.py # phrase audit
│   ├── distribution_check.py  # sanity check
│   └── output_audit.py        # main audit runner
├── model_client.py            # VLM client (Gemini primary)
├── cache.py                   # SQLite cache
├── config.py                  # taxonomy definitions
├── prompts/
│   ├── image_auditor_v1.txt   # primary VLM prompt
│   └── image_auditor_v2.txt   # alternative prompt
└── evaluation/
    ├── main.py                # entry point
    ├── sample_eval.py         # accuracy metrics
    ├── robustness_suite.py    # 21+ invariant tests
    ├── metamorphic_suite.py   # order/casing invariants
    └── per_row_cost.py        # token + cost log
```

That's the target. ~25 files, ~1500 lines total, well-organized, fully tested.