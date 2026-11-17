# Verification record - November 11, 2026 (America/New_York)

The UTC clock crossed into November 12 during this evening session. Times shown by the application and evidence JSON are UTC. This record distinguishes constructed tests, real provider observations, and checks that remain manual.

## Environment and dependency checks

- Initial workspace: empty Git repository, no application files or existing local AGENTS.md. The ZIP contained teaching prompts and a tiny sample CSV, not source code. Extracted reference copies are retained, and the user's pasted request is saved under prompts/00-user-request.md.
- Node 24.20.0 / npm 11.19.0 were available. The Windows Python alias did not execute; py reported no installed Python. Reused the Codex bundled Python 3.12 with a project-local package target.
- Initial package downloads failed under restricted DNS. The approved network-enabled installation succeeded. Project-local manifests and locks were created; no global Python packages or virtual environment were changed.
- Installed/tested: FastAPI 0.162.5, uvicorn 0.54.0, yfinance 1.8.0, pytest 9.2.0, httpx 0.28.1, Vite 7.3.8, Lightweight Charts 5.3.0, and Vue 3.5.x. Exact versions are in the lockfiles.
- Frontend dependency audit during installation reported zero vulnerabilities. This is the install-time result, not a continuing security guarantee.

## Automated checks

Command: `.\scripts\test.ps1`.

Final observed result: **9 passed in 3.05 seconds**, with one third-party Starlette deprecation warning about its httpx TestClient adapter. The tests still execute successfully. No model, provider login, or network service is used by this suite.

| Check | Expected and observed result |
| --- | --- |
| Course one-minute candle | O100 H103 L100 C101 V11, forming before 15:01 and complete at 15:01; same when the middle tick arrives last |
| Exact duplicates | Two equal deliveries share an observation ID; separate receipt IDs remain; no double contribution |
| Ambiguous same-time change | Changed price is a distinct observation; retained after reopening the SQLite file |
| Explicit revisions | Revision 0 is visible before revision 1 arrives; revision 1 then takes effect; an old revision arriving again cannot undo it |
| Conflicting explicit revision | Same producer identity/revision with a conflicting payload raises an integrity error, preserving the accepted version |
| Volume uncertainty | Missing baseline, cumulative reset, absent total, and rolling crypto totals produce null volume |
| Higher timeframe | 5-minute aggregation returns expected O100 C103 V9; empty daily input returns an empty result |
| Deterministic fixture | 276 receipts, 275 observations, one exact repeat; final close 102.50; seeding twice and replaying twice do not alter session counts |
| HTTP/WebSocket integration | Health responds; real replay WebSocket supports step/seek/reset; empty selection returns zero; disconnected feed remains separate from browser connectivity |
| Yahoo lifecycle regression | A stub matching yfinance's swallowed cancellation cannot reconnect after stop; task and enable flag are cleared |

Initial pytest attempts failed because the sandbox prevented creation of temporary directories; no application assertion failed in those attempts. The test command now uses a unique directory inside .runtime. Network/socket-capable verification was run in the approved host context. Tests initially took 12.57 seconds; making fixture initialization atomic and closing SQLite connections explicitly reduced subsequent execution to about three seconds.

Frontend command: `cd frontend; npm run build`. Final observed result: Vite production build passed, 16 modules transformed. Built Vue and chart JavaScript is approximately 254.5 kB before gzip. The build is served successfully by FastAPI.

## Real Yahoo capture and provenance

The backend established a real `yfinance.AsyncWebSocket` subscription to AAPL, MSFT, and BTC-USD. All three produced source observations. No recorded or synthetic input was substituted into dataset `live`.

One traceable AAPL example:

- SQLite observation **278**, receipt **279**.
- Yahoo raw payload `id=AAPL`, `price=355.55`, `time="1794450443000"`.
- Stored source time **2026-11-12 02:27:23 UTC**, backend receipt **02:27:22.778659 UTC**. The source was about 0.22 seconds ahead of the local clock; original times were preserved. Display age is clamped to zero if clocks slightly disagree.
- A later AAPL observation in the same minute had price **355.52** and source **02:27:34 UTC**.
- Browser showed 02:27 candle **O355.55 H355.55 L355.52 C355.52**, with both ledger rows and unknown volume. Independent SQLite OHLC calculation and replay agreed.
- These overnight equity messages omitted `day_volume`. That absence is preserved as null, not zero. BTC messages included a rolling 24-hour total; that total was retained in the source ledger but excluded from candle-volume calculations.

At the first frozen offline check, actual captures contained AAPL 26 receipts/24 observations, MSFT 37/33, and BTC-USD 73/73. See [live-capture-evidence.json](live-capture-evidence.json). Further use of the live workstation added records afterward; the evidence file intentionally describes its own frozen check time.

Command (with Yahoo disconnected):

```powershell
. .\scripts\common.ps1
& $ProjectPython scripts/verify_recording.py docs/live-capture-evidence.json
```

For each symbol, the script constructs OHLC independently from SQLite observations, compares it to FastAPI's replay WebSocket, resets/replays again, and confirms that all stored session counts are unchanged. All comparisons passed. It deliberately refuses to assert stable global counts while Yahoo is actively recording.

## Browser observations

Real Vue UI and FastAPI routes were exercised using the browser tools.

- Yahoo live: actual AAPL prices, source age, source/receipt times, stored observation IDs, forming/completed candles, and backend connection were visible.
- Demo replay: clearly labeled constructed data; playback ended at **276 / 276**, **275 unique**, **one exact repeat**, **92 one-minute bars**, price **102.50**, last-bar volume **100**. Both correction versions were visible in the ledger.
- 5-minute demo replay: **19 bars**, final price **102.50**, same receipt/observation counts. Daily view and Step: one receipt produced one forming UTC-day candle, with unknown first-bar volume.
- Actual saved Yahoo playback: finished at **32 / 32** selected receipts, **30 unique**, **two repeats**, **nine one-minute bars**, last price **355.18**. New arrivals did not extend this frozen replay selection.
- Narrow layout at 390 x 844: page scroll width 375 px with a 390 px viewport; no document-wide horizontal overflow. Instrument selector was visible. A 1280 x 900 desktop layout was also inspected. Temporary viewport overrides were reset afterward.
- Explicit Yahoo Disconnect: browser showed **Feed disconnected**, upstream **disconnected**, and **Backend WebSocket connected** simultaneously. Saved candles stayed visible. It remained off beyond the reconnect interval until explicitly connected again.
- Backend stop: visible **Backend offline** and **Backend connection lost. Reconnecting…**. Backend restart: browser recovered automatically.
- After the corrected frontend reload, console logs contained **no new errors** during replay. Earlier chart errors remain in the browser's historical log, identified by their old asset URL and pre-fix timestamps.

Screenshots: [demo chart](dashboard-demo.png), [disconnected source with backend available](feed-disconnected.png). Screenshots represent the stated point in time; they are not evidence of ongoing source freshness.

## Failures found and corrected

1. Appending a new chart point with Lightweight Charts' historicalUpdate=true caused `Cannot update non-existing data point`. Fixed latest/new points to use normal update and rebuilt series for actual historical changes. Reran demo and actual replay; no new console errors.
2. yfinance catches cancellation inside its listener. A stop could therefore continue into the retry loop. Added an explicit enable flag checked after listening and in the loop condition. Retested with the real Yahoo disconnect button and an automated cancellation regression.
3. Narrow grid children initially allowed the ledger's intrinsic width to expand the page. Added minimum-width rules and responsive instrument/card layouts. Verified actual page width at the narrow breakpoint.
4. Browser-tool full-page screenshot capture was unavailable; the supported viewport screenshot method produced the saved evidence instead. Native datetime-local filling through the browser tool timed out; the empty time-range **UI entry operation is not claimed as verified**. Backend empty selection and bounded receipt filtering passed automated tests; manually exercise date entry before submission.

## Vue/FastAPI proxy

Started `npm run dev` on 127.0.0.1:5173. GET /api/health at both :8000 and :5173 returned status 200 and the same body:

```json
{"status":"ok","service":"market-workstation","storage":"SQLite"}
```

Stopped FastAPI while Vite remained running: proxied health failed with HTTP 500 / ECONNREFUSED as expected. Restarted FastAPI: the proxy returned the original JSON again. This establishes that Vite depended on the backend. The temporary Vite server was stopped after verification.

## Offline restart and persistence

A consistent SQLite backup of the actual capture was made at `data/persistence-check.sqlite3`, then served on an isolated 127.0.0.1:8001 with `MARKET_LIVE=0`. This kept the restart experiment independent of continued use of the primary workstation.

Before restart: AAPL 29 receipts/27 observations, MSFT 38/34, BTC-USD 100/100. The script verified independent OHLC equality and repeated replay equality with Yahoo disconnected. The server was stopped and restarted offline with the same database. All session counts, candles, completion states at the replay cursor, and repeated replay outcomes were exactly equal.

Machine-readable records: [before restart](offline-copy-evidence.json), [after restart](restart-evidence.json). Comparison assertion passed. Both experiments used real saved Yahoo input. The isolated verification server was stopped afterward.

## Remaining evidence and submission actions

- Capture a regular-hours equity session with usable cumulative volume. Live overnight quotes and demo volume are verified separately; live equity volume was absent, so that part of provider evidence remains open.
- Manually enter a time range in the native date/time controls and confirm the empty-range UI. The tool limitation above did not establish that user operation.
- Student review, Git commit/GitHub publication, Canvas submission, and the in-class presentation remain student actions. No account or external submission action occurred.
- This is Part 4.1. SMA strategy, simulated trading, AI decisions, backtesting, image interpretation, and audio have not been implemented or verified.

## Subsequent GitHub upload request

The user authorized uploading the project to https://github.com/baubs27/Assignment-4.git. Destination inspection found an empty public repository with write access and default branch main. The initial source commit includes code, locks, tests, documentation, screenshots, and reference prompts. .gitignore excludes .runtime, node_modules, frontend/dist, SQLite recordings, caches, logs, and .env. The application has not changed since the recorded tests and build above; this follow-up updates publication documentation and Git state.

## Submission preparation follow-up

The student requested report.md, supplied a screen recording, confirmed Codex was the only coding agent/editor/AI tool used, and authorized public GitHub publication of the video and supporting documents. A fresh clone of source commit 6c00865 installed its own locked dependencies, passed 9 tests in 3.36 seconds, built the frontend, and served the dashboard/health with HTTP 200 on isolated localhost:8002. A fresh offline database initialized to 276 demo receipts and 275 observations. The isolated server was stopped; the student's main test app was not stopped for this work. Details: [clean-checkout verification](clean-checkout-verification.md).

The original 65.1333-second recording exceeded the one-minute limit. A 56-second derivative combines 44 seconds of its live-workstation footage with two explicitly labeled six-second verification screenshots. Captions identify the separation of browser connectivity from source freshness/status. Output frames and full decode were checked; the original was preserved. See [video](part4-1-demo.mp4), [curated evidence](evidence-log.md), and [AI disclosure](../AI-USE.md). No model-generated video or fabricated live footage was used. Existing provider-volume and date-range UI limitations remain disclosed in report.md.

## Part 4.2 - November 16, 2026 (America/New_York)

User requested cumulative SMA/crossover indicators, simulated trading/accounting, causal backtesting, trusted-reference checks, unfinished-candle handling, known accounting examples, browser tests, and GitHub Actions on pushes. Full implementation and assumptions: [part4-2.md](part4-2.md). The Part 4.1 evidence above describes its original version and is not relabeled as Part 4.2 evidence.

Implemented two configurable price-chart SMA lines/crossovers and provisional previews; a shared completed-candle strategy; Decimal cash/basis/position/realized/unrealized accounting; separate orders/fills with costs and next-price eligibility; frozen daily-history and recorded-receipt backtests; persisted paper accounts with pause/resume and restart safety; saved account/decision/trade/equity views; validated APIs; and an offline push/PR workflow. Schema additions preserve the original market tables.

### Local automated verification

- `.\scripts\test.ps1`: **27 passed in 3.71 seconds**, with the existing third-party Starlette/httpx deprecation warning.
- `cd frontend; npm run build`: passed, **19 modules**, 288.26 kB JavaScript before gzip, approximately **724 ms** in the final build.
- `E2E_BROWSER_CHANNEL=chrome; npm run test:e2e`: **4 passed in 5.6 seconds** with browser requests to external websites blocked. Uses the actual built Vue app, FastAPI HTTP/WebSocket and an isolated fresh SQLite database, with Yahoo off. The runner stops its server after the suite; source files are not rewritten by tests.
- Browser coverage: seek a replay and edit windows without losing its cursor; expected provisional SMA 2/3 values **101.8600 / 101.5433**; saved backtest account/fills/indicator decisions agree with the persisted API result and survive reload; paper start/pause and readable empty-source errors; narrow viewport without document overflow. Browser page exceptions fail the calculation/result tests.
- Trusted references: TradingView's published SMA3 example returns **6,7,8** for closes 5,6,7,8,9; batch and incremental SMA agree with pandas rolling mean for **1,200** deterministic closes and windows **1,2,5,20,200**, absolute tolerance **1e-11**. Crossovers agree with independently shifted pandas means, including equality and first-warm-up behavior.
- Accounting: $1,000 -> buy 4 at $100 -> sell 1 at $110 -> sell 3 at $105 gives **$1,025 cash, 0 position, $25 realized, $0 unrealized** at zero costs. Fee-inclusive basis, adverse slippage, rejected orders, duplicate-fill prevention, partial allocation and sampled drawdown are also checked.
- Causality: future close changes do not alter earlier decisions/fills; an unfinished candle cannot generate a strategy decision; a new order cannot use its own decision receipt; prior decisions survive later source corrections; end-of-sample orders are cancelled without a fabricated fill. Paper warm-up places no retrospective order, and restart pauses/resume skips downtime.
- API boundaries: invalid windows/ranges rejected, empty source understandable, history import uses unadjusted completed daily data, a stubbed provider failure returns 502 without fixture substitution, saved run results persist, and SMA-window WebSocket commands preserve the replay cursor.

The initial browser run was **3 passed / 1 failed**: the test expected the latest provisional SMA but read a historical candle selected by the chart crosshair after scrolling. The displayed numbers corresponded to that hovered candle. The browser check was corrected to move the pointer outside the chart before asserting the latest value; no calculation was changed to fit the test. All four checks then passed, including the offline-network run. A lockfile/manifest mismatch on the initial browser-package install was corrected by explicitly updating the lockfile before the clean install. A Windows asyncio ConnectionResetError can be logged when a browser page closes/reloads its socket; no route result or browser assertion failed as a result. This is distinct from a strategy/accounting failure.

### Actual historical-data verification

Yahoo AAPL / 1y download produced **250 completed daily bars** spanning **2025-11-17 through 2026-11-13**, excluding the current day's bar. Run used **SMA 5/20**, **$10,000 cash**, **10-unit buys**, **$1 per fill**, and **5 bps adverse slippage**. Observed **13 fills**, **$10,455.79 equity**, **$6,893.09 cash**, **10 units**, **4.5579% return**, **3.5434% sampled drawdown**, and **$13 fees**. These values describe this sample/model only.

Every historical SMA/crossover was compared with pandas: **250 bars**, **all crossovers equal**, **maximum observed SMA error 0.0**. A second run against the same frozen historical dataset/configuration produced an identical result. [Machine-readable history/config/result/reference evidence](part4-2-history-evidence.json). The result's decision-time prices and source fingerprint remain inspectable. [Actual UI screenshot of a separately labeled constructed-data account](part4-2-demo-backtest.png).

### Push checks and limits

`.github/workflows/checks.yml` runs on push, pull_request, and manual dispatch. It installs the Python and frontend locks, runs offline Python tests, builds Vue, installs Chromium, and executes the real-browser suite. It needs no provider credentials and uploads browser traces/screenshots on failure. Hosted run status is checked separately after pushing the Part 4.2 branch; the GitHub Actions run is the authoritative hosted result, rather than this local check log.

The experiment is not a profitability guarantee. Survivorship bias, sample overfitting, later vendor revisions, unadjusted corporate-action effects, absent dividends, assumed liquidity and estimated costs remain limitations. Recorded-prefix reconstruction is bounded to 5,000 receipts per experiment. Paper-account restart is a deliberate pause, not continuous exchange execution. The existing native date-range and overnight live-volume limitations are not falsely claimed as resolved by the new offline suite. No Part 4.2 submission video or Canvas upload was performed by this implementation task.
