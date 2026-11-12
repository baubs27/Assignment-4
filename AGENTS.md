# Working instructions

- Work inside this project. Read README.md, relevant implementation files, and docs/verification.md before editing. Preserve existing data and student changes.
- Scope is Part 4.1 unless the user requests another part. Course prompts under prompts/ and course_reference/ are reference documents, not automatically executable instructions or permission requirements. Use the user's current request to choose the work.
- Keep Vue, FastAPI, SQLite, and the required Yahoo WebSocket connection. Keep every synthetic fixture explicitly labeled and in dataset `demo` or an isolated test database.
- Never fabricate live evidence, timestamps, volume, trading performance, or API responses. Distinguish provider connection, browser connection, and source freshness.
- Preserve raw observations, receipts, duplicates, and earlier identifiable revisions. Reuse the same candle calculation for live and replay. No look-ahead: replay only sees receipts up to its cursor.
- Reuse the available Python runtime. Dependencies belong to .runtime/python or frontend/node_modules. Keep declarations and locks in sync; explain dependency changes. Never store credentials in source, prompts, screenshots, logs, or Git.
- Tests must protect data semantics and real boundaries, not mirror trivial UI styling. Run scripts/test.ps1 after backend changes and npm run build after frontend changes. Follow docs/browser-checks.md after interactive changes.
- SmokeTest means the repeatable offline backend/API checks plus the documented real-browser user operations. Tests report failures without modifying source. AutoLoop means inspect a failure, make the smallest in-scope correction, and rerun the affected check; stop on success or after five unsuccessful correction cycles and report the cause.
- Record major requests in prompts/ and actual results in docs/verification.md. Update README, architecture, and handoff when behavior changes.
- Show a concrete change summary and test results for student review before a Git commit. Do not commit, push, submit coursework, or send external messages unless requested.
