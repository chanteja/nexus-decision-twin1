# CHANGELOG — v12 "The Loop"

The upgrade that turns NEXUS from a forward **record** into a record that **learns**.
Addresses the core teardown finding: v11 stored foresight but never compounded from
it — calibration was measured and discarded, the counterfactual corpus was a
docstring, the "reality graph" was a line, and the seal was asserted rather than
externally anchored. v12 closes every one of those loops, in code, with tests.

All additions are honest by construction: each loop is a no-op until evidence exists,
so nothing claims the system learned what it has not yet earned.

## Added — the learning loop (the answer to "why exponential after year 3?")

- `forward_ledger/recalibrate.py` — **L1**: isotonic (PAVA, monotone) recalibration
  over resolved forward rows. Maps raw survival probability to what each confidence
  band actually achieved. Identity map below `MIN_N=30` resolved rows. Surfaced in
  `/v1/calibration.learning` so the curve can be shown bending on stage.
- `forward_ledger/counterfactual.py` + `Ledger._emit_counterfactuals` — **L2**: at
  resolution, the full branch vector is scored into a **separate append-only corpus**
  (`store.append_cf` / `.cf` sibling log / `forward_ledger_cf` QLDB table). The hashed
  core is never touched — `verify()` still passes. `regret = branch_prob` when the
  taken path failed, else `0`. Read via `/v1/counterfactuals`, aggregated by domain.
- `forward_ledger/ensemble.apply_learning()` — **L3**: blends the verdict toward the
  calibration-weighted consensus of *other* sealed forecasts on the same canonical
  question, shrunk by evidence, capped at α=0.5. `decide()` stays pure and swappable.
- `forward_ledger/questions.py` — canonical question identity; markets and the graph
  accrete onto stable ids instead of fragmenting on phrasing.
- `forward_ledger/graph.py` — the **typed reality graph** (Questions / Predictions /
  Outcomes / Authors + FORECASTS / ON / SETTLED_BY / CONTESTS edges) and `movers()`.
- `forward_ledger/anchor.py` + `anchor_handler.py` — the **external anchor**:
  OpenTimestamps (Bitcoin-anchored, network-gated) + an append-only anchor log,
  mirrored in prod to S3 Object Lock (WORM) and the QLDB journal digest.

## Changed

- `api/app.py` — `/v1/decide` now runs `apply_learning` (L1+L3) before sealing;
  `/v1/graph` returns the typed graph; new `/v1/movers`, `/v1/counterfactuals`,
  `/v1/anchor`; `/v1/prove` anchors the new head after settling; `/v1/verify/{id}`
  returns the external-anchor history; `/v1/calibration` exposes the `learning` state.
- `markets.py` — re-keyed by canonical question id; added `question_consensus()` (L3).
- `calibration.py` — emits the fitted reliability map + recalibration state.
- `store.py` / `qldb_adapter.py` — `append_cf` / `load_cf` for the counterfactual
  corpus (FileStore, MemoryStore, QLDB all parity).
- `ledger.py` — `resolve()` fans out to counterfactual emission; `counterfactual_rows()`
  read surface. Seal hashing unchanged.
- `run_demo.py --check` — now also prints the counterfactual corpus, the typed graph
  counts, and an external anchor.

## Infra

- `infra/cdk/nexus_rin_stack.py` — added an **S3 Object Lock (WORM)** anchor bucket
  and a **daily anchor Lambda** on EventBridge; IAM scoped to the bucket; fixed a
  latent `CfnLedger.attr_arn` reference (the attribute does not exist in this cdk
  version) by constructing the QLDB ARN via `format_arn`. Stack now `cdk synth`s clean.
- `infra/clean_rooms/federation.py` — added a **second analysis rule** federating
  joint **counterfactual regret by domain** (and a consensus rule), count-thresholded,
  so the un-copyable assets are pooled — not just the reliability curve.

## Frontend

- `src/landing/useNexusData.ts` — added `LearningState` on `Calibration`, and
  `fetchCounterfactuals`, `fetchRealityGraph` (typed), `fetchMovers`, `anchorLedger`.
  All read-only, all degrade to the live-feeling demo offline.

## Tests

- `tests/test_v12_learning.py` (14) + new API cases — recalibration identity/bend/
  monotonicity, counterfactual emission + regret semantics + domain aggregation,
  chain-still-valid-after-CF, typed graph + canonical accretion, movers, L3 blend,
  anchor history, and the new endpoints. **32 tests pass** (was 13).

## Honesty guarantees (by construction, carried from v11 and extended)

- Recalibration is the identity map until ≥30 forward rows resolve.
- Peer-consensus blending is a no-op when a question has no peers.
- Counterfactual regret is `0` for any decision that resolved correctly.
- The hashed seal core is never altered by resolution or counterfactual emission —
  `verify()` passes after every operation.
