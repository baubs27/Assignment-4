# Current handoff

## Part 4.2 continuation

The latest user request expands scope to cumulative Part 4.2. Implemented two configurable SMA overlays/crossover markers, provisional-candle labeling, a strategy lab, saved receipt-causal and historical-daily backtests, Decimal cash/position/basis/P&L accounting, persisted orders/fills/equity/decisions, and live paper-account start/pause/resume. Active paper accounts pause automatically after server restart; resume skips downtime decisions. See docs/part4-2.md for complete rules, schema, limitations, and the actual 250-bar AAPL experiment.

Added backend/indicators.py, simulation.py, research.py, research_api.py, frontend StrategyLab/ResearchChart/research.css, Python reference/accounting/API tests, Playwright e2e checks, and .github/workflows/checks.yml. The current working branch is codex/part-4-2-strategy. Existing submitted Part 4.1 artifacts remain pinned historical evidence. Current verification is appended to docs/verification.md; GitHub Actions is checked after the branch push. No Canvas upload, real order, or Part 4.3 model integration is authorized by this continuation.

The notes below retain the original Part 4.1 handoff history.

## Part 4.1 history

Implemented Part 4.1 in the selected project root. See README.md for commands and docs/design-pipeline.md for responsibilities/schema. The ZIP's prompts are preserved as reference material; the pasted request is saved under prompts/00-user-request.md. No later-part prompts were automatically executed.

Application: Vue dashboard, Lightweight Charts candles and volume, FastAPI HTTP and WebSocket routes, Yahoo subscription to AAPL/MSFT/BTC-USD, append-only receipts and immutable observations, exact-repeat handling, explicit revision projection, source-time candles and completion, and frozen receipt-order replay. Demo data is a separate dataset. Source age and upstream/backend status are independent.

Verification: 9 automated tests pass; frontend builds; actual Yahoo capture traced into SQLite and the browser; demo and real replay work; disconnect and backend recovery work; direct/proxied health verified; a real capture backup replayed identically after an offline restart. Evidence JSON and screenshots are in docs/. See docs/verification.md for observed counts, corrections, and remaining limitations. Local dependencies and recordings are ignored by Git.

Servers used for verification are stopped at handoff. Run `.\scripts\start.ps1` to launch the built app at http://127.0.0.1:8000, or add -Offline for disconnected startup. The selected computer uses the bundled Python path saved in .runtime/python-executable.txt; set MARKET_PYTHON if the runtime changes. No global Python installation was performed.

Remaining: manually exercise date-range entry in the browser; capture regular-hours equity volume when Yahoo supplies it; student code review and Canvas/presentation evidence. The user subsequently requested GitHub publication to https://github.com/baubs27/Assignment-4.git; source upload is authorized, with runtime dependencies and recordings excluded. No deployment or Canvas submission was performed. Further cumulative parts need their detailed requirements.

Submission follow-up: the user asked for report.md and explicitly approved publishing the attached recording and supporting report documents to public GitHub. Added AI-USE.md, docs/evidence-log.md, docs/clean-checkout-verification.md, and a captioned 56-second docs/part4-1-demo.mp4. A fresh GitHub clone independently installed locked dependencies, passed 9 tests, built the frontend, and passed offline dashboard/health/database checks. The report pins the submitted evidence revision, source baseline, and video. Original recording remains outside the repository. The main app was later started for user testing; do not stop that app as part of document work. The isolated clean-checkout server on port 8002 has been stopped. Canvas upload remains the student's action.
