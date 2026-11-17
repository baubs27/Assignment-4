# Market Desk - Live Market Workstation

A local IST 402 Parts 4.1-4.2 application for observing Yahoo Finance prices, inspecting candlesticks and volume, preserving/replaying observations, deriving SMA crossover signals, and measuring simulated account outcomes. Built with Vue 3, FastAPI, SQLite, and TradingView Lightweight Charts 5.3. Market provenance and receipt-order replay remain available alongside the strategy lab, saved backtests, and persistent paper accounts.

This implements the supplied Part 4.1 and Part 4.2 requirements. AI model decisions, chart-image interpretation, and voice belong to Part 4.3 and are not implemented. CSV loading is ungraded practice and is not used as evidence of streaming. The existing report.md/video document the submitted Part 4.1 version; the current Part 4.2 behavior and assumptions are documented in [docs/part4-2.md](docs/part4-2.md).

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

## Indicators, simulated accounts, and backtesting

In **Market data**, edit Fast SMA and Slow SMA (defaults 5/20). Cyan and gold lines use closing prices; arrows identify upward/downward crossovers. The legend follows the crosshair-selected candle, or the latest candle when the pointer is outside the chart. Unfinished-candle calculations and markers are labeled provisional and never place orders. Editing a chart window preserves the replay cursor.

Open **Strategy & backtests**. Choose a source, symbol, interval, SMA windows, initial cash, fixed buy quantity, fee per fill, and adverse slippage in basis points. Chart settings and experiment settings are independent; every saved run retains its own parameters.

- **Constructed demo recording:** deterministic offline experiment; labeled synthetic. Run backtest evaluates decisions and account outcomes, rather than merely replaying prices.
- **Saved Yahoo observations:** evaluates the actual receipt stream causally. Optional UTC start/end filter receipt times. Maximum 5,000 receipts per experiment; choose a narrower range for longer captures.
- **Downloaded Yahoo daily history:** Fetch Yahoo history (for example AAPL / 1y), then select the saved download and Run backtest. It uses completed unadjusted daily bars and excludes today's bar conservatively. Downloads are separate from the required streaming connection and retained as frozen snapshots with a SHA-256 fingerprint. Failures show an error, not synthetic fallback data.

The result shows cash, position/average cost, realized/unrealized P&L, account equity/return, maximum drawdown, order status, fills/fees, and decision-time candles with both SMAs, crossovers, and an equity curve. Saved experiments can be reopened after a browser/server restart. Start live paper account is available for the Yahoo-observation source. It warms up without retrospective orders and processes future observations even when the browser is closed. Pause cancels pending orders; Resume preserves balances while skipping downtime decisions. Server restart automatically pauses active accounts.

The strategy is long only: buy the configured whole-unit quantity when flat on an upward crossover; sell the entire position on a downward crossover. Daily backtests execute at the next bar's open. Recorded/live streams use the next eligible new source price after the decision receipt. No same-candle close fill or future close is used. Fees enter cost basis; slippage worsens both buys and sells. No shorting, borrowing, dividends, interest, or guaranteed liquidity is modeled. Remaining positions are marked, not forcibly liquidated at the sample end. See [full execution/accounting and uncertainty notes](docs/part4-2.md).

SQLite adds history_sets, simulation_runs, simulated_orders, and simulated_fills without deleting market tables. Run results also preserve decision-time candles and equity samples. Historical results and paper balances are separate from the live observation store and from each other.

## Data limits

Yahoo streaming quotes are sampled observations, not a complete exchange trade tape. Candles summarize captured ticks; missing intervals remain gaps. Values and delays depend on instrument and market hours. The application does not certify exchange-level real-time data, infer market-open status, or invent historical candles before recording began.

For equities, `day_volume`, when present, is treated as a cumulative session total. Candle volume sums differences in source-time order across adjacent usable totals on the same New York calendar date. An unknown baseline, missing total, decrease/reset, or date boundary makes the affected candle's volume unknown. The first captured candle is usually unknown. Attribution of a cumulative change to the later tick's interval is an estimate when ticks span gaps. Extended-hours provider resets are handled as decreases, not guessed away. BTC's rolling 24-hour volume is retained in the ledger but never used as candle volume. The actual overnight AAPL/MSFT messages received during verification omitted `day_volume`; regular-hours live equity volume still needs a separate observation. Demo and deterministic tests verify the volume chart and calculations.

Yahoo has no reliable trade identity/revision number in this stream. Exact normalized payload repeats share one observation with multiple receipt records. Changed messages at the same timestamp are retained as distinct observations. Only a producer-supplied event identity plus revision can replace an older version in the effective candle view. Old versions remain stored. The demo exercises this explicit correction mechanism; it is not claimed as a Yahoo feature.

## Verification

```powershell
.\scripts\test.ps1
```

Runs isolated SQLite, aggregation, API/WebSocket, and feed lifecycle tests with the upstream off. It exits nonzero on failure and uses a fresh database directory per run. It does not edit source. For UI changes, also follow [docs/browser-checks.md](docs/browser-checks.md). Observed results and limitations are recorded in [docs/verification.md](docs/verification.md).

Automated browser checks use the real built Vue UI, FastAPI routes/WebSocket, and a new isolated SQLite database, with Yahoo off:

```powershell
cd frontend
npm run build
$env:E2E_BROWSER_CHANNEL = 'chrome'  # Use installed Chrome on this Windows computer.
npm run test:e2e
```

For bundled Chromium instead, omit E2E_BROWSER_CHANNEL and install it once with `npx playwright install chromium`. The [GitHub Actions workflow](.github/workflows/checks.yml) runs locked installs, Python tests, the frontend build, and Chromium browser checks on every push and pull request, without provider credentials or network-dependent market tests. Browser failure screenshots/traces are uploaded as artifacts. Real Yahoo/history availability is checked separately and never stubbed as live evidence.

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

Submission evidence: [tool and model disclosure](AI-USE.md), [curated evidence log](docs/evidence-log.md), [clean-checkout verification](docs/clean-checkout-verification.md), and [56-second combined video](docs/part4-1-demo.mp4). The video labels its live-recording excerpt and its two verification-screenshot sections separately.

References: [yfinance WebSocket documentation](https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html), [Lightweight Charts documentation](https://tradingview.github.io/lightweight-charts/docs), [TradingView](https://www.tradingview.com/). TradingView Lightweight Charts™ is used under its Apache 2.0 license; see frontend node_modules/lightweight-charts/LICENSE and NOTICE. yfinance is an independent tool, not an official Yahoo library.
