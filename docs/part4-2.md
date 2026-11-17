# Part 4.2 - indicators, simulated accounting, and historical evaluation

## Implemented system

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

## SMA and crossover definition

SMA(N) is the arithmetic mean of the latest N available closing prices. No value is emitted before N bars. Fast and slow windows satisfy 1 <= fast < slow <= 500. The default is 5/20. Windows count observed bars; missing intervals are not fabricated. The incremental implementation retains only its bounded window and uses math.fsum to limit accumulated floating-point drift. A separate batch implementation computes each full window directly.

For difference fast-minus-slow, buy crossover means previous difference <= 0 and current difference > 0; sell means previous difference >= 0 and current difference < 0. There is no entry merely because the first fully warmed SMA happens to be above the other. Flat equality is not a repeated buy/sell signal.

The chart previews an unfinished bar by combining the committed completed-bar window with its current close. The preview does not update committed indicator state and is explicitly labeled provisional. Strategy decisions consume completed candles only. A source-time candle can later be corrected; a decision already made is not retroactively rewritten. Saved decision rows preserve the exact OHLC/SMA and known_at time used for that decision, which the strategy chart plots.

References and checks:

- [TradingView Moving Averages](https://www.tradingview.com/support/solutions/43000502589-moving-averages/): published SMA(3) example with closes 5,6,7,8,9 produces 6,7,8 after warm-up. Tested exactly.
- [pandas rolling-window documentation](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html): tests compare batch and incremental results with Series.rolling(N, min_periods=N).mean() across 1,200 deterministic prices and windows 1,2,5,20,200, within 1e-11 absolute tolerance. Crossovers are independently compared with shifted pandas series.
- Actual downloaded AAPL history was also compared with pandas: all 250 rows and every crossover agreed, with maximum observed SMA difference 0.0 in that run. See [historical evidence JSON](part4-2-history-evidence.json).

## Strategy and execution assumptions

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

## Accounting

Internal monetary arithmetic uses Decimal constructed from source decimal strings. Buy fill price = observed price * (1 + slippage_bps/10000); sell fill price = observed price * (1 - slippage_bps/10000). Fee is fixed per actual fill, not per unfilled/rejected order.

- Buy: cash decreases by quantity * fill_price + fee; position cost basis increases by that same amount.
- Sell: allocate weighted-average basis proportional to quantity sold. Net proceeds = quantity * fill_price - fee. Realized P&L increases by net proceeds minus allocated basis.
- Market value = held quantity * latest available mark. Unrealized P&L = market value - remaining basis.
- Equity = cash + market value. Total P&L = equity - initial cash. Return = (equity / initial cash - 1) * 100.
- Maximum drawdown is the largest percentage decline from an earlier equity peak in the sampled equity curve, including initial cash as the first peak. It is not an intrabar worst-case estimate.

The UI rounds currency for readability; components rounded independently can differ by one cent from a displayed summed total. Exact Decimal state is preserved as strings in state_json; fills carry eight-decimal prices/results for inspection. No balancing trade is fabricated to hide rounding.

Known example (zero fee/slippage): $1,000 cash; buy 4 at $100 -> $600 cash. Mark at $110 -> $40 unrealized. Sell 1 at $110, then the remaining 3 at $105 -> $1,025 cash, zero position, $25 realized, $0 unrealized. A separate fee/slippage example verifies fee-inclusive average cost, partial basis allocation, adverse prices, and rejected orders. A peak-to-trough example checks drawdown.

## Persistence and reproducibility

Schema is additive; market observation/receipt tables are preserved:

- history_sets: immutable dataset ID, symbol, fetch time, source description, SHA-256 digest, and full JSON daily-bar snapshot.
- simulation_runs: run ID/kind/status/times, exact parameter JSON, source metadata/digest, restartable paper state, full result JSON, and last processed receipt.
- simulated_orders: (run_id, order_id) key, status, and full order payload; status changes are updated atomically with account state.
- simulated_fills: (run_id, fill_id) key and immutable fill payload; repeated saves cannot duplicate fills.

Result JSON includes decision-time candles, signals, fills, order reasons, and equity samples. Backtests always create a fresh account and save an input fingerprint. Reopening a run does not rerun or alter it. Separate paper accounts and backtests do not share money. Local runtime databases are ignored by Git.

Recorded experiments are bounded to 5,000 receipts for this inspectable implementation; aggregation reconstructs the current prefix rather than using a production incremental bar index. Historical daily samples are suitable for longer tests. Data-source errors never silently substitute fixture data.

## Observed real-data experiment

On November 16, 2026, Yahoo returned 250 completed AAPL daily bars for a one-year download. The sample spans November 17, 2025 through November 13, 2026; the current day's unfinished/recently updated bar was excluded. Parameters: SMA 5/20, $10,000 starting cash, 10 units per buy, $1 per fill, 5 bps adverse slippage.

Observed result: 13 fills, $6,893.09 cash, 10 units held, $10,455.79 equity, 4.5579% sample return, 3.5434% sampled maximum drawdown, and $13 fees. Rounded realized/unrealized P&L were $391.33 / $64.45. The saved input digest is `70450a0e1adc80970ffccc430a92336c9852f8e0c9e3f1e6eec697b8a78068e7`. Repeating that frozen dataset/config produced an identical result. The JSON evidence retains the source/fetch time, configuration, decision endpoints, and first fills.

These are measured historical simulation results, not a forecast or an optimized strategy recommendation. The demonstration fixture is separately labeled synthetic. A different sample, timing model, fee/slippage value, or window can materially change the outcome.

## What remains uncertain

The selected-symbol universe consists of instruments available now, so survivorship bias is not eliminated. Repeated parameter tuning on one sample can overfit; no optimization, out-of-sample validation, or profitability guarantee is claimed. Today's vendor history can include later corrections; unadjusted prices omit dividends and may distort returns around corporate actions. Quote-based fills do not model spreads, market depth, partial liquidity, or actual order-book execution. Fees/slippage are estimates, not guaranteed transaction costs. Paper-account restart is deliberately a pause, not uninterrupted broker execution. Full-history reconstruction and retained result JSON are intended for classroom-scale samples, not unlimited sessions.

GitHub Actions runs deterministic offline Python/build/browser checks on pushes and pull requests. Provider availability checks are intentionally separate: CI passes cannot establish that Yahoo is currently sending data. The Part 4.1 native date-input and overnight live-volume verification limits remain documented in the original record; the current browser suite verifies the added strategy controls and saved results without inventing provider evidence.
