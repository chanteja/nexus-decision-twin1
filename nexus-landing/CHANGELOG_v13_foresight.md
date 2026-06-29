# v13 — Verifiable Foresight (the asset-level pass)

v12 closed a learning loop on top of the forward record. v13 does something harder:
it **concentrates the project on the one asset that actually compounds** (the
seal-time-anchored record + the reputation built on it) and **removes the parts that
diluted or faked it.** The reframe is deliberate — NEXUS issues *Foresight
Certificates*, it is not a "reality OS." Smaller claim, far more defensible.

## What changed and why

### 1. Recalibration is now statistically honest (`recalibrate.py`)
v12 fit a 10-decile isotonic curve at MIN_N=30 (~3 rows/bucket — noise). v13:
- **Beta-Binomial shrinkage** (`PSEUDO=4`): each bucket's empirical survival is pulled
  toward its stated probability, so a sparse bucket barely moves and noise can't fake a bend.
- **MIN_N raised to 40**, identity below it (unchanged honesty invariant).
- **Wilson confidence band** (`reliability_band`, `/v1/reliability`, and inside
  `/v1/calibration.learning`): the curve is shown WITH its uncertainty. A wide band is
  the honest signal that the bend isn't earned yet.
- PAVA monotonicity and the decile `apply()` interface are preserved.

### 2. The consensus-blend (old L3) is removed — it was an anti-asset (`ensemble.py`, `markets.py`)
Blending each new sealed call toward crowd consensus **herds the record**: forecasts
converge, the diversity that makes the trust graph valuable collapses, and consensus
looks accurate because everyone copied it (citogenesis). For a track-record product the
**independence of each sealed call is the asset.** So:
- `apply_learning` now does L1 recalibration only — it never mutates the verdict toward peers.
- Consensus is published as its **own forecaster** (`nexus-consensus`, `consensus_forecast`),
  self-excluding, sealed as a companion entry in `/v1/decide` when a crowd exists. The record
  now carries a second scoreboard: crowd vs. each individual, each with its own resolved track record.

### 3. Canonical questions must bind to external reality (`questions.py`)
- `is_bound(oracle_ref)` + a `q:prov:` prefix for unbound free-text questions.
- Provisional questions can be reasoned about but **never enter markets, trust, or consensus** —
  nothing external can grade them, so they can't earn standing. This is what makes the network
  effect and the settlement honest.

### 4. The Assumption Ledger — the only honest causal asset (`assumptions.py`, `/v1/assumptions`)
Replaces the vaporous "Reality Genome." `Prediction.assumptions` are **sealed into the hashed
core** (timestamped before the outcome). At resolution, each assumption is scored into a separate
append-only corpus, carrying signal **only when the bet it underwrote failed**. Aggregated, it
ranks the beliefs reality keeps falsifying, by domain — unbackfillable, because both the
assumption and the outcome were sealed externally in the past.

### 5. Evidence hashing (`ledger.py`)
Resolution now records `resolution_evidence_hash = sha256(oracle_evidence)`, surfaced in
`/v1/verify`. A stranger can re-derive that we settled on real external evidence, not our say-so —
closing the last "trust us" gap. Stored outside `core()`, so `verify()` is untouched.

### 6. Reputation: difficulty-weighted + first-to-be-right (`trust.py`, `/v1/first_movers`)
- `question_difficulty`: a question the crowd was split on counts more than a near-certain one,
  so farming easy calls no longer climbs the board.
- `trust_graph` adds `effective_trust` (difficulty-weighted) and `first_right`, and sorts by them.
- `first_to_call` / `/v1/first_movers`: who was provably RIGHT FIRST per resolved question, with
  lead time — computable only from a seal-time-anchored chain. The metric analysts actually pay for.
- `author_weight` (used by markets/graph) is unchanged, so nothing downstream breaks.

### 7. Clean Rooms: federate the un-copyable asset (`infra/clean_rooms/federation.py`)
Added `joint_reputation_by_type` + `ANALYSIS_RULE_REPUTATION`: the cohort's joint calibration **by
question type** — which kinds of bets the industry systematically misjudges. Aggregate-only,
count-thresholded; far more valuable than a shared reliability curve.

### 8. `seal_live.py` — the operational half of the winning demo beat
A CLI to seal ONE real, externally-bound call and anchor its Merkle root to OpenTimestamps **days
before the finals**, so a judge can verify on their own phone that the prediction predates the
outcome. Refuses unbound questions. (OTS submission needs network egress at run time; S3 Object
Lock + QLDB remain the AWS-native fallback anchors.)

## New / changed endpoints
- `GET /v1/assumptions` — the Assumption Ledger (causal corpus)
- `GET /v1/first_movers` — first-to-be-right leaderboard
- `GET /v1/reliability` — recalibration curve + 95% Wilson band
- `POST /v1/decide` — seals the independent call (no herding) + a companion `nexus-consensus` entry
- `GET /v1/verify/{id}` — now returns `resolution_evidence_hash`
- `GET /v1/trust` — adds `effective_trust`, `first_right`; sorted by difficulty-weighted quality
- `GET /v1/calibration` — `learning` now carries `reliability_band` + `significant`

## Tests
`tests/test_v13_foresight.py` (12 new) covers bound/provisional, evidence hashing, the assumption
ledger, the consensus forecaster + self-exclusion, difficulty + first-to-call, and the reliability
band. The obsolete herding test was replaced with an independence assertion. **44 passing.**

## What was deliberately NOT built
Reality Genome (theater over public data), causal inference as a "data monopoly" (the bottleneck is
inference, not collection — copyable), a generic decision database as a moat, and any expansion of
the simulator's future-count. None are assets; each hour there is stolen from the seal.
