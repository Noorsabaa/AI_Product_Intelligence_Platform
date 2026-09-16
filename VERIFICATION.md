# Verification · Feedback review v3

Verified locally on 13 September 2026, including the final username/password and separate report-history changes.

## Automated results

- **32 Python tests passed** (`.venv313/Scripts/python.exe -m pytest -q`). One upstream Starlette TestClient deprecation warning; no test failures.
- Frontend formatting, lint and production build passed. Chart code is loaded separately for Trends.
- Browser workflow passed in isolated Edge/Playwright with **zero JavaScript page errors**. Test data and accounts are separate from the app on port 8000.

The backend suite covers atomic CSV rejection, optional app/rating fields, distinct customer identities, missing sentiment, failure preserving published results, interrupted-run recovery, discovered categories from previously unseen vocabulary, duplicate-text abstention, small semantic corpora, normalized priority growth, chart/evidence totals, preserved names, immutable report evidence, escaping and safe CSV output.

Account tests cover salted password hashes, case-insensitive usernames, login failure, opaque session storage, HttpOnly cookies, expiry/logout, attempt limits, CSRF/origin rejection, separate feedback/workspaces, report-list isolation, foreign report IDs returning 404, and isolated exports. Background analysis is verified through each account's API context.

## Browser workflow

The final `qa/browser-results-v3.json` records successful checks for:

1. Username/password sign-up with optional sample feedback, sign-in and sign-out.
2. Separate Dashboard, Trends, Priorities, Generate report and Report history pages.
3. Chart-category filtering and share mode with consistent underlying totals.
4. Descending priority order, complete paginated evidence, negative/all-feedback tabs, text search and CSV download.
5. Report generation with a title, standalone HTML download, persistent archive and frozen evidence.
6. Invalid CSV errors without data replacement, followed by a real valid import without app names or ratings and a completed semantic analysis.
7. Historical reports/evidence remaining intact after active-data replacement.
8. A second account seeing an empty dashboard/archive and receiving 404 for the first account's report URL; signing back in restores the first account's history.
9. 390px layout without document overflow, mobile navigation and keyboard modal dismissal.

Screenshots in `qa/` show the sign-in screen, dashboard, trends, priorities, evidence, report generation and history. Browser tests create disposable users on port 8001; they do not create default credentials in the primary installation.

## Dataset and model observations

All **3,437 original raw review rows**, including every original column, were compared against `D:/AI_Product_Intelligence_Platform (2).zip` and are unchanged. SQLite integrity check returned `ok`. The original ZIP was not modified.

The semantic pipeline completed on the supplied sample: 34 discovered categories; 1,906 grouped records; 1,531 ungrouped; 2,289 English text sentiment results and 1,148 rating signals. A cached rerun took approximately 30 seconds on this machine. A separate cold one-review import exercised actual local model inference, followed by a cached account-workspace run.

These establish execution, coverage and consistency, not classification accuracy. There is no held-out, independently labeled company dataset. Current discovery is English-only, and sample data contains repeated/development-style feedback.

## Delivery boundaries

The running app on port 8000 uses local username/password accounts. There is no email collection or delivery. Users choose their own credentials; sample feedback is opt-in at sign-up. Each user's history and data are stored locally under `data/workspaces` and protected by authenticated API context.

The release includes source, built frontend, documentation and a consistent snapshot of the original sample database. Account databases, per-user workspaces, credentials, virtual environments, model downloads, node_modules and test databases are excluded. The ZIP is a distributable project, not a backup of any user's account.

This is not a production security certification or hosted-concurrency benchmark. Team roles, password recovery, SSO/MFA, production retention and deployment operations are not implemented.


## Import preprocessing update — September 13, 2026

- 64 backend tests passed, including 31 CSV normalization cases and an authenticated ambiguous-date retry regression. Invalid replacement imports preserve existing data.
- The supplied 180-row CSV with a `reviews` column and month/day dates parsed without edits; normalized range August 3 through September 13, 2026.
- Browser test on a disposable account verified the date-choice prompt, no writes before clarification, successful retry with the identical file, and no JavaScript errors.
- Frontend build, lint and formatting checks passed.


## GitHub source distribution

The GitHub branch contains the current source, tests, documentation and a synthetic 180-review CSV. Local accounts, report archives, SQLite databases, environment files, downloaded models, frontend build output and dependencies are excluded. Earlier 3,437-review results above describe local verification rather than data shipped in this checkout.

Current GitHub checkout validation: 64 backend tests passed. The frontend production build passed with Vite's native config loader (`node node_modules/vite/bin/vite.js build --configLoader native`), using the existing matching dependency installation. Frontend lint and formatting checks passed. `git diff --check` passed.
