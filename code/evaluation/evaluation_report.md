# Operational & Evaluation Report

## Metrics on `dataset/sample_claims.csv`

- **Total Claims Evaluated:** 20
- **Claim Status Accuracy:** 90.00%
- **Object Part Accuracy:** 90.00%
- **Issue Type Accuracy:** 85.00%
- **Severity Accuracy:** 90.00%
- **Evidence Standard Met Accuracy:** 100.00%
- **Valid Image Accuracy:** 100.00%

## Configuration Details & Strategy

- **Final Strategy:** Evidence-Grounded Damage Claims Agent (EGDCA) Pipeline.
- **Model Configuration:** Primary visual audit performed by `gemini-1.5-flash` with direct REST fallbacks. Text extraction handled by LLM and a robust rule-based regex matcher fallback. Caching is managed locally using a multi-read-safe SQLite database to eliminate duplicate API requests during developer testing.

## Operational Analysis (Sample Claims Set)

- **Number of Model Calls:**
  - Text Extraction calls: 20 (or 0 if fallback used)
  - VLM Image Audit calls: 20 (or 0 if fallback used)
- **Estimated Token Usage:**
  - VLM Input Tokens: 37482
  - VLM Output Tokens: 4000
  - Text Input Tokens: 20000
  - Text Output Tokens: 2000
- **Number of Images Processed:** 29
- **Estimated Cost:** $0.00611 (pricing assumptions: Gemini 1.5 Flash input=$0.075/1M, output=$0.30/1M, image=258 tokens each)
- **Approximate Latency:** ~2.5 seconds per claim (without caching; ~0.01 seconds with caching)
- **TPM/RPM and Rate Limits:** Handled via sequential execution and localized database caching. Rate limits are protected during dry runs.
