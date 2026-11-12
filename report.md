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

## Startup, data flow, and SQLite schema

The app runs locally at `http://127.0.0.1:8000`. With Python 3.12+ and a compatible Node.js/npm environment, the project provides these PowerShell commands from the repository root:

```powershell
# Restore locked project-local dependencies and build the Vue frontend.
.\scripts\install.ps1

# Start the app with the Yahoo connection enabled.
.\scripts\start.ps1

# Alternatively, start with Yahoo disconnected for offline replay.
.\scripts\start.ps1 -Offline

# Run isolated backend/API checks without the live provider.
.\scripts\test.ps1
```

`MARKET_PYTHON` can select an existing Python executable. The scripts install packages under the project rather than requiring a global package install. SQLite initializes automatically at `data/market.sqlite3`; `MARKET_DB` selects another file. Initialization enables foreign keys and write-ahead logging and loads the demo fixture atomically. Restarting does not erase saved Yahoo records. No database credentials or Yahoo login are required. Dependencies, local databases, caches, and generated builds are excluded from Git.

The implemented data path is:

```text
Yahoo WebSocket -> yfinance adapter -> SQLite observations + receipt records
    -> effective observations known so far -> source-time candle aggregation
    -> FastAPI /ws/market -> Vue -> price candles, volume pane, and ledger

SQLite recorded receipts -> frozen replay selection -> receipt-order cursor
    -> the same effective-observation projection and candle aggregation
    -> FastAPI /ws/market -> Vue replay view
```

| SQLite table | Preserved fields and purpose |
| --- | --- |
| `observations` | Immutable `id`, dataset/source/symbol, `source_time`, price, nullable cumulative volume and volume kind, optional `event_key` and `revision`, original `raw_json`, and unique payload fingerprint |
| `receipts` | Monotonic receipt `id`, observation foreign key, backend `receipt_time`, and duplicate flag; every accepted delivery gets a receipt, including exact repeats |

Fingerprint identity includes the dataset, source, symbol, normalized values, and raw payload. A unique explicit event/revision key rejects conflicting values for the same identified version. Yahoo messages without such keys can remain distinct even at equal timestamps. Effective projection removes exact repeats and selects the highest explicit revision available at the cursor. Earlier stored versions are retained. Price ordering uses source time with original observation ID as a deterministic tie-breaker; replay ordering uses receipt ID so local wall-clock adjustments do not change arrival order.

Candles use UTC interval buckets. Completion is derived separately using the selected live or replay clock. A complete interval can still be revised by a late observation. Replay is read-only and freezes the selected receipt list. If the user crops the receipt range, any lost volume baseline is treated as unknown. Browser and provider connection states are independent, and a source-observation age over 60 seconds is labeled stale.

## Verification results

The public repository was cloned into a clean verification directory. Dependencies were installed from its committed lockfiles rather than copied from the original working environment. The complete clean-checkout procedure and observations are included below.

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

## Clean-checkout verification - full record

### Version and isolation

Repository: https://github.com/baubs27/Assignment-4

Application source commit: `6c00865acc400e9988ff0c6cc9a3539d02866226`.

A fresh clone of the GitHub main branch was created in an ignored verification directory, outside the working source tree's tracked files. Git status was clean and HEAD matched the source commit above. Python and frontend dependencies were installed from the committed lockfiles into this clone. No original workstation database or generated frontend build was copied into it. The available Python interpreter was selected with MARKET_PYTHON; installed application packages belonged to the clone's own .runtime/python.

### Commands and observed results

| Check | Observed result |
| --- | --- |
| git clone --no-hardlinks --branch main URL verification-directory | Clone succeeded; HEAD was 6c00865; tracked working tree clean |
| Python pip install --target .runtime/python -r backend/requirements-lock.txt | Locked dependencies installed successfully |
| In frontend: npm ci | 37 packages installed; installation audit reported zero vulnerabilities at that time |
| In frontend: npm run build | Passed; Vite 7.3.8; 16 modules; 254.51 kB JavaScript before gzip; 2.99 seconds |
| scripts/test.ps1 | **9 passed in 3.36 seconds**, one third-party Starlette/httpx deprecation warning |
| scripts/start.ps1 -Offline -Port 8002 with a fresh MARKET_DB | FastAPI started; built Vue files served; SQLite initialized automatically |
| GET /api/health on the isolated server | HTTP 200; status ok; service market-workstation; storage SQLite |
| GET / on the isolated server | HTTP 200; Market Desk page title present |
| GET /api/feed | disconnected, as required for offline startup |
| GET /api/sessions | Demo initialized with 276 receipts and 275 unique observations |
| Final git status --porcelain | No tracked or untracked non-ignored changes |

The isolated server was stopped afterward. The user's primary testing app and its recordings were not altered. Existing browser and real-Yahoo observations are recorded separately in [verification.md](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/verification.md); this clean-checkout run did not pretend to perform a new live-volume capture.

### Scope of the result

The source, lockfiles, tests, build, startup, static dashboard delivery, and fresh database initialization were verified from the GitHub checkout. The later submission-support commit adds documentation and the derived video without changing application source, dependency locks, or tests. Its application paths are compared to the verified source commit before publication. Existing limitations remain: regular-hours equity volume still needs provider evidence, native date-range UI entry still needs a manual check, and provider timing/availability are not guaranteed.

## Curated, redacted evidence log

This is a selected process record, not a full chat export. Entries connect the intended change, a short instruction excerpt, the resulting code/document, an observed check, the decision, and remaining uncertainty. Credentials, personal account information, absolute user paths, and private third-party content are omitted. The implementation baseline is [6c00865](https://github.com/baubs27/Assignment-4/commit/6c00865acc400e9988ff0c6cc9a3539d02866226).

### 1. Make the live source traceable

- **Intent / instruction excerpt:** "Make the data source, age, and feed status visible."
- **Result:** [backend/feed.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/backend/feed.py) validates Yahoo messages and converts source milliseconds to Unix seconds; [backend/store.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/backend/store.py) stores raw payloads and receipts; [frontend/src/App.vue](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/frontend/src/App.vue) shows source age, provider state, backend connectivity, and the ledger.
- **Evidence:** Actual AAPL observation 278 / receipt 279 had price 355.55 and source time 02:27:23 UTC on November 12, 2026. A later tick at 02:27:34 had price 355.52. The browser and independent SQLite calculation agreed on O355.55 H355.55 L355.52 C355.52. [Machine-readable real-capture evidence](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/live-capture-evidence.json).
- **Decision:** Keep source time and receipt time separate; an open browser socket cannot establish source freshness. Small clock differences are retained, with displayed age clamped at zero.
- **Uncertainty:** Overnight equity messages omitted cumulative volume; these observations prove live prices, not known live equity candle volume.

### 2. Preserve duplicate, revised, and late observations

- **Intent / instruction excerpt:** "Explain and test how duplicate, revised, and out-of-order observations are handled."
- **Result:** Immutable observation versions and append-only receipts in [backend/store.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/backend/store.py); shared source-time aggregation in [backend/candles.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/backend/candles.py); [tests/test_pipeline.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/tests/test_pipeline.py).
- **Evidence:** Sending an exact repeat retained a separate receipt while reusing its observation ID. A changed same-time Yahoo-like payload remained a separate observation. Explicit revision 1 superseded revision 0 only after it was received. A late middle tick still produced the course example O100 H103 L100 C101 V11; the bar changed from forming to complete at the interval boundary.
- **Decision:** Do not infer correction identity merely from equal timestamps. Resolve only explicit producer identities/revisions known at the replay cursor; retain every stored version.
- **Uncertainty:** Yahoo's tested message format does not provide reliable revision identities, so explicit correction behavior is verified with constructed inputs rather than claimed as a provider feature.

### 3. Failed approach: historical updates for newly added candles

- **Intent / instruction excerpt:** "use a charting library to display updating candlesticks and corresponding volume."
- **Failed generated approach:** `candles.update(priceRows[i], true)` was used while appending a new point. The true argument requested a historical update, although that timestamp did not yet exist in the chart.
- **Observed failure:** Browser console: `Cannot update non-existing data point when historicalUpdate is true`. The dashboard ledger could advance while chart synchronization failed.
- **Resulting code:** [frontend/src/App.vue](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/frontend/src/App.vue), draw(): normal `candles.update(priceRows[i])` and `volume.update(volumeRows[i])` for latest/new data; setData rebuild when earlier timestamps/values change or a replay moves backward.
- **Decision / recheck:** Distinguish appending/latest updates from actual historical replacement. Replayed demo data to 276 receipts and real Yahoo data to the selected end; no new chart errors occurred after the corrected reload. [Demo verification screenshot](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/dashboard-demo.png).
- **Uncertainty:** Full selected-history rebuilds favor clarity over unlimited-session performance.

### 4. Failed approach: relying on cancellation to stop Yahoo

- **Intent / instruction excerpt:** "including an unavailable-feed condition."
- **Failed generated approach:** Cancel the Yahoo listener and assume that cancellation always propagates to stop the adapter. Inspection showed that yfinance could catch CancelledError and return; the adapter could then enter its retry path.
- **Observed failure:** After the first Disconnect request, a subsequent status check still reported connected with a newer connection time.
- **Resulting generated code:** [backend/feed.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/backend/feed.py):

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

- **Decision / recheck:** Make the desired lifecycle state explicit rather than relying only on cancellation behavior. [tests/test_feed.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/tests/test_feed.py) uses a stub that deliberately swallows cancellation; stopping must leave no task and no reconnect. The actual UI then showed Yahoo disconnected while the backend WebSocket remained connected. [Disconnection screenshot](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/feed-disconnected.png).
- **Uncertainty:** Some natural upstream failures may first appear as stale source data before the bounded listener reconnects. Intentional disconnect was verified; every possible provider failure was not simulated.

### 5. Verify replay without changing the recording

- **Intent / instruction excerpt:** "Store market observations in SQLite so that they can be retrieved and replayed."
- **Result:** Frozen receipt selection and cursor commands in [backend/main.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/backend/main.py); independent check in [scripts/verify_recording.py](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/scripts/verify_recording.py).
- **Evidence:** Each real captured symbol's replay OHLC matched an independent SQLite grouping. Resetting/replaying again produced identical candles and left session counts unchanged. An isolated backup of real captured observations was then served offline, restarted, and checked again: [before restart](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/offline-copy-evidence.json) and [after restart](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/restart-evidence.json) matched.
- **Decision:** Replay in original receipt ID order while aggregating prices in source-time order; use only observations available at the cursor. Keep replay read-only.
- **Uncertainty:** A cropped receipt range can lose the cumulative-volume baseline. The last recorded bar can correctly remain forming at the last receipt's historical clock.

### 6. Verify the public source from a clean checkout

- **Intent / instruction excerpt:** "linked in report.md and verified from a clean checkout."
- **Result:** Fresh clone of the published source commit; dependency installation from committed locks; separate fresh SQLite database and offline server.
- **Evidence:** Nine tests passed in 3.36 seconds; production build passed; dashboard and health returned HTTP 200; offline feed stayed disconnected; demo initialization was 276 receipts / 275 observations. [Clean-checkout record](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/clean-checkout-verification.md).
- **Decision:** Do not rely on an existing node_modules directory, the original recordings, or an already-built frontend as proof of reproducibility.
- **Uncertainty:** Installation still requires a suitable Python/Node environment and package-network access. The Starlette/httpx test adapter emits one deprecation warning.

### 7. Prepare one compliant-length combined video

- **Intent / instruction excerpt:** "one combined video lasting 30 seconds to 1 minute" and "briefly identify one design or verification decision."
- **Input / action:** Student supplied a 65.1333-second screen recording and explicitly authorized public GitHub publication. Codex used FFmpeg to create [part4-1-demo.mp4](https://github.com/baubs27/Assignment-4/blob/a4883cad6189f976b4a4daf57f2172f916488423/docs/part4-1-demo.mp4): 44 seconds from the live recording, six seconds of the demo verification screenshot, and six seconds of the disconnection verification screenshot. On-screen captions explain source freshness versus browser connectivity. Still-image sections are labeled.
- **Verification:** Output duration 56.00 seconds; H.264 MP4; 1600 x 940; 15 fps; complete decode succeeded. Original audio measured approximately -91 dB, so the published derivative is silent and captioned. Source recording is preserved locally. Selected output frames were inspected before publication.
- **Decision:** Meet the time limit without representing demo data as live or verification stills as continuous live interaction. Include the process explanation in this log and report; no separate process video is claimed.
- **Uncertainty:** The video and repository must remain accessible to the instructor. Live equity volume is still not established by this overnight recording; the report states that limitation.

## Tool and model disclosure (AI-USE)

### AI tool, editor, and model

The AI coding tool used was **OpenAI Codex in the Codex desktop app**, a GPT-6-based coding agent. The exact model variant/selector label was not recorded in the retained project evidence; this disclosure does not guess a more specific model name. The student confirmed that no other coding agents, editors, or AI models were used for this assignment. No model switch is documented during the work.

Codex read the supplied assignment and starter prompts, proposed the local architecture, generated and edited the Vue/FastAPI/SQLite application, wrote tests and documentation, inspected failures, corrected code, ran the app, operated the browser for verification, and uploaded the authorized project to GitHub. Codex also drafted report.md, this disclosure, and the curated evidence log from retained project evidence. The student supplied the requirements, requested and tested the app, supplied the screen recording, confirmed the tool disclosure, and authorized publication of the recording and supporting documents.

The generated code and prose are AI-assisted work. Test results establish the checks described in the evidence, not that every possible behavior is correct. No independent student review of every generated line is claimed by this disclosure.

### Supporting tools and changes in approach

| Tool | Use |
| --- | --- |
| Codex workspace editor and PowerShell | Create/edit source and Markdown; inspect files; run the project commands |
| Git and GitHub connector | Inspect the repository, commit and push authorized files, verify the published commit |
| Python 3.12, FastAPI, sqlite3, yfinance | Implement the backend, immutable observation store, receipts, Yahoo connection, and candle calculation |
| Node.js/npm, Vue, Vite, Lightweight Charts | Build the browser dashboard and price/volume chart |
| pytest and FastAPI TestClient | Verify data semantics, replay transport, database behavior, and the feed cancellation regression |
| Browser automation and screenshots | Exercise real UI operations, inspect console failures, and preserve selected verification screenshots |
| FFmpeg 9.0.2 via project-local imageio-ffmpeg 0.8.1 | Inspect the supplied screen recording, shorten/re-encode it, add captions, and assemble the single 56-second submission video |

The computer's Windows Python alias did not run, so the agent reused the available bundled Python with project-local dependencies. The Yahoo client could swallow cancellation, so an explicit enable flag and a regression test replaced reliance on cancellation alone. The chart library rejected an inappropriate historical-update call, so latest/new candle updates and historical rebuilds were separated. These were implementation and tool-use changes; they were not changes of AI model.

### Video and evidence preparation

The student's original recording was 65.1333 seconds, exceeding the one-minute limit. Its audio track measured approximately -91 dB and contained no useful narration. The published derivative contains the first 44 seconds of that recording, followed by two six-second verification screenshots from the actual project. The screenshots are visibly labeled as verification screenshots; the demo screen is explicitly labeled as constructed data. Captions identify the design decision to distinguish browser connectivity from market-source freshness/status. The output is a silent, captioned 56-second MP4, not a claim that the still images are continuous live footage. The original recording is preserved outside the repository.

No generative image/video model was used. No AI decision service, chart-image model, live-audio model, or autonomous trading model is implemented in Part 4.1. The curated evidence log in this report records selected prompts, code, observed checks, decisions, and limitations without exporting the full chat. Credentials, student account details, local absolute user paths, and private third-party messages are omitted from that log.

## Remaining limitations

- **Regular-hours live equity volume evidence remains pending.** The actual overnight AAPL/MSFT messages used for verification omitted cumulative volume. The application correctly displays unknown volume. Calculated volume and the histogram were verified with constructed data; that does not establish live equity volume. BTC's rolling 24-hour total is not candle volume.
- Native date-range entry in the browser still needs a manual check. Backend empty selections and receipt-range filtering passed, but the browser automation tool could not complete the date/time-input operation, so that UI action is not claimed as verified.
- Yahoo quotes are sampled observations with instrument-dependent availability and timing, not a complete exchange trade tape. Gaps remain gaps; daily buckets use UTC rather than an exchange-session calendar. Source and local clocks can differ slightly.
- Historical projection favors a readable classroom implementation over unlimited retention or many concurrent users. A completed interval can still receive late data or corrections.

## Canvas submission

This report includes the completed-work summary, design decisions, startup and schema explanation, verification results, clean-checkout record, curated evidence log with failed approaches and generated-code excerpts, tool/model disclosure, remaining limitations, GitHub version, and accessible video links in one document. Supporting repository links provide the source artifacts and machine-readable evidence.

The public video link was checked without sign-in and returned HTTP 200. The repository is public. Upload **only this report.md** to Canvas for Part 4.1; do not upload source-code files or ZIP archives. The linked video is 56 seconds long and includes a brief design/process explanation. No Canvas submission was performed by the coding agent.
