# Operational & Evaluation Report

## Metrics on `dataset/sample_claims.csv`

- **Total Claims Evaluated:** 20
- **Claim Status Accuracy:** 95.00%
- **Object Part Accuracy:** 95.00%
- **Issue Type Accuracy:** 85.00%
- **Severity Accuracy:** 90.00%
- **Evidence Standard Met Accuracy:** 100.00%
- **Valid Image Accuracy:** 100.00%
- **Risk Flags Exact Match Accuracy:** 45.00%
- **Risk Flags Avg Jaccard Similarity:** 0.6043

### Confusion Matrix (Claim Status)
| Expected \ Predicted | Supported | Contradicted | Not Enough Info |
|---|---|---|---|
| **Supported** | 12 | 1 | 0 |
| **Contradicted** | 0 | 5 | 0 |
| **Not Enough Info** | 0 | 0 | 2 |


### Per-Class Performance
| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| Supported | 100.00% | 92.31% | 0.9600 | 13 |
| Contradicted | 83.33% | 100.00% | 0.9091 | 5 |
| Not Enough Information | 100.00% | 100.00% | 1.0000 | 2 |


### Performance Breakdown by Object Type
| Object Type | Claims | Claim Status Acc | Object Part Acc | Issue Type Acc | Severity Acc |
|---|---|---|---|---|---|
| Car | 8 | 87.50% | 100.00% | 75.00% | 87.50% |
| Laptop | 6 | 100.00% | 100.00% | 100.00% | 100.00% |
| Package | 6 | 100.00% | 83.33% | 83.33% | 83.33% |


### Blind-vs-Aware VLM Audit Agreement Statistics
| Agreement Category | Count | Percentage |
|---|---|---|
| Agree | 14 | 70.00% |
| Disagree Different Damage | 3 | 15.00% |
| Reconciled Resolved | 3 | 15.00% |


## Configuration Details & Strategy

- **Final Strategy:** 3-Pass VLM Pipeline with Confidence-Gated CoT Self-Correction (EGDCA).
- **Model:** `gemini-3.5-flash` via Vertex AI REST API.
- **Passes:** (1) Blind audit — zero claim context, (2) Aware audit — full context + evidence checklist rubric, (3) CoT Reconciler — fires on blind/aware disagreement (~15-25% of claims).
- **Caching:** SQLite database keyed on prompt+image content hash. Prevents redundant API calls during iteration.

## Operational Analysis (Actual Measured API Usage)

- **Number of Actual API Calls (20 sample claims):**
  - VLM Image Audit calls: 43 (20 blind + 20 aware + 3 reconciler)
  - Text Extraction calls: 20
- **Actual Measured API Token Usage:**
  - VLM Input Tokens: 144,099
  - VLM Output Tokens: 13,399
  - Text Input Tokens: 10,320
  - Text Output Tokens: 681
- **Number of Images Processed:** 29
- **Actual Cost for this Run:** $0.016 (pricing: input=$0.075/1M, output=$0.30/1M)
- **Estimated Cost per Claim:** ~$0.0008 (sample set) — scales to ~$0.035 for 44 test claims
- **Approximate Latency:** ~2.5 seconds per claim (live API); ~0.01s with cache hit
- **TPM/RPM Strategy:** Exponential backoff with jitter on 429/503 errors. No batching — sequential processing is sufficient for 44 claims within rate limits.
