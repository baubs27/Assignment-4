# Part 4.2 - Indicators, Simulated Trading, and Backtesting

Prepared November 17, 2026. This report contains the implementation summary, design/execution assumptions, verification results, AI disclosure, curated evidence log, repository/version, and demonstration-video information together in one file.

## Repository and identifying commit

- **Repository:** [baubs27/Assignment-4](https://github.com/baubs27/Assignment-4).
- **Part 4.2 source tree:** [codex/part-4-2-strategy](https://github.com/baubs27/Assignment-4/tree/codex/part-4-2-strategy). Use this branch for Part 4.2; the default main branch retains the earlier Part 4.1 submission.
- **Verified application commit:** [5dd85d78669a50394690e44f9d0fae3237c3df8a](https://github.com/baubs27/Assignment-4/commit/5dd85d78669a50394690e44f9d0fae3237c3df8a).
- **Hosted verification:** [GitHub Actions run 44005363811](https://github.com/baubs27/Assignment-4/actions/runs/44005363811), completed successfully for that exact commit. Its status and commit were checked again while preparing this report.
- The report/video preparation changes documentation and media only. It does not change the verified application, dependency locks, or tests. [Earlier Part 4.1 report](https://github.com/baubs27/Assignment-4/blob/86e0a32a34338d3376c97c2629362225b77057db/report.md) remains available in Git history.

## Combined demonstration and process video

**[Watch the 54-second Part 4.2 video](https://github.com/baubs27/Assignment-4/blob/9b71f35082cb745dc680f1b250c7206377d63b6f/docs/part4-2-demo.mp4)**. [Direct MP4 link](https://raw.githubusercontent.com/baubs27/Assignment-4/9b71f35082cb745dc680f1b250c7206377d63b6f/docs/part4-2-demo.mp4).

Video artifact commit: `9b71f35082cb745dc680f1b250c7206377d63b6f`. File SHA-256: `014e960b330a565d3f568b1a7129f4feaec5cd3d0a270c9a6efa0a32bb518c70`.

The single captioned video combines 18 seconds from the student's November 17 recording with 36 seconds of an additional actual-workstation capture. It shows Yahoo price/SMA overlays, the constructed AAPL backtest and its account/decision/trade views, then the saved AAPL daily-history result and equity/fills. The sources are labeled: constructed demo prices are not presented as live Yahoo data. The additional capture uses an isolated copy of the local database; it does not change the original account/market records. Captions identify a design decision: strategy orders become eligible after completed-bar decisions, while cash, position, and P&L remain inspectable.

The supplied recording was 72.67 seconds, longer than the one-minute maximum. Its later MSFT/constructed-demo attempt showed an empty-data warning because the demo fixture contains AAPL only. The original recording is preserved. The submission copy uses a shorter excerpt plus a successful matching-source capture instead of presenting that unsuccessful attempt as a completed backtest. It is a silent, captioned MP4; the supplied audio measured approximately -91 dB. No separate process recording is required. The preparation and observed failure are documented in the evidence log below.

## Completion summary

The existing Vue/FastAPI/SQLite workstation now derives two configurable closing-price SMAs and their crossovers, applies the completed-bar crossover rule to simulated accounts, and evaluates historical decisions/outcomes. The Market data chart shows both averages and provisional/confirmed signal status. Strategy & backtests exposes parameter/source selection, cash/positions, orders/fills, realized/unrealized P&L, equity/return/drawdown, saved runs, and decision-time charts. Live paper accounts start, pause, and resume independently of an open browser.

Part 4.1 Yahoo capture, source-age/status display, immutable observations/receipts, and read-only replay are retained. These remain distinct from the separate historical-download service and from explicitly labeled constructed fixtures. No actual brokerage orders or Part 4.3 model/audio service is connected.

## Startup, data flow, and persistent records

From the repository root in PowerShell:

```powershell
.\scripts\install.ps1          # Restore locked packages and build Vue.
.\scripts\start.ps1            # Start localhost:8000 with Yahoo enabled.
.\scripts\start.ps1 -Offline   # Start with Yahoo disconnected.
.\scripts\test.ps1             # Run isolated offline Python checks.
```

Select an existing Python 3.12+ executable with MARKET_PYTHON if necessary. Dependencies belong to .runtime/python and frontend/node_modules. SQLite initializes automatically at data/market.sqlite3 with foreign keys and WAL; MARKET_DB can select another file. Demo initialization is idempotent. No database password, Yahoo login, or private credential is embedded in source or this report. Local databases, caches, packages, and generated builds are excluded from Git.

```text
Yahoo WebSocket -> validated observations + append-only receipts in SQLite
    -> as-of-receipt/source-time candles -> SMA previews / completed-bar decisions
    -> pending simulated order -> later eligible price -> fill/account/equity
    -> SQLite run/order/fill records -> Vue strategy lab and ledgers

Frozen Yahoo daily snapshot -> sequential next-open historical evaluator
Constructed/recorded receipts -> receipt-order historical evaluator
Both evaluators -> shared completed-bar strategy and Decimal broker
```

Raw market records retain observation identity, raw payload, source/receipt times, duplicate receipts, and identifiable revisions. Completion is computed from interval end and the live/replay clock. New simulation tables are additive and are described below. The full disclosure, methods, checks, failure analysis, and uncertainty are included inline; repository links are supporting artifacts, not substitutes for those sections.

## Design, execution, accounting, and historical results

### Implemented system

The existing Vue/FastAPI/SQLite workstation now has two closing-price SMAs, crossover markers, an experiment/paper-account interface, persistent orders/fills/accounts, and a historical evaluator. Part 4.1 data capture and replay remain intact. No real trading account, order router, or Part 4.3 AI service is connected.

| Module | Responsibility |
| --- | --- |
| backend/indicators.py | Independent batch SMA, incremental bounded-window SMA, equality-aware crossover, provisional chart previews |
| backend/simulation.py | Shared strategy, Decimal broker, causal recorded-tick runner and next-open daily-bar runner |
| backend/research.py | Frozen Yahoo daily imports, saved experiments, paper lifecycle/worker, SQLite persistence |
| backend/research_api.py | Validated parameters, history/backtest/account HTTP routes |
| frontend/src/StrategyLab.vue | Parameters, source selection, accounts, saved experiments, orders/fills/decisions, assumptions |
| frontend/src/ResearchChart.vue | Decision-time OHLC, SMA lines, crossovers, and account equity |
| frontend/e2e/workstation.spec.js | Real browser regression checks with deterministic offline inputs |
| .github/workflows/checks.yml | Push/PR Python, build, and browser checks without provider secrets |

### SMA and crossover definition

SMA(N) is the arithmetic mean of the latest N available closing prices. No value is emitted before N bars. Fast and slow windows satisfy 1 <= fast < slow <= 500. The default is 5/20. Windows count observed bars; missing intervals are not fabricated. The incremental implementation retains only its bounded window and uses math.fsum to limit accumulated floating-point drift. A separate batch implementation computes each full window directly.

For difference fast-minus-slow, buy crossover means previous difference <= 0 and current difference > 0; sell means previous difference >= 0 and current difference < 0. There is no entry merely because the first fully warmed SMA happens to be above the other. Flat equality is not a repeated buy/sell signal.

The chart previews an unfinished bar by combining the committed completed-bar window with its current close. The preview does not update committed indicator state and is explicitly labeled provisional. Strategy decisions consume completed candles only. A source-time candle can later be corrected; a decision already made is not retroactively rewritten. Saved decision rows preserve the exact OHLC/SMA and known_at time used for that decision, which the strategy chart plots.

References and checks:

- [TradingView Moving Averages](https://www.tradingview.com/support/solutions/43000502589-moving-averages/): published SMA(3) example with closes 5,6,7,8,9 produces 6,7,8 after warm-up. Tested exactly.
- [pandas rolling-window documentation](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html): tests compare batch and incremental results with Series.rolling(N, min_periods=N).mean() across 1,200 deterministic prices and windows 1,2,5,20,200, within 1e-11 absolute tolerance. Crossovers are independently compared with shifted pandas series.
- Actual downloaded AAPL history was also compared with pandas: all 250 rows and every crossover agreed, with maximum observed SMA difference 0.0 in that run. See [historical evidence JSON](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/docs/part4-2-history-evidence.json).

### Strategy and execution assumptions

All accounts start with configured cash and zero position. Whole-unit fixed-size buys are allowed only when flat. A downward crossover exits the entire position. The underlying accounting supports partial sales and is verified separately with known examples. No pyramiding, shorting, margin/borrowing, dividends, interest, or stock-lending costs are modeled.

Orders and fills are different records. A crossover can create a pending order; only a subsequent eligible price can fill it. Insufficient cash/position or inability to pay the fee rejects an order without a fill. A new opposing crossover cancels an unfilled pending order. Pausing also cancels pending orders. An unfillable final order is cancelled with an end-of-sample explanation. No terminal liquidation is invented; positions remain marked and unrealized.

| Source/mode | Decision information | Fill rule |
| --- | --- | --- |
| Downloaded daily history | Complete daily bar closes and all earlier selected closes | Pending order fills at the next selected daily bar's open, before that next bar's close is processed |
| Recorded observation backtest | Only the receipt prefix currently available; source-time aggregation as known at that receipt clock | New, nonduplicate eligible source price with a later receipt ID than the decision and source time at/after eligible_at |
| Live paper account | Available completed bars; history at account start is warm-up only | Future eligible observation after the completed-bar decision; runs in the backend without requiring an open browser |

Daily timestamps label UTC session dates; next-open timestamps are bar labels, not claims of exact exchange execution time. Today's daily bar is conservatively excluded even after market close. Selection-range warm-up uses only bars inside that selection. Imported bars are today's vendor data vintage; later vendor corrections are a limitation, not a claim of point-in-time exchange history. Recorded-stream decisions freeze actual as-of-receipt candles and do not incorporate later revisions into earlier decisions. Receipt clocks are made monotonic for simulation while original records remain unchanged.

The first eligible tick that causes a completed-bar decision cannot fill the order generated by that same decision: pending fills are processed before new decisions for each receipt. Historical bar fills similarly precede processing that bar's close. Tests alter future closes and compare earlier decision/fill prefixes to check this causality boundary.

Paper-account state includes the indicator windows, previous difference, decision watermark, last processed receipt, balances, position basis, pending orders, fills, and equity. Pause and worker processing are serialized to avoid losing a pause request to a concurrent save. Restart pauses existing active accounts and cancels pending orders. Resume warms through the missed completed bars without orders, updates the mark, skips old receipts, and preserves cash and positions. Downtime is never represented as active fills.

### Accounting

Internal monetary arithmetic uses Decimal constructed from source decimal strings. Buy fill price = observed price * (1 + slippage_bps/10000); sell fill price = observed price * (1 - slippage_bps/10000). Fee is fixed per actual fill, not per unfilled/rejected order.

- Buy: cash decreases by quantity * fill_price + fee; position cost basis increases by that same amount.
- Sell: allocate weighted-average basis proportional to quantity sold. Net proceeds = quantity * fill_price - fee. Realized P&L increases by net proceeds minus allocated basis.
- Market value = held quantity * latest available mark. Unrealized P&L = market value - remaining basis.
- Equity = cash + market value. Total P&L = equity - initial cash. Return = (equity / initial cash - 1) * 100.
- Maximum drawdown is the largest percentage decline from an earlier equity peak in the sampled equity curve, including initial cash as the first peak. It is not an intrabar worst-case estimate.

The UI rounds currency for readability; components rounded independently can differ by one cent from a displayed summed total. Exact Decimal state is preserved as strings in state_json; fills carry eight-decimal prices/results for inspection. No balancing trade is fabricated to hide rounding.

Known example (zero fee/slippage): $1,000 cash; buy 4 at $100 -> $600 cash. Mark at $110 -> $40 unrealized. Sell 1 at $110, then the remaining 3 at $105 -> $1,025 cash, zero position, $25 realized, $0 unrealized. A separate fee/slippage example verifies fee-inclusive average cost, partial basis allocation, adverse prices, and rejected orders. A peak-to-trough example checks drawdown.

### Persistence and reproducibility

Schema is additive; market observation/receipt tables are preserved:

- history_sets: immutable dataset ID, symbol, fetch time, source description, SHA-256 digest, and full JSON daily-bar snapshot.
- simulation_runs: run ID/kind/status/times, exact parameter JSON, source metadata/digest, restartable paper state, full result JSON, and last processed receipt.
- simulated_orders: (run_id, order_id) key, status, and full order payload; status changes are updated atomically with account state.
- simulated_fills: (run_id, fill_id) key and immutable fill payload; repeated saves cannot duplicate fills.

Result JSON includes decision-time candles, signals, fills, order reasons, and equity samples. Backtests always create a fresh account and save an input fingerprint. Reopening a run does not rerun or alter it. Separate paper accounts and backtests do not share money. Local runtime databases are ignored by Git.

Recorded experiments are bounded to 5,000 receipts for this inspectable implementation; aggregation reconstructs the current prefix rather than using a production incremental bar index. Historical daily samples are suitable for longer tests. Data-source errors never silently substitute fixture data.

### Observed real-data experiment

On November 16, 2026, Yahoo returned 250 completed AAPL daily bars for a one-year download. The sample spans November 17, 2025 through November 13, 2026; the current day's unfinished/recently updated bar was excluded. Parameters: SMA 5/20, $10,000 starting cash, 10 units per buy, $1 per fill, 5 bps adverse slippage.

Observed result: 13 fills, $6,893.09 cash, 10 units held, $10,455.79 equity, 4.5579% sample return, 3.5434% sampled maximum drawdown, and $13 fees. Rounded realized/unrealized P&L were $391.33 / $64.45. The saved input digest is `70450a0e1adc80970ffccc430a92336c9852f8e0c9e3f1e6eec697b8a78068e7`. Repeating that frozen dataset/config produced an identical result. The JSON evidence retains the source/fetch time, configuration, decision endpoints, and first fills.

These are measured historical simulation results, not a forecast or an optimized strategy recommendation. The demonstration fixture is separately labeled synthetic. A different sample, timing model, fee/slippage value, or window can materially change the outcome.

### What remains uncertain

The selected-symbol universe consists of instruments available now, so survivorship bias is not eliminated. Repeated parameter tuning on one sample can overfit; no optimization, out-of-sample validation, or profitability guarantee is claimed. Today's vendor history can include later corrections; unadjusted prices omit dividends and may distort returns around corporate actions. Quote-based fills do not model spreads, market depth, partial liquidity, or actual order-book execution. Fees/slippage are estimates, not guaranteed transaction costs. Paper-account restart is deliberately a pause, not uninterrupted broker execution. Full-history reconstruction and retained result JSON are intended for classroom-scale samples, not unlimited sessions.

GitHub Actions runs deterministic offline Python/build/browser checks on pushes and pull requests. Provider availability checks are intentionally separate: CI passes cannot establish that Yahoo is currently sending data. The Part 4.1 native date-input and overnight live-volume verification limits remain documented in the original record; the current browser suite verifies the added strategy controls and saved results without inventing provider evidence.


## Verification results and clean-checkout evidence

These results apply to application commit 5dd85d78669a50394690e44f9d0fae3237c3df8a, implemented and tested on November 16, 2026. The document/media update does not claim a new market-data experiment or a new application test run on November 17.

| Check | Observed result and boundary |
| --- | --- |
| Local Python tests | **27 passed**. Covers inherited persistence/candle behavior plus SMA references, crossovers, provisional handling, accounting, historical-provider boundaries, causal execution, paper persistence/pause/resume/restart, and API validation. One existing third-party Starlette/httpx deprecation warning remains. |
| Frontend production build | **Passed**, 19 modules, approximately 288.26 kB JavaScript before gzip. |
| Real-browser suite | **4 passed** against built Vue, FastAPI HTTP/WebSocket, and a fresh SQLite database with Yahoo off. Browser HTTP requests to external sites are blocked. |
| Browser SMA check | Seek to 276/276 demo receipts, set windows 2/3, and inspect the latest forming candle: **101.8600 / 101.5433**, explicitly provisional. Editing windows preserves the cursor. |
| Browser account check | Run the 2/3 constructed backtest with $1,000/four-unit buys; visible account, fills, and decision values agree with the persisted result. Reload and reopen the saved run successfully. |
| Browser lifecycle/error/layout checks | Start and pause a paper account; show a readable empty-source error; verify strategy controls at 390 px without document overflow. Page exceptions fail the applicable checks. |
| Known zero-cost accounting | Buy 4 at $100, sell 1 at $110, sell 3 at $105: **$1,025 cash, zero position, $25 realized and $0 unrealized**. |
| Fee/slippage accounting | $1 per fill and 100 bps adverse slippage: first four-unit buy at a $100 quote fills at $101, leaving $595 cash and $405 basis. After a one-unit sale at a $110 quote and a $110 mark: **$6.65 realized, $26.25 unrealized, $32.90 total P&L**. |
| Drawdown/rejections/idempotency | Peak-to-trough arithmetic, invalid marks, insufficient cash/position, and repeated-fill prevention passed. |
| Causality checks | Altering future closes preserves earlier decision/fill prefixes. Incomplete candles do not generate orders. Later corrections do not rewrite earlier decisions. Final pending orders are cancelled rather than filled with invented future prices. |
| Paper restart/lifecycle | Existing bars warm up without retrospective orders; pause cancels pending orders; restart pauses active accounts; resume preserves balances while skipping downtime decisions. Older active accounts remain covered even after more than 50 newer saved experiments. |
| Actual Yahoo daily history | 250 completed AAPL bars; every SMA/crossover agreed with pandas, maximum observed SMA difference **0.0**; repeated frozen-data evaluation returned an identical result. Detailed results appear in the historical experiment section above. |
| Hosted GitHub Actions | **Success** for the exact commit, including locked Python/npm installs, Python tests, production build, Chromium installation, and the four browser checks. |

### Clean-checkout procedure used by hosted CI

The successful hosted run began with actions/checkout on a fresh Ubuntu runner, Python 3.12, and Node.js 22. It installed backend/requirements-lock.txt, ran python -m pytest tests -q, ran npm ci and npm run build in frontend, installed Chromium with npx playwright install --with-deps chromium, and ran npm run test:e2e. This verifies Part 4.2 from the published source independently of the original workstation's database, installed frontend packages, or generated build.

The workflow runs on **push**, **pull_request**, and **workflow_dispatch**, with repository contents read-only permission. It needs no Yahoo/provider secret. Browser failure screenshots/traces are uploaded as an artifact when tests fail. Its server uses a new isolated database on localhost:8765 and is stopped after the suite. Passing offline CI establishes deterministic implementation checks; it does not establish current Yahoo availability.

Reproduction commands for the browser suite after installing dependencies:

```powershell
cd frontend
npm run build
$env:E2E_BROWSER_CHANNEL = 'chrome'  # This Windows computer uses installed Chrome.
npm run test:e2e
```

On a clean environment using bundled Chromium, omit E2E_BROWSER_CHANNEL and install Chromium first. The code-level [workflow](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/.github/workflows/checks.yml), [Python reference tests](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/tests/test_indicators.py), [accounting/causality tests](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/tests/test_simulation.py), [research API tests](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/tests/test_research_api.py), and [browser tests](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/frontend/e2e/workstation.spec.js) are supporting links. The exact hosted [run summary and logs, which may require GitHub sign-in](https://github.com/baubs27/Assignment-4/actions/runs/44005363811) are publicly accessible through GitHub.

## Curated, redacted evidence log

The selected entries below connect the request, resulting artifact/code, observed check, decision, and remaining uncertainty. They omit credentials, personal account information, absolute local user paths, and private third-party messages. They are not a complete chat export. All application file links identify the verified commit above.

### 1. Derive and verify the indicators

- **Intent / instruction excerpt:** "Display two simple moving averages of different lengths and their crossover" and "compare batch and incremental calculations."
- **Artifact:** [backend/indicators.py](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/backend/indicators.py) and [tests/test_indicators.py](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/tests/test_indicators.py).
- **Observation:** TradingView's SMA3 example returned 6,7,8 after warm-up. Batch/incremental calculations matched pandas over 1,200 deterministic closes and five window sizes; independently shifted pandas means produced the same crossover directions. All 250 real historical rows also matched.
- **Decision:** Use one closing-price definition, explicit warm-up, and equality-aware crossover boundaries in chart and strategy calculations. Mark unfinished previews separately rather than consuming them as settled prices.
- **Uncertainty:** Correct arithmetic does not make a lagging indicator predictive or guarantee profits. Sparse observations mean windows count available bars rather than a guaranteed uninterrupted time span.

### 2. Enforce the completed-candle and next-price boundary

- **Intent / instruction excerpt:** "using only information available at each decision time" and "explain how unfinished candles are handled."
- **Artifact:** Strategy.close(), receipt_step(), and simulate_bars() in [backend/simulation.py](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/backend/simulation.py).
- **Relevant generated-code excerpts:**

```python
# Strategy.close(): no provisional or already-processed candle decision.
if not c['complete'] or c['timestamp'] <= self.last_bar:
    return

# Broker.fill_pending(): a new decision cannot fill from its own receipt.
if receipt_id is not None and receipt_id <= o['decision_receipt']:
    continue

# Daily evaluator: fill a pre-existing order at this open before using this close.
s.broker.fill_pending(c['open'], c['timestamp'])
at = c['timestamp'] + INTERVALS[config['interval']]
s.broker.mark_to_market(c['close'], at)
s.close(c, at)
```

- **Observation:** Tests mutated later closes and compared earlier prefixes; prior decisions/fills were unchanged. A late correction did not rewrite earlier decisions, and no unfinished candle produced a strategy decision.
- **Decision:** Freeze decision-time OHLC/SMA values and process execution before new decisions at each eligible event. Keep an unfillable final order cancelled/pending-explanation visible, without a fabricated fill.
- **Uncertainty:** Today's vendor historical data may incorporate later corrections; the algorithmic causality checks are not proof of point-in-time vendor-data provenance.

### 3. Check the broker independently of strategy profits

- **Intent / instruction excerpt:** "Track orders and fills, cash, positions, and realized and unrealized profit or loss" and "Check simulated accounting against known examples."
- **Artifact:** Broker in [backend/simulation.py](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/backend/simulation.py), [known-example tests](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/tests/test_simulation.py), persisted records in [backend/research.py](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/backend/research.py).
- **Observation:** The $1,000 example ended at $1,025 with $25 realized and no remaining position. Fee/slippage, weighted-average partial basis allocation, duplicate fills, drawdown, and rejected orders passed. Browser values matched the stored result and survived reload.
- **Decision:** Keep orders separate from fills, include buy fees in basis, deduct sell fees from proceeds, and use Decimal internally. Persist money/decision state atomically with order/fill records.
- **Uncertainty:** The simulated price/fee/liquidity model does not reproduce a real order book, partial liquidity, or guaranteed execution.

### 4. Revised browser verification: inspect the intended candle

- **Intent / instruction excerpt:** "Verify the moving averages and crossover against a trusted reference" and "Keep browser tests."
- **Failed check:** The first browser run had three passes and one failure. It expected latest provisional values 101.8600 / 101.5433 but received 100.0850 / 99.9067 because a historical candle remained selected by the chart crosshair after scrolling.
- **Evidence / artifact:** The browser log and selected-candle behavior, recorded in [verification.md](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/docs/verification.md); the corrected [Playwright test](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/frontend/e2e/workstation.spec.js).
- **Relevant generated test code:**

```javascript
await page.getByLabel('Fast SMA window').fill('2')
await page.getByLabel('Slow SMA window').fill('3')
await page.mouse.move(5,5) // Inspect latest candle instead of a hovered historical candle.
await expect(page.getByTestId('chart-sma')).toHaveText('101.8600 / 101.5433')
```

- **Decision / recheck:** Specify which candle is being verified; move the pointer outside the chart before asserting the latest value. No indicator calculation was changed to fit the expectation. All four browser checks subsequently passed locally and in hosted CI.
- **Uncertainty:** Native date-range entry from Part 4.1 remains a separate manual-verification item; this corrected test does not establish that unrelated UI operation.

### 5. Match the selected instrument to an actual dataset

- **Intent / instruction excerpt:** The student supplied a Part 4.2 recording to demonstrate the app.
- **Observed failed attempt:** Near the end of the 72.67-second input, MSFT was selected with Constructed demo recording. The UI returned **"No completed candles in this selection."** The demo seed contains AAPL, not MSFT.
- **Artifact:** Dataset-specific fixture in [backend/demo.py](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/backend/demo.py), source selection in [StrategyLab.vue](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/frontend/src/StrategyLab.vue), and the source-recording review during report preparation.
- **Decision / recheck:** Select AAPL for the constructed demo; use saved Yahoo observations or an actual historical download for another instrument. The added capture runs the matching AAPL demo and reopens the actual saved AAPL historical run, showing their account/decision/trade views without changing the algorithm or fabricating missing data.
- **Uncertainty:** A selected symbol/time range still needs enough completed bars to warm up both SMAs. A readable empty-data warning is not a successful backtest and is not presented as one.

### 6. Evaluate actual frozen historical data

- **Intent / instruction excerpt:** "Show the resulting trades and account performance, and explain what the results establish and what they leave uncertain."
- **Artifact:** [historical evidence JSON](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/docs/part4-2-history-evidence.json), historical import/runner code, and the saved local SQLite snapshot/run.
- **Observation:** AAPL 1y produced 250 completed bars; SMA 5/20 with the stated costs produced 13 fills, $10,455.79 equity, 4.5579% sample return, and 3.5434% sampled maximum drawdown. Repeating that same frozen snapshot/configuration produced an identical result; every SMA/crossover matched pandas.
- **Decision:** Save source fingerprint, fetch time, parameters, decision-time candles, orders, fills, and equity so the outcome can be inspected. Display open positions as unrealized rather than inventing a closing trade.
- **Uncertainty:** The full imported snapshot lives in local SQLite; the committed JSON is a summary and selected observations, not all 250 source bars. A fresh download can differ in window/vintage. Current-symbol selection, repeated tuning, missing dividends/corporate-action adjustments, and estimated costs constrain interpretation.

### 7. Verify the published source in a separate environment

- **Intent / instruction excerpt:** "run automated checks on pushes using GitHub Actions."
- **Artifact:** [checks.yml](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/.github/workflows/checks.yml) and [hosted run 44005363811](https://github.com/baubs27/Assignment-4/actions/runs/44005363811).
- **Observation:** The hosted run for the exact submitted code commit succeeded through checkout, locked installs, Python tests, build, Chromium installation, and real-browser tests. It did not use the original workstation database or Yahoo credentials.
- **Decision:** Use deterministic source fixtures for reproducible push/PR checks, with browser traces/screenshots on failure, and keep real-provider observations separate.
- **Uncertainty:** CI cannot certify provider freshness or every possible market/account failure. The initial browser-package install also needed a lockfile update before npm ci; the committed manifest/lock then installed successfully locally and in CI.

## Tool and model disclosure (AI-USE)

### Agent, editor, model, and roles

The coding agent/editor used was **OpenAI Codex in the Codex desktop app**, identified in this session as a GPT-6-based coding agent. The exact model variant/selector label is not recorded in retained project evidence, so a more specific model name is not guessed. The student previously confirmed that no other coding agents, editors, or AI models were used for the assignment. No manual model switch was reported or documented.

Codex read the supplied requirements, extended the Vue/FastAPI/SQLite code, wrote SMA/accounting/causality/API/browser tests, investigated failures, ran local checks, downloaded actual Yahoo history for the labeled experiment, configured/checked GitHub Actions, prepared the video, and drafted this report. The student directed the work, tested the application, supplied the recordings, confirmed the disclosure, and authorized public GitHub publication of the video and supporting documents. Generated code and prose are AI-assisted; no independent student inspection of every generated line is claimed.

| Tool or component | Use in this work |
| --- | --- |
| Codex workspace editor and PowerShell | Inspect/edit source and Markdown, run the project commands, and prepare this self-contained report |
| Git and GitHub connector | Publish the authorized branch/artifacts and verify commit/hosted workflow status |
| Python 3.12, FastAPI, sqlite3, yfinance | Backend, Yahoo streaming/history, candle aggregation, persistence, and simulation |
| Python Decimal | Cash, position basis, fees, and P&L arithmetic |
| pandas | Independent SMA/crossover reference; not the production strategy decision implementation |
| Node.js/npm, Vue, Vite, Lightweight Charts | Build the dashboard, SMA overlays, strategy forms, ledgers, and price/equity charts |
| pytest and FastAPI TestClient | Deterministic reference, accounting, causality, lifecycle, and route/WebSocket checks |
| Playwright with Chrome/Chromium | Actual browser tests and the additional actual-app recording, using isolated databases |
| FFmpeg 9.0.2 and Playwright's recorder helper | Inspect duration/audio, record/re-encode the combined 54-second MP4, and add explanatory captions |

### Changed approaches and disclosure limits

The existing usable Python interpreter was reused instead of relying on the nonfunctional Windows Python alias. A mismatched frontend lockfile was updated before npm ci. The SMA browser assertion was revised to clear the crosshair selection instead of changing a correct calculation. The supplied video's MSFT/demo mismatch was resolved by choosing a matching dataset for the additional capture. The browser recorder's missing helper was installed only in the ignored project runtime. These are implementation/testing/media-tool changes, not evidence of an AI model switch.

The new video uses actual application captures and captions; no generative image/video model or fabricated account display is used. Its original recording is preserved. The earlier 56-second Part 4.1 video is not substituted for this Part 4.2 demonstration. The app itself has no chart-image model, AI decision provider, autonomous AI trader, or live-audio integration in Part 4.2.

The curated log above contains selected prompt excerpts, files/code, observations, decisions, and uncertainty rather than a complete chat export. Credentials, personal account information, local absolute paths, and private third-party material are excluded. The repository retains AI-USE.md as course documentation, but the complete disclosure needed to read this submission is included here.

## Remaining limitations and submission scope

- Historical results describe the selected sample and execution assumptions, not future profitability. Survivorship bias, overfitting from repeated tuning, vendor-data revisions, unadjusted corporate actions, omitted dividends/interest, and imperfect liquidity/cost modeling remain limitations.
- Maximum drawdown uses sampled equity marks rather than intrabar worst-case prices. Currency components are rounded independently for display and can differ by one cent when added; exact internal Decimal state is retained.
- Recorded-prefix experiments are bounded to 5,000 receipts. Full-history reconstruction and JSON account snapshots suit classroom-scale data rather than unlimited sessions or many simultaneous users.
- The application intentionally pauses paper accounts at restart. Resume skips downtime orders; it is not uninterrupted exchange/broker execution.
- The AAPL-only demo must not be selected as a source for MSFT or another instrument. Empty selections and insufficient warm-up can validly produce no trades.
- Earlier native date-range UI entry and overnight equity-volume verification limits are not claimed as resolved by the new strategy/browser checks. Actual real-time availability remains instrument/provider dependent.
- The full actual historical download is stored locally and excluded from Git. The public JSON provides its fingerprint, parameters, and result summary; it is not a standalone complete 250-bar replay file.

## Supporting artifacts and Canvas submission

All required narrative, verification, AI disclosure, and curated evidence content appears in this report. Optional supporting artifacts include the [README](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/README.md), [agent instructions](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/AGENTS.md), [data-flow/schema notes](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/docs/design-pipeline.md), [Part 4.2 implementation notes](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/docs/part4-2.md), [verification record](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/docs/verification.md), [historical evidence JSON](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/docs/part4-2-history-evidence.json), and [constructed-account screenshot](https://github.com/baubs27/Assignment-4/blob/5dd85d78669a50394690e44f9d0fae3237c3df8a/docs/part4-2-demo-backtest.png).

Upload **only report.md** to the Canvas Part 4.2 submission page. Source files and ZIP archives belong in the linked GitHub repository. The video must remain accessible to the instructor through the public link above. No Canvas submission has been performed by the coding agent.
