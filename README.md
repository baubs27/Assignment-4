# Market Desk - Live Market Workstation

A local IST 402 Part 4.1 application for observing Yahoo Finance prices, inspecting candlesticks and volume, preserving observations in SQLite, and replaying a recording. Built with Vue 3, FastAPI, and TradingView Lightweight Charts 5.3. The frontend includes an observation ledger, source and receipt timestamps, source age, separate upstream/backend status, a candle inspector, and receipt-order replay.

This implements the Part 4.1 requirements in the pasted request. SMA strategies, model decisions, paper trading, backtesting, chart-image analysis, and voice belong to later cumulative parts and are not implemented. CSV loading is ungraded practice and is not used as evidence of streaming.

## Start on this computer

Dependencies are already installed under `.runtime/python` and `frontend/node_modules`, and the frontend is built. In PowerShell from this folder:

```powershell
.\scripts\start.ps1
```

Open **http://127.0.0.1:8000**. Use Ctrl+C in that terminal to stop. FastAPI serves the built Vue frontend, API, and WebSocket from one local origin. No credentials or Yahoo account are required.

To start with Yahoo disconnected:

```powershell
.\scripts\start.ps1 -Offline
```

The Connect Yahoo button explicitly enables the shared upstream subscription. Disconnect Yahoo leaves the backend WebSocket and saved data available. Select **Demo replay** to exercise the chart offline. Demo prices are constructed teaching data, clearly separated from Yahoo observations by dataset.

## Install or restore

Prerequisites: Python 3.12+, Node.js 20.19+ or 22.12+ (tested Node 24.20.0), and npm. This computer has Node/npm and the Codex bundled Python 3.12; the Windows `python` alias is not a usable interpreter. The scripts reuse the bundled interpreter, recorded locally in ignored `.runtime/python-executable.txt`. On another computer, set `MARKET_PYTHON` to your Python executable:

```powershell
$env:MARKET_PYTHON = 'C:\path\to\python.exe'
.\scripts\install.ps1
.\scripts\start.ps1
```

The installer uses `pip install --target .runtime/python -r backend/requirements-lock.txt`, `npm ci`, and `npm run build`. Packages stay inside the project; no virtual environment or global package installation is required. `backend/requirements.txt` declares compatible ranges; `requirements-lock.txt` captures the versions actually tested on Windows/Python 3.12. `frontend/package-lock.json` locks frontend dependencies. Network access is needed for installation and Yahoo streaming. Optional web fonts fall back to system fonts offline.

## Database initialization

SQLite initializes automatically at startup at **data/market.sqlite3** with foreign keys and WAL enabled. An atomic, idempotent teaching fixture is loaded into dataset `demo`; Yahoo messages use dataset `live`. No demo observations enter the live dataset. To select a different database before starting:

```powershell
$env:MARKET_DB = "$PWD\data\another-session.sqlite3"
.\scripts\start.ps1 -Offline
```

Recorded sessions survive server restarts. Database and runtime files are ignored by Git. To inspect the schema or raw messages, use SQLite or Python's sqlite3; an example is in [docs/design-pipeline.md](docs/design-pipeline.md). Never delete a database to reset replay: replay is read-only.

## Using the workstation

1. Select AAPL, MSFT, or BTC-USD. Choose 1m, 5m, 15m, 1h, or 1d. The small-screen instrument selector provides the same choices as the desktop sidebar.
2. In **Yahoo live**, the backend records all three subscribed symbols, even when a different chart is selected. Read source age and upstream status before interpreting a price. More than 60 seconds is marked stale, regardless of the browser connection.
3. Hover over a candle to inspect OHLC, source-derived volume, and whether its interval has ended. All chart buckets are aligned to UTC, including daily bars. A completed interval can still receive a late observation or identifiable correction.
4. Choose **Saved Yahoo** for actual captured observations or **Demo replay** for deterministic teaching data. Set an optional receipt-time range in UTC and click Load range. Play, pause, step, reset, seek, or change receipts per playback tick. A new replay selection starts at receipt zero; switching interval reloads that selection.
5. Replay freezes the selected receipt list at connection time. Source times determine prices within a candle; receipt order determines when an observation becomes known. A paused replay does not advance historical time. At the end, the last bar may still be forming at the last recorded receipt time. No synthetic closing tick is added.

## Data limits

Yahoo streaming quotes are sampled observations, not a complete exchange trade tape. Candles summarize captured ticks; missing intervals remain gaps. Values and delays depend on instrument and market hours. The application does not certify exchange-level real-time data, infer market-open status, or invent historical candles before recording began.

For equities, `day_volume`, when present, is treated as a cumulative session total. Candle volume sums differences in source-time order across adjacent usable totals on the same New York calendar date. An unknown baseline, missing total, decrease/reset, or date boundary makes the affected candle's volume unknown. The first captured candle is usually unknown. Attribution of a cumulative change to the later tick's interval is an estimate when ticks span gaps. Extended-hours provider resets are handled as decreases, not guessed away. BTC's rolling 24-hour volume is retained in the ledger but never used as candle volume. The actual overnight AAPL/MSFT messages received during verification omitted `day_volume`; regular-hours live equity volume still needs a separate observation. Demo and deterministic tests verify the volume chart and calculations.

Yahoo has no reliable trade identity/revision number in this stream. Exact normalized payload repeats share one observation with multiple receipt records. Changed messages at the same timestamp are retained as distinct observations. Only a producer-supplied event identity plus revision can replace an older version in the effective candle view. Old versions remain stored. The demo exercises this explicit correction mechanism; it is not claimed as a Yahoo feature.

## Verification

```powershell
.\scripts\test.ps1
```

Runs isolated SQLite, aggregation, API/WebSocket, and feed lifecycle tests with the upstream off. It exits nonzero on failure and uses a fresh database directory per run. It does not edit source. For UI changes, also follow [docs/browser-checks.md](docs/browser-checks.md). Observed results and limitations are recorded in [docs/verification.md](docs/verification.md).

For frontend development, run the backend as above, then in a second PowerShell:

```powershell
cd frontend
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` and `/ws` to port 8000. Rebuild with `npm run build` before using the single-server start command to view frontend changes. Interactive API documentation: http://127.0.0.1:8000/docs.

## Files

```text
backend/          FastAPI, Yahoo adapter, SQLite store, candle formation, demo seed
frontend/         Vue dashboard, chart, styles, Vite configuration and lockfile
scripts/          Project-local install, start, and test commands
tests/            Deterministic data, transport, and feed lifecycle checks
docs/             Architecture, verification, browser checks, submission checklist
prompts/          Original request and supplied course prompts (reference material)
course_reference/ Unmodified extracted starter-package prompt copies
handoffs/         Session state and resume instructions
data/             Local SQLite recordings (ignored)
.runtime/         Local Python packages and test databases (ignored)
AGENTS.md         Standing instructions for future work
```

AI assisted implementation and debugging; the student should inspect the code and reproduce the checks before submission. Source repository: [baubs27/Assignment-4](https://github.com/baubs27/Assignment-4). Local recordings, installed dependencies, and build output are excluded from Git. Canvas submission and account actions remain student tasks.

References: [yfinance WebSocket documentation](https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html), [Lightweight Charts documentation](https://tradingview.github.io/lightweight-charts/docs), [TradingView](https://www.tradingview.com/). TradingView Lightweight Charts™ is used under its Apache 2.0 license; see frontend node_modules/lightweight-charts/LICENSE and NOTICE. yfinance is an independent tool, not an official Yahoo library.
