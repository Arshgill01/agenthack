# Operational & Evaluation Report

## Metrics on `dataset/sample_claims.csv`

- **Total Claims Evaluated:** 20
- **Claim Status Accuracy:** 95.00%
- **Object Part Accuracy:** 100.00%
- **Issue Type Accuracy:** 90.00%
- **Severity Accuracy:** 90.00%
- **Evidence Standard Met Accuracy:** 100.00%
- **Valid Image Accuracy:** 100.00%
- **Risk Flags Exact Match Accuracy:** 50.00%
- **Risk Flags Avg Jaccard Similarity:** 0.6375

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
| Car | 8 | 87.50% | 100.00% | 75.00% | 75.00% |
| Laptop | 6 | 100.00% | 100.00% | 100.00% | 100.00% |
| Package | 6 | 100.00% | 100.00% | 100.00% | 100.00% |


### Blind-vs-Aware VLM Audit Agreement Statistics
| Agreement Category | Count | Percentage |
|---|---|---|
| Agree | 15 | 75.00% |
| Disagree Different Damage | 3 | 15.00% |
| Reconciled Resolved | 2 | 10.00% |


## Configuration Details & Strategy

- **Final Strategy:** Evidence-Grounded Damage Claims Agent (EGDCA) Pipeline with Blind-First Dual Audit.
- **Model Configuration:** Visual audit performed in two passes (blind first, then claim-aware) by `gemini-3.5-flash` on Vertex AI. Caching is managed locally using a SQLite database to reduce API requests.

## Operational Analysis (Actual Measured API Usage)

- **Number of Actual API Calls:**
  - VLM Image Audit calls: 42
  - Text Extraction calls: 9
- **Actual Measured API Token Usage:**
  - VLM Input Tokens: 142740
  - VLM Output Tokens: 12867
  - Text Input Tokens: 4551
  - Text Output Tokens: 319
- **Number of Images Processed:** 29
- **Actual Cost for this Run:** $0.01500 (pricing: input=$0.075/1M, output=$0.30/1M)
- **Caching Note:** Cache hits consumed 0 actual API tokens and incurred $0.00 actual cost.
- **Approximate Latency:** ~2.5 seconds per claim (without caching; ~0.01 seconds with caching)
