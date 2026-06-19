# Pass 7: Re-Assessment After Reading Anti-Gravity Code

## 7.1 What anti-gravity actually built (deeper look)

After reading the actual code files, my prior assessment was partially wrong. The code is
more sophisticated than the 25% accuracy suggested. Let me re-evaluate:

### What's actually good:

1. **`code/extractor.py`** (199 lines):
   - LLM-based primary extraction with prompt engineering
   - Comprehensive fallback regex covering all 3 object types
   - Handles Hindi romanized ("bumper ke upar", "bumper ke piche"), Spanish romanized,
     missing cases
   - Severity heuristic (high/medium/low) from keywords
   - JSON cleaning + taxonomy validation

2. **`code/auditor.py`** (148 lines):
   - VLM call per image with detailed prompt
   - 10 risk categories explicitly listed in prompt
   - Original photo detection
   - Graceful fallback when VLM fails
   - Per-image JSON normalization

3. **`code/decision.py`** (236 lines):
   - Sophisticated rule-based aggregation
   - User history inheritance
   - Wrong_object, wrong_object_part detection
   - Damage mismatch detection (scratch vs dent, etc.)
   - Cropped/obstructed handling for contents missing claim
   - Multiple supporting image IDs logic
   - Justification text generation

4. **`code/linter.py`** + **`code/pipeline.py`** + **`code/main.py`**:
   - Clean schema enforcement
   - End-to-end orchestration with error isolation

### Why it scores 25%:

The bottleneck is **Stage 3 (VLM auditor)**. When no API key is present:
- `call_vlm_model` returns empty string
- JSON parsing fails
- Exception caught → fallback runs
- Fallback returns `valid_call=False`, all images as `detected_risks=["manual_review_required"]`
- All claims get defaulted to "manual_review_required" with unknown damage

The decision engine then can't tell supported from contradicted, so it defaults to
"contradicted" or "not_enough_information" for everything.

### The single biggest improvement opportunity:

**Make the fallback path actually useful.** When no VLM is available:
- Use text-only heuristics to make educated guesses
- Don't default to "manual_review_required" for every claim
- Use regex on the claim text to determine likely issue_type
- Use keyword density for severity

This alone could lift accuracy from 25% to 40-50%.

## 7.2 Re-evaluated strategy

Given the existing code is solid in structure, the optimal move is **NOT to rewrite from
scratch**. Instead:

1. **Enhance the fallback path** in `auditor.py` and `extractor.py`
2. **Add caching** that survives across runs (SQLite-backed)
3. **Add prompt-injection detection** in the extractor
4. **Build the robustness + audit suite** that the May 2026 champion had
5. **Write DESIGN.md + HARDENING_NOTES.md + OPERATIONAL.md**
6. **Add per-row cost/latency tracking**
7. **Test two-model reconciliation** if budget allows

Estimated effort: 4-6 hours for Tier A, 8-10 hours for Tier A + B.

## 7.3 The truly winning-worthy move

The May 2026 champion won not by having the best raw model — they won by having:
1. Clean deterministic pipeline
2. Robustness suite with 21+ invariant tests
3. Output audit script
4. HARDENING_NOTES.md explaining hidden-test risk
5. DESIGN.md explaining architecture
6. All numbers in their README to back up the claims

Anti-gravity has #1 partially. Missing: #2-6.

Adding #2-6 in 4 hours would put us in top 10-20%.

## 7.4 Revised realistic accuracy

| Scenario | claim_status | issue_type | object_part | severity |
|---|---|---|---|---|
| Anti-gravity current (no VLM) | 25% | 10% | 10% | 10% |
| Anti-gravity + smart fallback (no VLM) | 45% | 35% | 40% | 30% |
| Anti-gravity + smart fallback + prompt tuning | 55% | 45% | 50% | 40% |
| Anti-gravity + Gemini Flash VLM | 75-85% | 70-80% | 80-90% | 70-80% |
| Anti-gravity + two-model consensus | 80-90% | 75-85% | 85-92% | 75-85% |

The smart fallback gets us ~45% claim_status. That's better than current but still not
competitive on raw accuracy. It's enough to land in top 30%, not top 10%.

## 7.5 What we should actually do (revised plan)

Phase 1 (2 hours) — Quick wins:
- Fix the audit fallback to be useful (use heuristics, not just manual_review)
- Add caching by image hash
- Add prompt-injection detection
- Verify AVIF loading works

Phase 2 (2 hours) — Make it auditable:
- Build robustness_suite.py with 21+ synthetic tests
- Build audit_output.py with hallucination + distribution checks
- Run sample eval, measure baseline

Phase 3 (1 hour) — Documentation:
- Write DESIGN.md explaining the architecture
- Write HARDENING_NOTES.md explaining hidden-test risks
- Write OPERATIONAL.md with cost/latency analysis
- Update README.md

Phase 4 (1 hour) — Polish:
- Run on full test set
- Generate final output.csv
- Package code.zip
- Validate everything

Total: 6 hours of focused work. Lands us in top 20-30% without VLM, top 10-15% with VLM.

## 7.6 The killer insight we discovered

Anti-gravity's decision engine is actually really good at handling the EDGE CASES that
the sample data shows:
- case_008: user said hood, image shows front bumper → wrong_object_part detected
- case_014: user said damaged, image shows clean → damage_not_visible detected
- case_018: missing contents claim with cropped image → special handling
- case_019: wrong object in image → wrong_object + claim_mismatch
- case_020: text instruction in image + user history risk → all detected

The decision engine is the **moat**. The vision layer is the weak point. So our
optimization should be:
1. Keep the decision engine mostly as-is
2. Improve the vision layer fallback
3. Add the engineering rigor around it (testing, docs, audit)

## 7.7 Final recommendation

Build on top of anti-gravity's existing work. Add:

1. **Smart fallback for vision** (when no VLM key) — use heuristics + image metadata
2. **Caching layer** for repeatability
3. **Robustness suite** (21+ synthetic tests)
4. **Output audit** (hallucination detection)
5. **Documentation** (DESIGN + HARDENING + OPERATIONAL + README)
6. **Per-row cost/latency** tracking
7. **Two-model reconciliation** if API key available

Don't:
- Rewrite the pipeline from scratch
- Change the output schema
- Hardcode any test labels
- Use any model other than Gemini Flash for cost reasons

Expected outcome:
- Without VLM at runtime: 45-55% sample accuracy, top 20-30% placement
- With VLM at runtime: 75-85% sample accuracy, top 5-10% placement

This is achievable in 6 hours of focused work.