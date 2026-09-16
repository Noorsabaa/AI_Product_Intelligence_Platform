# AI Product Intelligence Platform History

## Starting Point

This project is a FastAPI and React dashboard that ingests app reviews, detects language, predicts sentiment, categorizes complaints, detects spikes, and displays results.

## Work Completed

1. Diagnosed the API startup problem: FastAPI and Uvicorn were installed in the project virtual environment, not the global Python installation.
2. Evaluated the original 910-review dataset. It had no manual ground truth, so only proxy quality checks were possible.
3. Lazy-loaded ML libraries and cached the sentiment and categorization models. API import time fell from roughly 89 seconds to about 2.25 seconds.
4. Added category quality controls: very short text is skipped and trusted categories require confidence of at least 0.7.
5. Evaluated the supplied 3,000-row labelled dataset. The ingestion layer correctly de-duplicated 163 duplicate keys, leaving 2,837 unique reviews.
6. Added multilingual sentiment support using XLM-R, with a local English RoBERTa fallback when the multilingual model is unavailable.
7. Added neutral sentiment calibration using star ratings as a low-confidence tie-breaker, especially for 3-star reviews.
8. Added fast keyword routing for billing, login, syncing, compatibility, notifications, crashes, and missing features. Ambiguous reviews still use embeddings.
9. Added dashboard pipeline status, current stage, and approximate progress display.
10. Fixed empty spike and recommendation files causing dashboard API errors.
11. Added `scripts\evaluate_model.py` for repeatable accuracy, coverage, precision, recall, and F1 evaluation.

## Evaluation Results

After the local fallback run on the labelled evaluation dataset:

- Sentiment coverage: 99.1%
- Sentiment accuracy: 80.0%
- Sentiment macro F1: 77.9%
- Trusted category coverage on complaint rows: 68.1%
- Trusted category accuracy: 94.5%
- Trusted category macro F1: 87.7%

Neutral sentiment F1 improved from 1.6% to 64.2% after calibration.

## Model Download Decision

The multilingual XLM-R model is approximately 1.11 GB. Its download stalled after a partial download, so the download was stopped and the stale lock was removed. The application currently uses the cached English RoBERTa fallback. Kaggle was considered for batch multilingual processing, but that would require exporting enriched predictions back into the local application.

## Current Usage

Start the API:

```powershell
.\venv\Scripts\python.exe -m uvicorn api.main:app
```

Start the frontend in another terminal:

```powershell
cd frontend
npm run dev
```

Run evaluation:

```powershell
.\venv\Scripts\python.exe scripts\evaluate_model.py --labels complaint_intelligence_test_3000_labeled.csv
```

The API health endpoint is available at `http://127.0.0.1:8000/health`.

## Remaining Gaps

- The multilingual model needs a successful download before it can run locally.
- Existing `scratch\test_*.py` files are scripts rather than proper pytest tests, and some call external Google Play services.
- The frontend bundle is larger than the recommended Vite warning threshold.
- Recommendations now run as the final pipeline stage, with a deterministic local fallback when Gemini is unavailable.
- Secondary categories and evidence review IDs were added after the original history was written.