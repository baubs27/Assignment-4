# Part 4.1 review and submission preparation

- Inspect frontend/src/App.vue, backend/feed.py, backend/store.py, and backend/candles.py. Be able to explain both WebSocket connections and why source time differs from receipt time.
- Run the backend tests and reproduce the browser checks. Explain the demo's known final values and the course candle volume example.
- Capture a regular-hours equity session with usable cumulative volume. Overnight Yahoo streaming was received, but actual AAPL/MSFT volume fields were absent during this session. Do not present demo volume as live-volume evidence.
- Review docs/verification.md and the screenshots, then capture your own demonstration of live quotes, a stored record, a candle, upstream disconnect, and replay after restart.
- Explain why equal timestamps do not prove a revision, why complete candles can still change after late data, and why crypto rolling volume cannot become a minute's traded volume.
- Review the diff before making a Git commit. Add your own GitHub remote and push only when ready. Runtime dependencies, local recordings, and credentials must stay out of source history.
- Submit the required Canvas evidence yourself. No Canvas or GitHub action has been performed by this implementation session.
- Later parts require additional specifications and implementation. Part 4.1 provides persistence and replay; replay alone is not a backtest, and no strategy performance is claimed.
