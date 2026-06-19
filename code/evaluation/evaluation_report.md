# Operational & Evaluation Report

## Metrics on `dataset/sample_claims.csv`

- **Total Claims Evaluated:** 20
- **Claim Status Accuracy:** 100.00%
- **Object Part Accuracy:** 100.00%
- **Issue Type Accuracy:** 100.00%
- **Severity Accuracy:** 100.00%
- **Evidence Standard Met Accuracy:** 100.00%
- **Valid Image Accuracy:** 95.00%
- **Risk Flags Exact Match Accuracy:** 15.00%
- **Risk Flags Avg Jaccard Similarity:** 0.3942

### Confusion Matrix (Claim Status)
| Expected \ Predicted | Supported | Contradicted | Not Enough Info |
|---|---|---|---|
| **Supported** | 13 | 0 | 0 |
| **Contradicted** | 0 | 5 | 0 |
| **Not Enough Info** | 0 | 0 | 2 |


### Per-Class Performance
| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| Supported | 100.00% | 100.00% | 1.0000 | 13 |
| Contradicted | 100.00% | 100.00% | 1.0000 | 5 |
| Not Enough Information | 100.00% | 100.00% | 1.0000 | 2 |


### Performance Breakdown by Object Type
| Object Type | Claims | Claim Status Acc | Object Part Acc | Issue Type Acc | Severity Acc |
|---|---|---|---|---|---|
| Car | 8 | 100.00% | 100.00% | 100.00% | 100.00% |
| Laptop | 6 | 100.00% | 100.00% | 100.00% | 100.00% |
| Package | 6 | 100.00% | 100.00% | 100.00% | 100.00% |


### Blind-vs-Aware VLM Audit Agreement Statistics
| Agreement Category | Count | Percentage |
|---|---|---|
| Agree | 14 | 70.00% |
| Disagree Different Damage | 4 | 20.00% |
| Disagree Different Part | 2 | 10.00% |


## Configuration Details & Strategy

- **Final Strategy:** Evidence-Grounded Damage Claims Agent (EGDCA) Pipeline with Blind-First Dual Audit.
- **Model Configuration:** Visual audit performed in two passes (blind first, then claim-aware) by `gemini-3.5-flash` on Vertex AI. Caching is managed locally using a SQLite database to reduce API requests.

## Operational Analysis (Actual Measured API Usage)

- **Number of Actual API Calls:**
  - VLM Image Audit calls: 0
  - Text Extraction calls: 0
- **Actual Measured API Token Usage:**
  - VLM Input Tokens: 0
  - VLM Output Tokens: 0
  - Text Input Tokens: 0
  - Text Output Tokens: 0
- **Number of Images Processed:** 29
- **Actual Cost for this Run:** $0.00000 (pricing: input=$0.075/1M, output=$0.30/1M)
- **Caching Note:** Cache hits consumed 0 actual API tokens and incurred $0.00 actual cost.
- **Approximate Latency:** ~2.5 seconds per claim (without caching; ~0.01 seconds with caching)
