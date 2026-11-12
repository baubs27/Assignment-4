# Data flow and design decisions

```text
Yahoo Finance WebSocket
    | yfinance.AsyncWebSocket; one subscription for AAPL / MSFT / BTC-USD
    v
backend/feed.py: validate source time (epoch ms -> seconds), price and volume
    |
    v
backend/store.py: immutable observations + append-only receipt records
    |                         |
    | live view               | frozen replay selection, cursor in receipt order
    +------------+------------+
                 v
       project(): deduplicate, resolve explicit revision identities known so far
                 v
       backend/candles.py: source-time ordering -> UTC OHLCV + completion
                 v
       backend/main.py /ws/market: snapshot + source/receipt time + upstream status
                 v
       frontend/src/App.vue: price candles, volume histogram, inspector and ledger
```

All blocks above exist. Later-part strategy, simulation, backtesting, image interpretation, model, and audio services do not yet exist.

## Responsibilities

| File | Responsibility |
| --- | --- |
| backend/feed.py | Yahoo lifecycle/retry, provider payload validation, timestamp conversion, dataset selection |
| backend/store.py | Schema, immutable normalized payload identity, receipts, selection, revision projection |
| backend/candles.py | Shared live/replay candle aggregation and volume semantics |
| backend/demo.py | Atomic deterministic fixture initialization, isolated dataset |
| backend/main.py | Local HTTP routes, replay commands, heartbeat snapshots, static Vue delivery |
| frontend/src/App.vue | UI controls, WebSocket lifecycle/recovery, chart synchronization, provenance |
| frontend/src/style.css | Responsive dark workstation layout, focus and reduced-motion handling |

Vue keeps presentation and interaction on the client. FastAPI owns provider connections and derived data. SQLite provides inspectable local durability without a separate database service. Lightweight Charts supports financial candles, corresponding histogram panes, crosshairs, zoom, and incremental latest-bar updates. Historical changes use a series rebuild so late ticks and moving corrections can safely alter previous candles. No model service receives any data in this part.

## SQLite schema and identity

`observations`: integer `id`; `dataset`; `source`; `symbol`; `source_time` (Unix seconds UTC); `price`; nullable `cumulative_volume`; `volume_kind` (session/rolling); nullable `event_key` and `revision`; canonical `raw_json`; unique SHA-256 `fingerprint` of normalized fields plus original payload. Source, dataset, and symbol are part of identity. Unique `(dataset, source, symbol, event_key, revision)` prevents conflicting values for one explicitly identified version. NULL identities allow unrelated same-time Yahoo observations. A conflict is rejected and counted by the adapter; the accepted earlier version is not silently overwritten.

`receipts`: integer monotonic `id`; foreign-key `observation_id`; `receipt_time` (backend wall-clock Unix seconds); `duplicate` flag. Each accepted delivery gets a receipt, including repeats. Insertion ID, rather than clock ordering, preserves arrival order if the computer clock moves. Source time is retained independently. Raw JSON remains queryable for provenance. Wall-clock receipt time is not an exchange event time.

An exact repeat links to the same observation. No same-timestamp price change is assumed to be a correction. Where an explicit producer event identity and revision exist, the highest revision **seen by the replay cursor** supplies the effective value. Later delivery of an older revision cannot undo it. Tied source timestamps use original observation ID as a deterministic tie-breaker because true exchange sequencing is unavailable. Every stored version remains inspectable.

Example inspection (run using the project interpreter and PYTHONPATH configured by scripts/common.ps1):

```python
import sqlite3
with sqlite3.connect('data/market.sqlite3') as db:
    for row in db.execute('''
        SELECT o.id, r.id, o.symbol, o.source_time, r.receipt_time,
               o.price, o.cumulative_volume, r.duplicate, o.raw_json
        FROM receipts r JOIN observations o ON o.id = r.observation_id
        WHERE o.dataset = 'live' AND o.symbol = 'AAPL' ORDER BY r.id
    '''):
        print(row)
```

Database creation is automatic. SQLite connections commit on success, roll back on errors, and close explicitly. Demo initialization is one transaction. Schema versioning would be needed before a future incompatible migration; no destructive migration currently runs.

## Candle rules

Buckets: `floor(source_time / interval_seconds) * interval_seconds`; intervals 60, 300, 900, 3600, and 86400 seconds. Daily buckets are UTC calendar days, not exchange-session OHLC candles. Only captured observations contribute; gaps are not forward-filled.

Within each bucket, the first source-time observation is open and the last is close; max/min form high/low. Duplicates do not add a price or volume contribution. A late arrival reorders source events and can change historical OHLCV. Identifiable revisions replace the previous effective observation, then all affected candles are recomputed. Completion is separate from OHLCV: bucket end <= current backend clock in live mode, or last receipt time at the replay cursor. Complete means the interval ended; it does not promise no future revisions.

Volume differences use the immediately preceding effective source observation, including one from the prior bucket, if both totals are known session values on the same New York trading date and the current total did not decrease. Unknown baseline, missing values, resets, date boundaries, and crypto rolling totals produce `volume: null`, never a fabricated zero. If any contribution within a bucket is unknown, the entire bucket volume is unknown. The method attributes increments to the later tick's bucket; sparse ticks can straddle intervals and limit precision. It is not exchange-certified trade volume.

Course example: baseline at 14:59:59 price 99 total 1000; 15:00:05 price 100 total 1004; 15:00:20 price 103 total 1009; 15:00:50 price 101 total 1011. The 15:00 candle is O100 H103 L100 C101 V11. It is forming at 15:00:55 and complete at 15:01:00, including when the 15:00:20 tick arrives last.

## Transport and replay

HTTP: GET /api/health, /api/sessions, /api/feed; POST /api/feed/connect or /disconnect. WebSocket /ws/market takes symbol, interval, dataset, mode, and optional receipt-time start/end. Replay commands: play, pause, step, reset, seek(cursor), speed(batch). Invalid selections close with code 1008. Blank/empty selections return an explicit empty snapshot.

Live snapshots are rebuilt at most once per second per browser connection; playback advances a selectable batch every 0.5 seconds. Snapshots carry canonical observations and the last 12 receipts for inspection. Replay freezes the selected receipt list, preserves receipt ID order, and never writes data. Range boundaries apply to receipt time; a cropped range may lose the volume baseline. The latest price is chosen by source time; receipt time may belong to a late delivery. The UI shows both.

The browser retries its backend connection after 3 seconds and labels lost connectivity. Yahoo reconnects independently with 2-60 second backoff and a bounded 300 second listener lifetime. Source age is measured independently; >60 seconds is stale. An open connection alone is not evidence of fresh data. Some upstream failures can be reflected first by staleness before the listener timeout reports a reconnect. Explicit Disconnect sets an enable flag before cancellation because yfinance catches CancelledError internally; a regression test verifies it cannot restart afterward.

## Local service boundaries and scale

Bind to 127.0.0.1 only. API control routes intentionally have no public authentication; do not expose this teaching server to a network. The only required external request is the Yahoo subscription (public symbols, no credentials); optional Google Fonts is cosmetic. No private files or accounts are sent to Yahoo. No order execution exists.

The implementation favors an inspectable student project: full selected-record projection per snapshot is suitable for short classroom captures, not unlimited retention or many clients. A production design would add retention, incremental aggregates, bounded history, provider sequence guarantees, exchange session calendars, and migrations. Those limits do not justify silently dropping receipts here.
