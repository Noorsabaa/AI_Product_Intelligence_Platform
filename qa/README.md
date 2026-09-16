# Browser verification

`browser-smoke.cjs` tests navigation, actual chart rendering, shared filters, source evidence, saved actions, search, export, CSV validation, background analysis, mobile layout, dialog keyboard handling and network-error recovery.

Use a separate database: the test intentionally changes action statuses and runs analysis.

1. Install Playwright in your development environment, or set `PLAYWRIGHT_MODULE` to an existing installation.
2. Copy the workspace database using SQLite backup (not a live file copy) into `qa/browser.db`.
3. Set `INTELLIGENCE_DB=qa/browser.db` in the test-server terminal and run Uvicorn on port 8001, with a built frontend.
4. Run `node qa/browser-smoke.cjs` from the project root. Microsoft Edge is the default installed browser; `BROWSER_CHANNEL=chrome` selects Chrome. `SIGNAL_TEST_URL` overrides `http://127.0.0.1:8001`.

Results are written to `browser-results.json` and PNG screenshots in this directory. Test databases and exports are excluded from the portable package. Browser automation uses a temporary profile and does not access your personal browser session.
