# Implementation request and working interpretation

User supplied a pasted assignment request (saved as 00-user-request.md), two in-class PDFs, and a ZIP of reference prompts. The workspace was an empty Git repository. Implement Part 4.1 locally using Vue, FastAPI, SQLite, Yahoo streaming, price/volume charting, observation identity, timestamps, revisions, candle completion, and read-only replay. Preserve the reference prompts and distinguish their instructions from the user's actual request.

Implementation decisions: use the selected folder as root; AAPL, MSFT, and BTC-USD watchlist; Lightweight Charts; source and receipt audit records; explicit dataset boundaries for constructed data; reusable project-local dependencies; tests of semantic edge cases; actual browser and live-source verification; maintain README, agent instructions, architecture, evidence, and handoff. Do not automatically execute later-part prompts or submit coursework.
