# Repeatable browser check for Part 4.1

Start `.\scripts\start.ps1 -Offline`, then open http://127.0.0.1:8000. Backend tests are `.\scripts\test.ps1`; the following UI steps use the real Vue frontend and FastAPI WebSocket, not mocked DOM state.

1. Select Demo replay. It must say CONSTRUCTED TEACHING DATA, Replay paused, 0 / 276 receipts, and Your recording is ready. Select 50 receipts/tick and Play. At the end expect 276 / 276, 275 unique observations, one exact repeat, 92 one-minute bars, last price 102.50, last volume 100, and revision 0/1 in the ledger. The last bar remains forming at replay clock 16:31:10 UTC on Nov 9, 2026.
2. Reset and Step. Expect one receipt, one candle, and unknown first-bar volume. Play again: the same final values should return. Saved demo counts in GET /api/sessions must not change.
3. Try 5m and 1d, replay again, and inspect the resulting bars. Changing timeframe resets replay. Reset then use the replay slider to seek to the end; the final price remains 102.50. Pan/zoom and Fit chart should work.
4. Load a receipt range after the demo session, such as Nov 10 2026 00:00:00-01:00:00 UTC. Expect No recorded observations and disabled Play. Clear the inputs and reload to recover.
5. Inspect at desktop and narrow widths. The page must not scroll horizontally; the ledger alone can scroll within its container. The narrow-screen instrument selector must be available. Check console errors after playback; none should arise from chart updates.
6. Select Yahoo live and Connect Yahoo. Allow a bounded observation window (for example 60 seconds), then record whether the connection opened and whether each instrument produced data. Never describe subscription success alone as quote receipt. Trace an actual ledger row to SQLite and compare its source time, receipt time, and price with the last appropriate candle. Inspect any omitted volume fields.
7. Disconnect Yahoo while staying on Yahoo live. Expect Feed disconnected and upstream disconnected, while Backend WebSocket connected remains visible. Candles and recordings remain. Watch for longer than a reconnect-backoff interval to confirm it stays off. Reconnect to check recovery.
8. With Yahoo disconnected, choose Saved Yahoo, select the captured instrument/range, and replay to the end twice. Compare OHLCV against a direct SQLite aggregation; stored session counts must remain unchanged. Restart the server offline and repeat to prove persistence.
9. For frontend development, start `cd frontend; npm run dev` in a second terminal. Compare GET /api/health directly at :8000 and through Vite at :5173. Stop the backend: the proxied request must fail, and the browser must show offline. Restart offline and verify recovery. Stop the Vite process when done.

Record actual results, dates, screenshots, unresolved checks, and any corrections in verification.md. UI checks are separate from the automated backend command; no automated browser-runner package is installed.
