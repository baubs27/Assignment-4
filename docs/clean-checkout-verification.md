# Clean-checkout verification

## Version and isolation

Repository: https://github.com/baubs27/Assignment-4

Application source commit: `6c00865acc400e9988ff0c6cc9a3539d02866226`.

A fresh clone of the GitHub main branch was created in an ignored verification directory, outside the working source tree's tracked files. Git status was clean and HEAD matched the source commit above. Python and frontend dependencies were installed from the committed lockfiles into this clone. No original workstation database or generated frontend build was copied into it. The available Python interpreter was selected with MARKET_PYTHON; installed application packages belonged to the clone's own .runtime/python.

## Commands and observed results

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

The isolated server was stopped afterward. The user's primary testing app and its recordings were not altered. Existing browser and real-Yahoo observations are recorded separately in [verification.md](verification.md); this clean-checkout run did not pretend to perform a new live-volume capture.

## Scope of the result

The source, lockfiles, tests, build, startup, static dashboard delivery, and fresh database initialization were verified from the GitHub checkout. The later submission-support commit adds documentation and the derived video without changing application source, dependency locks, or tests. Its application paths are compared to the verified source commit before publication. Existing limitations remain: regular-hours equity volume still needs provider evidence, native date-range UI entry still needs a manual check, and provider timing/availability are not guaranteed.
