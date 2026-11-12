# Tool and model disclosure - Assignment 4, Part 4.1

## AI tool, editor, and model

The AI coding tool used was **OpenAI Codex in the Codex desktop app**, a GPT-6-based coding agent. The exact model variant/selector label was not recorded in the retained project evidence; this disclosure does not guess a more specific model name. The student confirmed that no other coding agents, editors, or AI models were used for this assignment. No model switch is documented during the work.

Codex read the supplied assignment and starter prompts, proposed the local architecture, generated and edited the Vue/FastAPI/SQLite application, wrote tests and documentation, inspected failures, corrected code, ran the app, operated the browser for verification, and uploaded the authorized project to GitHub. Codex also drafted report.md, this disclosure, and the curated evidence log from retained project evidence. The student supplied the requirements, requested and tested the app, supplied the screen recording, confirmed the tool disclosure, and authorized publication of the recording and supporting documents.

The generated code and prose are AI-assisted work. Test results establish the checks described in the evidence, not that every possible behavior is correct. No independent student review of every generated line is claimed by this disclosure.

## Supporting tools and changes in approach

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

## Video and evidence preparation

The student's original recording was 65.1333 seconds, exceeding the one-minute limit. Its audio track measured approximately -91 dB and contained no useful narration. The published derivative contains the first 44 seconds of that recording, followed by two six-second verification screenshots from the actual project. The screenshots are visibly labeled as verification screenshots; the demo screen is explicitly labeled as constructed data. Captions identify the design decision to distinguish browser connectivity from market-source freshness/status. The output is a silent, captioned 56-second MP4, not a claim that the still images are continuous live footage. The original recording is preserved outside the repository.

No generative image/video model was used. No AI decision service, chart-image model, live-audio model, or autonomous trading model is implemented in Part 4.1. The curated [evidence log](docs/evidence-log.md) records selected prompts, code, observed checks, decisions, and limitations without exporting the full chat. Credentials, student account details, local absolute user paths, and private third-party messages are omitted from that log.
