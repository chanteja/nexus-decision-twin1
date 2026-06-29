# CHANGELOG — v11 "The Record"

The upgrade that turns NEXUS from a retrospective argument into a forward,
verifiable prediction record. Addresses the core teardown finding: in v10 every
"proof" was retrospective and self-asserted.

## Added — the Forward Ledger (the moat)
- `backend/forward_ledger/ledger.py` — append-only, hash-chained, tamper-evident log
  with a publishable Merkle root and a hard seal-before-resolution invariant.
- `store.py` (FileStore/MemoryStore) + `qldb_adapter.py` (AWS QLDB, the immutable
  journal that anchors the seal independent of our app).
- `oracles.py` + `resolver.py` — autonomous settlement by sources NEXUS does not
  control; predictions never self-grade.
- `calibration.py` — accuracy/Brier/reliability from **resolved rows only**; forward
  (the real test) and backtest (hindsight, context) kept strictly separate; honest
  empty/small-n states.
- `trust.py` — calibration-weighted Trust Graph with sample-size shrinkage.
- `markets.py` — calibration-weighted Reality Markets vs a naive market.
- `ensemble.py` — `/v1/decide` emits the full 7-branch vector to seed the
  counterfactual corpus; Bedrock ensemble with deterministic local fallback.
- `api/app.py` — `/v1/decide` (seals when resolvable), `/v1/commit`, `/v1/calibration`,
  `/v1/ledger`, `/v1/verify/{id}`, `/v1/prove`, `/v1/trust`, `/v1/markets`, `/v1/status`.
- `tests/` — 13 tests covering chain integrity, tamper detection, the ordering
  invariant, resolved-only calibration, trust shrinkage, and the API loop. All pass.
- `infra/cdk/` — QLDB ledger, resolver Lambda on an EventBridge cron, API Gateway.
- `infra/clean_rooms/federation.py` — privacy-safe joint calibration across tenants.

## Changed — the landing now reads the real record
- Proof panel reframed from "backtest" to **THE RECORD**: forward (sealed-before-
  outcome) is the headline; backtest is shown as labeled hindsight context.
- `loadCalibration`/`renderProof` consume the new forward/backtest shape; **prove it**
  now calls `POST /v1/prove` to settle due predictions live; added **put your decision
  on the record** → `POST /v1/commit` returning a hash + Merkle root + verify link.
- Substrate line → `aws qldb immutable ledger · lambda+eventbridge auto-resolver ·
  clean rooms federation`. HUD telemetry no longer wears a "live" costume in demo mode.
- `src/landing/useNexusData.ts` brought to parity: forward-ledger types, `commitPrediction`,
  `proveLedger`, `fetchTrust`, `fetchMarkets`.

## Honesty guarantees (by construction)
- Fresh ledger → 0 resolved forward predictions, stated plainly.
- Forward calibration is never inflated; small-n is flagged illustrative.
- Backtest is never presented as the forward claim.
- Every seal provably predates its resolution, or `verify()` raises.
