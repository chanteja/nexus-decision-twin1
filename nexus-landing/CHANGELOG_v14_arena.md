# CHANGELOG v14 — The Reality Arena

v13 made the project a verifiable forward record. v14 makes a judge **experience** it
in five minutes instead of hearing about it. Three demo-critical builds, nothing
rewritten, AWS kept central.

## 1. Aged seal → live resolution
A backdated, ~30-day-old Human-vs-AI cohort (`forward_ledger/arena_seed.py`) is sealed
into the same hash-chained ledger. Eight questions are already due; **two are held
back** and released on operator command, so reality "arrives" on stage and the board
moves — regardless of how long the server has been running.

- `POST /v1/prove` settles the already-due seals → the board fills.
- `POST /v1/demo/resolve_live` releases the held questions → the top scores shift.
- Every arena seal predates its resolution (`created_at` ~30d ago, `resolved_at` = now);
  `Ledger.verify()` still passes. The seal-before-outcome invariant is real.

## 2. Judge phone verification
- `standalone/verify.html` — a phone-first page that reads `/v1/verify/{id}`,
  **recomputes the hash in the judge's own browser**, confirms seal < resolution, and
  shows the external anchor. No NEXUS account, no trust required.
- `GET /v1/verify/{id}/qr?base=<public-origin>` returns an SVG QR (pure-Python `segno`)
  that deep-links the verify page to that entry. The arena screen renders it live.

## 3. The Reality Score leaderboard (humans vs AI)
- `forward_ledger/reality_score.py` — ONE legible integer per forecaster:
  `1000 + 800·difficulty-weighted-calibration + 12·first-to-be-right (cap 120)`.
  A projection of the existing Trust Graph — uncopyable for the same reason it is.
- `GET /v1/leaderboard`, `GET /v1/reality_score`, `GET /v1/arena` (board + live state
  + countdown + honesty note).
- `standalone/arena.html` — Humans vs Claude vs GPT vs Gemini, animated score deltas,
  the two live-resolution buttons, the anchor button, and the scannable verify QR.
- Forecasters with only pending calls show as **provisional** so the board is alive
  before anything resolves.

## Honesty (the whole point of the project)
The arena is the **spectacle**: a backdated demo cohort, real chain + real ordering but
illustrative. Every arena row is reported `cohort: "demo"`, and `/v1/calibration` keeps
its **illustrative** caveat whenever demo rows are present (it no longer drops the
caveat just because n ≥ 30) and splits `cohorts.real_forward_resolved` vs
`demo_forward_resolved`. The genuinely anchored, verify-on-your-phone **proof** is a
`seal_live.py` entry (one real bound call, OpenTimestamps). Spectacle vs proof — never
conflated.

## AWS posture (unchanged, clarified)
AWS stays central: Bedrock (the model panel that becomes the AI competitors), Lambda +
EventBridge + Step Functions (the autonomous resolve/anchor loop), S3 Object Lock (WORM),
Neptune, Clean Rooms, KMS. The only correction is factual: **AWS retired QLDB on
2025-07-31**, so the durable immutable store is now the app-level Merkle chain persisted
in DynamoDB/S3 with **S3 Object Lock (WORM)** + **OpenTimestamps** as the verifiable
anchor. Verifiability lives in the chain, not in any one managed service. See
`ARCHITECTURE.md` (v14 addendum).

## Files
- new: `backend/forward_ledger/reality_score.py`, `backend/forward_ledger/arena_seed.py`,
  `nexus-landing/standalone/arena.html`, `nexus-landing/standalone/verify.html`,
  `backend/tests/test_v14_arena.py`
- changed: `api/app.py` (arena seed at startup; `/v1/leaderboard`, `/v1/reality_score`,
  `/v1/arena`, `/v1/demo/arena`, `/v1/demo/resolve_live`, `/v1/verify/{id}/qr`),
  `oracles.py` (`SeedOracle.extend`), `calibration.py` (honesty caveat + cohorts),
  `forward_ledger/__init__.py`, `requirements.txt` (`segno`), `run_demo.py` (--check arena).
- tests: **51 passing**.

One sentence: *the world's first verifiable forecasting infrastructure where humans and
AI compete to predict reality — and a judge checks the proof on their own phone.*
