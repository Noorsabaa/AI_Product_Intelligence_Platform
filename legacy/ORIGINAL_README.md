# AI Product Intelligence Platform

## Project Overview

> **North Star:** Help Customer Success teams quickly understand what customers are complaining about, identify emerging problems, and know what action to take based on the evidence in customer feedback.

The AI Product Intelligence Platform is an AI-powered system designed to help B2B SaaS companies understand large amounts of customer feedback and complaints.

## Purpose

This portfolio project turns app reviews into product intelligence for Customer Success and Product teams. The local pipeline:

1. Ingests Google Play reviews or a CSV dataset.
2. Detects language and whether a review is analyzable.
3. Predicts sentiment.
4. Assigns complaint categories with confidence gating.
5. Detects calendar-based complaint spikes.
6. Generates evidence-backed recommendation briefs.
7. Displays results in a React dashboard with filters and source-review inspection.

This is a local demonstration project, not a multi-user production service. It uses SQLite, in-process background tasks, and locally cached machine-learning models.

## Requirements

- Windows PowerShell
- Python 3.11 or newer
- Node.js and npm
- Enough disk space for cached transformer and embedding models

Install the Python packages used by the project:

```powershell
python -m pip install -r requirements.txt
```

Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

## Configuration

Create a `.env` file in the repository root if Gemini recommendations are desired:

```text
GEMINI_API_KEY=your_key_here
```

Gemini is optional. Without it, the project uses deterministic local recommendation briefs.

The multilingual sentiment model is optional as well. If it is not cached locally, the project uses the English fallback and processes only English reviews.

## Initialize the Database

From the repository root:

```powershell
python scripts/init_db.py
```

Initialization is idempotent. It creates a fresh database and upgrades older local databases with the derived review columns and dashboard views without deleting existing reviews.

## Run the Application

Start the API in one PowerShell terminal:

```powershell
python -m uvicorn api.main:app --reload
```

Start the dashboard in another:

```powershell
cd frontend
npm run dev
```

The API is available at `http://127.0.0.1:8000`. The dashboard URL is printed by Vite, normally `http://localhost:5173`.

Useful endpoints:

- `GET /health`
- `GET /dashboard/summary`
- `GET /dashboard/categories`
- `GET /dashboard/spikes`
- `GET /dashboard/spike-reviews`
- `GET /dashboard/recommendations`
- `POST /ingest/csv`
- `POST /pipeline/run`
- `GET /pipeline/status`

## Run the Pipeline

The dashboard can upload a CSV and start analysis. The CSV must contain:

```text
app_name,content,review_date,score
```

Scores must be integers from 1 to 5. A valid upload replaces the active local dataset atomically; an invalid upload does not remove the existing dataset.

The pipeline stages are language detection, sentiment, categorization, spike detection, and recommendations. Monitor progress through `GET /pipeline/status` or the dashboard.

For a small portfolio dataset, the default conservative spike profile may
produce no spikes because it requires production-like complaint volume. To
demonstrate the complete workflow without editing code, use the explicitly
labelled demo profile when starting the API:

```powershell
$env:SPIKE_PROFILE = "demo"
python -m uvicorn api.main:app --reload
```

The default is `conservative`; use that profile for interpreting results. The
demo profile is only for showing the spike, evidence, and recommendation flow
on a small dataset.

To ingest the configured Google Play apps directly:

```powershell
python scripts/ingest_all_apps.py
```

This requires network access and depends on Google Play availability.

To analyze any public Google Play app, use its package ID from the Play Store URL:

```powershell
python -m scripts.ingest_app --name Trello --package com.trello
```

The command adds the app's reviews and runs the full analysis pipeline. Optional
arguments include `--days`, `--lang`, `--country`, and `--count`:

```powershell
python -m scripts.ingest_app --name Trello --package com.trello --days 90 --lang en --country us
```

The scraper supports Google Play apps only. The Play Store package ID must be
correct, and the request depends on Google Play availability.

## Evaluate the Models

Run evaluation against the supplied labelled fixture:

```powershell
python scripts/evaluate_model.py --labels complaint_intelligence_test_3000_labeled.csv
```

The report includes aggregate metrics and breakdowns by language, review length, app, and true category. Category metrics only include predictions meeting the trusted confidence threshold of `0.7`.

The supplied labelled dataset is a development fixture with repeated and synthetic-style examples. Its metrics should not be treated as production accuracy. A manually labelled holdout set from real customer feedback is needed for stronger claims.

## Tests

Run the isolated test suite:

```powershell
python -m pytest -q
```

The tests use temporary databases. The executable experiments in `scratch/` are intentionally excluded from pytest collection.

## Project Layout

```text
api/          FastAPI application and dashboard, ingestion, and pipeline routes
db/           SQLite connection and canonical schema
frontend/     React and Vite dashboard
ingestion/    Google Play scraping and app upsert logic
migrations/   Targeted view migrations for existing databases
scripts/      Pipeline stages, initialization, evaluation, and ingestion commands
tests/        Isolated automated tests
scratch/      Manual experiments and generated local pipeline outputs
```

## Important Limitations

- SQLite and in-process background tasks are suitable for this single-machine portfolio scope only.
- The English fallback must not be used to score non-English reviews; those rows remain pending until a multilingual model is available.
- Sentiment and category predictions are model outputs, not ground truth.
- Keyword confidence is a heuristic, and embedding similarity is not calibrated probability.
- Spike priority is a transparent heuristic using growth, volume, and average rating.
- Recommendations should be reviewed against the source reviews before being used for an operational decision.
The system will process customer feedback, identify sentiment, complaint categories, topics, and priority, and detect meaningful trends over time. It will then turn these findings into clear summaries and recommendations that help Customer Success teams understand what customers are struggling with and decide what needs attention.

The main goal is to move from simply collecting customer feedback to turning that feedback into actionable product intelligence.