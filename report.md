# Part 4.1 - Market Data and the Dashboard

## Repository and submitted version

- **GitHub repository:** [baubs27/Assignment-4](https://github.com/baubs27/Assignment-4)
- **Submitted application and supporting-evidence commit:** [a4883cad6189f976b4a4daf57f2172f916488423](https://github.com/baubs27/Assignment-4/commit/a4883cad6189f976b4a4daf57f2172f916488423)
- **Clean-checkout application baseline:** [6c00865acc400e9988ff0c6cc9a3539d02866226](https://github.com/baubs27/Assignment-4/commit/6c00865acc400e9988ff0c6cc9a3539d02866226). The submission-support commit adds documentation and video; the application, dependency locks, and tests are unchanged from this verified baseline.

## Combined demonstration and process video

**[Watch the 56-second video](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/part4-1-demo.mp4)**. [Direct MP4 link](https://raw.githubusercontent.com/baubs27/Assignment-4/a4883cad6189f976b4a4daf57f2172f916488423/docs/part4-1-demo.mp4).

The single captioned video contains 44 seconds of the supplied live-workstation recording, followed by a six-second demo-replay verification screenshot and a six-second Yahoo-disconnection verification screenshot. The still-image sections are explicitly labeled. The demo is constructed teaching data, not live prices. Captions identify one design decision: browser connectivity and market-source freshness/status are measured separately. This combines the application demonstration and a brief process explanation; there is no separate process recording. The original 65.1-second recording was preserved while a shorter submission copy was prepared.

## What was completed

A local client-server workstation was implemented with a **Vue frontend, FastAPI backend, and SQLite database**. The backend subscribes to Yahoo Finance through yfinance's asynchronous WebSocket client for AAPL, MSFT, and BTC-USD. A separate FastAPI WebSocket sends derived candles and status to the browser. TradingView Lightweight Charts displays updating candlesticks and a corresponding volume pane when volume can be determined. The interface shows the selected symbol/timeframe, source, source-observation age, upstream feed status, backend connection status, OHLC values, and candle completion.

Incoming observations are retained with raw payloads, source timestamps, backend receipt timestamps, observation IDs, and receipt IDs. Saved Yahoo observations and a clearly separated demo dataset can be replayed with play, pause, step, reset, seek, and speed controls. Replay freezes its selected receipts and does not write to the recording. Available intervals are 1m, 5m, 15m, 1h, and UTC-day bars. CSV loading was not used as evidence of live streaming.

Setup commands and database initialization are documented in the [README](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/README.md). The [agent instructions](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/AGENTS.md) and [design/data-flow and SQLite schema notes](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/design-pipeline.md) describe the system that exists. Startup initializes SQLite automatically; no Yahoo login or credentials are embedded in the project. Recordings, installed packages, and generated builds remain outside source control.

## Key design decisions

1. **Separate observations from receipts.** An exact repeat reuses its immutable observation record but receives a new receipt record, so arrival evidence is retained without double-counting its contribution to a candle. A changed message at the same source timestamp is retained separately unless the producer supplies an explicit event identity and revision number. Earlier identifiable revisions remain stored; the newest revision seen so far supplies the effective value.
2. **Separate source order from arrival order.** Source time determines open, high, low, and close within each interval. Receipt ID order determines when observations become available during replay, making late arrivals and revisions visible at the appropriate cursor position. The same aggregation code serves live and replay views.
3. **Make completion and uncertainty explicit.** A bar is complete when its interval has ended relative to the live or replay clock. Completion is derived from timestamps and the selected clock, not treated as an exchange guarantee that no correction can arrive later. Equity volume uses differences between usable cumulative session totals. Missing baselines, missing totals, resets, and crypto rolling totals produce unknown volume rather than invented zeroes.
4. **Keep connectivity distinct from freshness.** The browser can remain connected while Yahoo is disconnected or source observations are stale. Source age is displayed independently; observations older than 60 seconds are marked stale.

## Verification results

The public repository was cloned into a clean verification directory. Dependencies were installed from its committed lockfiles rather than copied from the original working environment. The [clean-checkout verification record](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/clean-checkout-verification.md) documents the commands and results.

| Check | Observed result |
| --- | --- |
| Automated backend/API tests from clean checkout | **9 passed in 3.36 seconds**; one third-party Starlette/httpx deprecation warning |
| Clean frontend production build | Passed with Vite; 16 modules transformed |
| Fresh offline startup | Dashboard and health endpoint returned HTTP 200; SQLite initialized with 276 demo receipts and 275 unique observations; Yahoo remained disconnected |
| Course candle example, including a late middle observation | O100, H103, L100, C101, V11; forming before interval end and complete afterward |
| Actual Yahoo source-to-chart trace | AAPL observations at 02:27:23 and 02:27:34 UTC on November 12, 2026 produced O355.55, H355.55, L355.52, C355.52; browser, SQLite, and replay agreed |
| Duplicate/revision handling | Repeats did not double-count; same-time ambiguous changes were retained; explicit revisions became effective only after receipt |
| Replay and restart | Independent SQLite OHLC matched replay for all three captured symbols; repeated replay and an offline restart preserved counts and outcomes |
| Unavailable-feed condition | Disconnecting Yahoo left the browser/backend connection and stored candles available; stopping the backend showed offline feedback and restart recovery |

Supporting evidence includes the [detailed verification log](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/verification.md), [actual Yahoo capture results](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/live-capture-evidence.json), [before-restart results](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/offline-copy-evidence.json), and [after-restart results](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/restart-evidence.json).

## One failed approach and the resulting decision

The first Yahoo stop implementation relied on cancelling the listener. A subsequent status check showed a new connected session after Disconnect. Inspection found that the client could catch cancellation and return, allowing the adapter to retry. The decision was to track the intended lifecycle state explicitly: `stop()` sets `self.enabled = False` before cancellation, and `run()` checks that flag after listening and in its loop condition. This generated code is in [backend/feed.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/backend/feed.py). The [regression test](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/tests/test_feed.py) deliberately simulates swallowed cancellation and verifies that stopping leaves no task or reconnect. Actual browser disconnection then passed. This links the observed failure, code inspection, implementation decision, and recheck.

The [curated, redacted evidence log](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/evidence-log.md) also records a chart-update failure and correction, selected prompt excerpts, resulting files, tests, browser observations, and remaining uncertainty. It is not a complete chat export.

## Remaining limitations

- **Regular-hours live equity volume evidence remains pending.** The actual overnight AAPL/MSFT messages used for verification omitted cumulative volume. The application correctly displays unknown volume. Calculated volume and the histogram were verified with constructed data; that does not establish live equity volume. BTC's rolling 24-hour total is not candle volume.
- Native date-range entry in the browser still needs a manual check. Backend empty selections and receipt-range filtering passed, but the browser automation tool could not complete the date/time-input operation, so that UI action is not claimed as verified.
- Yahoo quotes are sampled observations with instrument-dependent availability and timing, not a complete exchange trade tape. Gaps remain gaps; daily buckets use UTC rather than an exchange-session calendar. Source and local clocks can differ slightly.
- Historical projection favors a readable classroom implementation over unlimited retention or many concurrent users. A completed interval can still receive late data or corrections.

## Tool and model disclosure

[AI-USE.md](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/AI-USE.md) discloses Codex's role in implementation, testing, debugging, documentation, publication, and video preparation. The student confirmed that no other coding agents, editors, or AI models were used. The exact model variant was not recorded; no model switch is claimed. The disclosure distinguishes the coding agent from the application itself, which has no AI decision or trading model in Part 4.1.

The repository and video are public links. Only this **report.md** should be uploaded to Canvas for Part 4.1; source files and ZIP archives belong in the linked repository.
