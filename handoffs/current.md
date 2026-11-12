# Current handoff

Implemented Part 4.1 in the selected project root. See README.md for commands and docs/design-pipeline.md for responsibilities/schema. The ZIP's prompts are preserved as reference material; the pasted request is saved under prompts/00-user-request.md. No later-part prompts were automatically executed.

Application: Vue dashboard, Lightweight Charts candles and volume, FastAPI HTTP and WebSocket routes, Yahoo subscription to AAPL/MSFT/BTC-USD, append-only receipts and immutable observations, exact-repeat handling, explicit revision projection, source-time candles and completion, and frozen receipt-order replay. Demo data is a separate dataset. Source age and upstream/backend status are independent.

Verification: 9 automated tests pass; frontend builds; actual Yahoo capture traced into SQLite and the browser; demo and real replay work; disconnect and backend recovery work; direct/proxied health verified; a real capture backup replayed identically after an offline restart. Evidence JSON and screenshots are in docs/. See docs/verification.md for observed counts, corrections, and remaining limitations. Local dependencies and recordings are ignored by Git.

Servers used for verification are stopped at handoff. Run `.\scripts\start.ps1` to launch the built app at http://127.0.0.1:8000, or add -Offline for disconnected startup. The selected computer uses the bundled Python path saved in .runtime/python-executable.txt; set MARKET_PYTHON if the runtime changes. No global Python installation was performed.

Remaining: manually exercise date-range entry in the browser; capture regular-hours equity volume when Yahoo supplies it; student code review and Canvas/presentation evidence. The user subsequently requested GitHub publication to https://github.com/baubs27/Assignment-4.git; source upload is authorized, with runtime dependencies and recordings excluded. No deployment or Canvas submission was performed. Further cumulative parts need their detailed requirements.
