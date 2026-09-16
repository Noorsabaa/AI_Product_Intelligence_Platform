# Feedback review · v3

A local workspace for a support manager to understand customer feedback, investigate recurring complaints, and keep a reliable reporting history.

## Start

Clone this repository and install Python **3.13** plus Node.js **22.12+ or 24+**. The Git checkout contains frontend source; the launcher installs and builds it on first start. Create an account with a username and password (at least 12 characters). No email service is used. One process serves the API and built frontend at **http://127.0.0.1:8000**.

From the project folder on Windows, run:

```powershell
.\start.ps1 -Setup
```

Setup installs the ML dependencies and explicitly downloads the embedding and English sentiment models. Model weights total roughly 600 MB; Python dependencies need additional space and bandwidth. Normal analysis uses local caches and does not upload feedback to an LLM provider. Environments, model weights, account databases and user workspaces are not committed. After setup, use `start.cmd` or `./start.ps1` for subsequent starts.

For a smaller installation without neural-model downloads:

```powershell
.\start.ps1 -Setup -LexicalOnly
```

Then select **Data → Analysis method and limitations → Lexical discovery**. Lexical mode needs ratings for sentiment. Import & analyze attempts the default semantic method; if those models are absent, the import is retained and Data shows the failure so you can run lexical analysis. It never silently substitutes rating sentiment for an expected English text-model run.

Use `-Port 8002` if needed. Stop with Ctrl+C. **Run one server/worker per database.** SQLite startup recovers interrupted jobs; multiple workers require a separate job service and are not supported by this local edition. The launcher reuses `.venv313` if present; fresh installations create `.venv`.

## Accounts and private workspaces

Each username has its own feedback database, model cache, dashboard, exports and report archive. Usernames are case-insensitive and use 3–40 letters/numbers/dots/underscores/hyphens. Passwords use salted scrypt hashes. Login uses an opaque, expiring HttpOnly session cookie; mutations require a session CSRF token. Signing out invalidates the session. There are no default credentials.

New accounts start empty. Import `examples/customer_feedback_demo.csv` from the dashboard to explore 180 synthetic SaaS reviews. These are fictional examples, not a model accuracy benchmark. The optional sample checkbox at registration copies the server's existing sample database if it has been populated; a fresh Git checkout has no sample database. Sign out from the sidebar to switch accounts.

To populate that shared sample source explicitly after setup, run `.\.venv\Scripts\python.exe -m scripts.manage import examples/customer_feedback_demo.csv`. This affects the CLI sample database, not existing account workspaces.

The report archive is scoped on the server to the signed-in user, including direct report URLs and evidence exports. Reports belonging to another account return 404. Account credentials live in `data/accounts.db`; each user's data lives under `data/workspaces/<generated-id>/reviews.db`. These databases are excluded from release packaging. Back up the entire data directory to preserve local accounts and histories; a portable release is not a backup of user accounts.

This is a local account implementation, not SSO or an audited hosted identity service. There is no email or password-recovery flow. Keep your password safe. For HTTPS hosting, set `COOKIE_SECURE=1`; the default HTTP cookie setting is for the localhost launcher. Rate limits protect signup/login, but shared-host concurrency, team roles, MFA and production operations are outside this version.

## Manager workflow

1. **Import company feedback.** Upload a CSV containing feedback text and dates. Common column names such as `Reviews`, `Feedback`, `Date` and `Created At` are recognized automatically. Optional columns: `score`, `service`, `segment`, `customer_id`, `source`. There is no app picker or fixed list of companies.
2. **Read the four KPIs.** Analyzed reviews, positive, negative and neutral. Missing sentiment is disclosed in About these results and is never counted as neutral.
3. **Open Trends to follow a category.** The line-chart selector comes from discovered categories. It changes only the chart; KPIs and priorities remain scoped to the reporting period. Switch between counts and share of all analyzed feedback.
4. **Open Priorities to inspect complaints.** The leading eight complaint categories appear first; expand the list for every category. Open a row to see score components, every contributing review, search, pagination and CSV export. Names can be edited without changing membership.
5. **Open Generate report.** Choose the reporting period and optionally enter a report title. The report summarizes sentiment, complaint concentrations, changes, and actual supplied service/segment metadata. It gives observations rather than engineering recommendations.
6. **Open Report history.** Only reports generated by the signed-in account appear. Reports persist in SQLite with the exact figures, labels and complete review evidence from generation time. Later reanalysis, renames and dataset replacements do not change them. Download standalone HTML, evidence CSV, or use Print / Save PDF.

Each sidebar item opens a separate page: Dashboard, Trends, Priorities, Generate report, Report history and Data. Dashboard contains only the four KPIs and a concise period summary. Report generation and the historical log are separate pages. The reporting-period selection carries across these pages.

The reporting window ends at the latest valid date in your dataset, visibly shown beside the filter. It is not represented as live telemetry. Weekly charts include empty weeks; first/last buckets can be partial. Neutral feedback is not a complaint.

## CSV behavior

The importer normalizes column names (including casing and spaces), comma/semicolon/tab/pipe separators, UTF-8, Windows-1252 and BOM-marked UTF-16 exports. Empty rows are ignored. Dates may use ISO timestamps, year-first dates, month/day/year, day/month/year, English month names, modern five-digit Excel serials, or Unix seconds/milliseconds. Numeric calendar dates require a four-digit year. Month/day order is inferred from unambiguous dates across the file. When it cannot be inferred safely, choose the interpretation in the import dialog; no file editing is needed. Unambiguous dates retain their meaning even in mixed-locale files. Dates normalize to ISO internally, timezone-bearing timestamps normalize to UTC dates, and future dates remain invalid. Ratings accept whole numbers 1–5, decimal equivalents such as `5.0`, `5/5` and `5 stars`; missing ratings remain unavailable. Conflicting columns and truly invalid values are reported rather than silently discarded. The template is optional. The whole file is validated before a write transaction: an invalid row means nothing is imported. Limits: 10 MB and 50,000 rows per import.

Append is the default. Duplicate identity uses source metadata, customer ID when supplied, normalized date, content and rating. Identical wording from different supplied customer IDs is retained. Without identifiers, truly distinct identical same-day records cannot always be distinguished. Changing contextual metadata on an already imported duplicate is not an update operation.

Replacement requires an explicit checkbox and replaces current feedback/categories; saved reports remain. Imports and analysis runs cannot overlap. Raw text/ratings/dates are kept separately from model output. For legacy schema compatibility, a missing raw rating has an internal placeholder plus an explicit missing flag; APIs, exports and sentiment analysis correctly treat it as missing.

## Pipeline

`CSV format normalization → validation → language identification → sentiment → cached embeddings → UMAP → HDBSCAN → extracted category names → aggregate trends/priority → immutable report`

Default models: `sentence-transformers/all-MiniLM-L6-v2` for semantic grouping and `cardiffnlp/twitter-roberta-base-sentiment-latest` for English text sentiment. HDBSCAN decides how many dense groups exist. Outliers are not reassigned. Class-based TF-IDF names groups from their actual phrases; there is no issue-category dictionary.

Discovery uses distinct normalized English texts with at least four words, preventing repeated templates from manufacturing cluster density. Review counts still include retained records; distinct-text counts are shown beside priorities. Embeddings and sentiment are cached in SQLite. New coherent groups can emerge on the next analysis run; isolated novel comments remain visible as ungrouped evidence.

The lighter alternative uses TF-IDF → truncated SVD → HDBSCAN. It discovers categories from repeated vocabulary but handles paraphrases less well. Its sentiment uses ratings: 1–2 negative, 3 neutral, 4–5 positive.

See **[DESIGN.md](DESIGN.md)** for the rationale, scoring formula, modeling limits and production roadmap.

## Included sample and current limits

The original local development corpus of 3,437 reviews is preserved on the development machine and in the separately packaged release; it is not committed to Git. Source brands are legacy import metadata, not the product's organizing structure. This repository includes a smaller synthetic CSV for demonstration and original fixtures under `examples/`.

During prior local verification, English semantic discovery was run on the 3,437-record development corpus: **34 categories, 1,906 grouped records, 1,531 ungrouped**. English text sentiment covered 2,289 records; 1,148 used supplied ratings. A rerun with cached embeddings and sentiment took about **30 seconds** on the development machine. These are coverage/runtime observations, not accuracy claims.

English-only topic discovery is an explicit current limitation. Other languages remain ungrouped and use ratings when present; without ratings their sentiment remains unavailable. Short/ambiguous language detection can also abstain. Long text sentiment is truncated to 512 model tokens; document segmentation and multi-issue assignment are future work.

This is a **local application with separate user accounts**, not a production multi-tenant SaaS service. Basic per-user authentication and workspace isolation are implemented. Team roles, production identity/security review, retention controls, connectors, multilingual validation, account impact weighting and scheduled ingestion remain further work. Do not equate feedback volume with unique affected customers, outages, root causes or lost revenue.

## Development and verification

The backend is FastAPI + SQLite; the frontend is React + Recharts + Vite. Node is only necessary when editing the frontend. Use Node 22.12+ or 24+:

```powershell
cd frontend
npm ci
npm run lint
npm run format:check
npm run build
cd ..
```

With the ML/dev dependencies installed in your selected Python environment:

```powershell
python -m pytest -q
python -m scripts.manage init
python -m scripts.manage analyze --engine semantic
python -m scripts.manage import feedback.csv
```

On Windows, replace `python` with `.\.venv\Scripts\python.exe` (or the existing `.venv313` environment). Set the shell environment variable `INTELLIGENCE_DB` to use an isolated database. `.env.example` documents environment overrides; `.env` files are not loaded by the active application.

`qa/browser-smoke.cjs` exercises real browser workflows against a **disposable database on port 8001**, including replacement. Never point that mutating script at your primary workspace. Set `PLAYWRIGHT_MODULE` to your installed Playwright module and optionally `BROWSER_CHANNEL` (default `msedge`). See **[VERIFICATION.md](VERIFICATION.md)** for results.

`api/` holds routes; `services/` holds shared import, analysis, discovery, intelligence and report code; `frontend/src/` holds the interface. `legacy/` preserves retired experiments and v2 UI code and is not part of the active pipeline. `examples/` preserves original fixtures. The original ZIP is unchanged. `python -m scripts.package_release` makes a portable release excluding secrets, accounts, user workspaces, environments, dependencies and test databases. The default CLI database is the server sample source; set `INTELLIGENCE_DB` explicitly to operate on a specific user workspace.
