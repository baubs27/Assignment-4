# Curated evidence log - Part 4.1

This is a selected process record, not a full chat export. Entries connect the intended change, a short instruction excerpt, the resulting code/document, an observed check, the decision, and remaining uncertainty. Credentials, personal account information, absolute user paths, and private third-party content are omitted. The implementation baseline is [6c00865](https://github.com/baubs27/Assignment-4/commit/6c00865acc400e9988ff0c6cc9a3539d02866226).

## 1. Make the live source traceable

- **Intent / instruction excerpt:** "Make the data source, age, and feed status visible."
- **Result:** [backend/feed.py](../backend/feed.py) validates Yahoo messages and converts source milliseconds to Unix seconds; [backend/store.py](../backend/store.py) stores raw payloads and receipts; [frontend/src/App.vue](../frontend/src/App.vue) shows source age, provider state, backend connectivity, and the ledger.
- **Evidence:** Actual AAPL observation 278 / receipt 279 had price 355.55 and source time 02:27:23 UTC on November 12, 2026. A later tick at 02:27:34 had price 355.52. The browser and independent SQLite calculation agreed on O355.55 H355.55 L355.52 C355.52. [Machine-readable real-capture evidence](live-capture-evidence.json).
- **Decision:** Keep source time and receipt time separate; an open browser socket cannot establish source freshness. Small clock differences are retained, with displayed age clamped at zero.
- **Uncertainty:** Overnight equity messages omitted cumulative volume; these observations prove live prices, not known live equity candle volume.

## 2. Preserve duplicate, revised, and late observations

- **Intent / instruction excerpt:** "Explain and test how duplicate, revised, and out-of-order observations are handled."
- **Result:** Immutable observation versions and append-only receipts in [backend/store.py](../backend/store.py); shared source-time aggregation in [backend/candles.py](../backend/candles.py); [tests/test_pipeline.py](../tests/test_pipeline.py).
- **Evidence:** Sending an exact repeat retained a separate receipt while reusing its observation ID. A changed same-time Yahoo-like payload remained a separate observation. Explicit revision 1 superseded revision 0 only after it was received. A late middle tick still produced the course example O100 H103 L100 C101 V11; the bar changed from forming to complete at the interval boundary.
- **Decision:** Do not infer correction identity merely from equal timestamps. Resolve only explicit producer identities/revisions known at the replay cursor; retain every stored version.
- **Uncertainty:** Yahoo's tested message format does not provide reliable revision identities, so explicit correction behavior is verified with constructed inputs rather than claimed as a provider feature.

## 3. Failed approach: historical updates for newly added candles

- **Intent / instruction excerpt:** "use a charting library to display updating candlesticks and corresponding volume."
- **Failed generated approach:** `candles.update(priceRows[i], true)` was used while appending a new point. The true argument requested a historical update, although that timestamp did not yet exist in the chart.
- **Observed failure:** Browser console: `Cannot update non-existing data point when historicalUpdate is true`. The dashboard ledger could advance while chart synchronization failed.
- **Resulting code:** [frontend/src/App.vue](../frontend/src/App.vue), draw(): normal `candles.update(priceRows[i])` and `volume.update(volumeRows[i])` for latest/new data; setData rebuild when earlier timestamps/values change or a replay moves backward.
- **Decision / recheck:** Distinguish appending/latest updates from actual historical replacement. Replayed demo data to 276 receipts and real Yahoo data to the selected end; no new chart errors occurred after the corrected reload. [Demo verification screenshot](dashboard-demo.png).
- **Uncertainty:** Full selected-history rebuilds favor clarity over unlimited-session performance.

## 4. Failed approach: relying on cancellation to stop Yahoo

- **Intent / instruction excerpt:** "including an unavailable-feed condition."
- **Failed generated approach:** Cancel the Yahoo listener and assume that cancellation always propagates to stop the adapter. Inspection showed that yfinance could catch CancelledError and return; the adapter could then enter its retry path.
- **Observed failure:** After the first Disconnect request, a subsequent status check still reported connected with a newer connection time.
- **Resulting generated code:** [backend/feed.py](../backend/feed.py):

```python
while self.enabled:
    # connect, subscribe, and listen
    ...
    await asyncio.wait_for(ws.listen(receive), timeout=300)
    if not self.enabled:
        return

# stop() sets the flag before cancelling the task:
self.enabled = False
```

- **Decision / recheck:** Make the desired lifecycle state explicit rather than relying only on cancellation behavior. [tests/test_feed.py](../tests/test_feed.py) uses a stub that deliberately swallows cancellation; stopping must leave no task and no reconnect. The actual UI then showed Yahoo disconnected while the backend WebSocket remained connected. [Disconnection screenshot](feed-disconnected.png).
- **Uncertainty:** Some natural upstream failures may first appear as stale source data before the bounded listener reconnects. Intentional disconnect was verified; every possible provider failure was not simulated.

## 5. Verify replay without changing the recording

- **Intent / instruction excerpt:** "Store market observations in SQLite so that they can be retrieved and replayed."
- **Result:** Frozen receipt selection and cursor commands in [backend/main.py](../backend/main.py); independent check in [scripts/verify_recording.py](../scripts/verify_recording.py).
- **Evidence:** Each real captured symbol's replay OHLC matched an independent SQLite grouping. Resetting/replaying again produced identical candles and left session counts unchanged. An isolated backup of real captured observations was then served offline, restarted, and checked again: [before restart](offline-copy-evidence.json) and [after restart](restart-evidence.json) matched.
- **Decision:** Replay in original receipt ID order while aggregating prices in source-time order; use only observations available at the cursor. Keep replay read-only.
- **Uncertainty:** A cropped receipt range can lose the cumulative-volume baseline. The last recorded bar can correctly remain forming at the last receipt's historical clock.

## 6. Verify the public source from a clean checkout

- **Intent / instruction excerpt:** "linked in report.md and verified from a clean checkout."
- **Result:** Fresh clone of the published source commit; dependency installation from committed locks; separate fresh SQLite database and offline server.
- **Evidence:** Nine tests passed in 3.36 seconds; production build passed; dashboard and health returned HTTP 200; offline feed stayed disconnected; demo initialization was 276 receipts / 275 observations. [Clean-checkout record](clean-checkout-verification.md).
- **Decision:** Do not rely on an existing node_modules directory, the original recordings, or an already-built frontend as proof of reproducibility.
- **Uncertainty:** Installation still requires a suitable Python/Node environment and package-network access. The Starlette/httpx test adapter emits one deprecation warning.

## 7. Prepare one compliant-length combined video

- **Intent / instruction excerpt:** "one combined video lasting 30 seconds to 1 minute" and "briefly identify one design or verification decision."
- **Input / action:** Student supplied a 65.1333-second screen recording and explicitly authorized public GitHub publication. Codex used FFmpeg to create [part4-1-demo.mp4](part4-1-demo.mp4): 44 seconds from the live recording, six seconds of the demo verification screenshot, and six seconds of the disconnection verification screenshot. On-screen captions explain source freshness versus browser connectivity. Still-image sections are labeled.
- **Verification:** Output duration 56.00 seconds; H.264 MP4; 1600 x 940; 15 fps; complete decode succeeded. Original audio measured approximately -91 dB, so the published derivative is silent and captioned. Source recording is preserved locally. Selected output frames were inspected before publication.
- **Decision:** Meet the time limit without representing demo data as live or verification stills as continuous live interaction. Include the process explanation in this log and report; no separate process video is claimed.
- **Uncertainty:** The video and repository must remain accessible to the instructor. Live equity volume is still not established by this overnight recording; the report states that limitation.

## Tool disclosure

See [AI-USE.md](../AI-USE.md) for the coding agent/model disclosure, the student's confirmation that no other AI tools were used, and the role of video preparation. Supporting prompts are selected excerpts above; no complete chat export is needed for this log.
