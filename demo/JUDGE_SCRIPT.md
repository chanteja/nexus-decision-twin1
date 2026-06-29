# NEXUS — judge script

Everything a judge needs to verify the claims in under five minutes. No AWS, no keys.

## 0 · Boot (30s)
```bash
cd backend && pip install -r requirements.txt
python -m pytest -q            # full suite (capabilities, concurrency, multi-tenant, pipeline, security)
python run_demo.py            # serves :8000, seeds the strategy scenario
```

## 1 · The aha (the thing to remember) — `decision-graph.html`
Open `nexus-landing/standalone/index.html?api=http://localhost:8000` → **start here**.
Click **Let reality settle it**. One falsified belief re-scores five connected decisions,
re-ranks what to change, prices the exposure (**$40M repriced**), and the twin learns.
See `90_SECOND_DEMO.md` for the narration. Static previews: `cascade.svg`,
`recommendation-card.svg`.

## 2 · The recommendation engine (the "I want this") — live
```bash
curl localhost:8000/twin/graph/propagate | python -m json.tool
```
Every entry of `recommended_changes` carries: `recommended_action`, `reason`,
`confidence` (before→after), `financial_impact` (capital at risk, dollars repriced,
the model, `estimate:true`), `why_now`, `evidence[]`, `alternative`. The portfolio
total is in `summary.capital_repriced`.

## 2b · The real simulation (the engine, not a score)
```bash
curl "localhost:8000/twin/futures?decision=Open%20Mexico%20next%3F&assumptions=Brazil%20demand%20grows%20%3E18%25,FX%20stays%20stable,we%20can%20hire%20fast" | python -m json.tool
```
`simulation` returns a sampled outcome distribution (p10/p50/p90), expected survival, and a
per-assumption sensitivity ranking. Probabilities are LEARNED from the record — the belief
the demo already falsified gets a low P(holds) and dominates the variance. Real Monte-Carlo,
deterministic by seed (`forward_ledger/simulation.py`).

## 2c · Business impact, measured
```bash
curl localhost:8000/twin/value | python -m json.tool
```
Measured facts (coverage, verification rate, audit readiness, capital repriced) separated
from a declared-input ROI estimate — no invented precision.

## 3 · The proof (verify without trusting us)
```bash
curl localhost:8000/twin/verification        # sealed-pending vs resolved, the proof surface
curl localhost:8000/v1/verify/<id>           # seal predates outcome + chain intact + anchor
```
Or open `verify.html` and recompute a seal's hash on your own device.

## 4 · The honesty invariant (this is the credibility)
```bash
curl localhost:8000/twin                     # Decision Confidence on a FRESH twin = unscored
```
A fresh twin reports **0 verified outcomes** and says so. Dollar figures are labeled
**estimates** with their model attached (`committed capital × Δconfidence`) — no invented
precision. The one genuinely time-anchored seal (`seal_live.py`) is the entry to check.

## What each claim rests on
| Claim | Where it is verified |
|---|---|
| "one broken belief re-scores the strategy" | `GET /twin/graph/propagate` — deterministic read, `test_propagation.py` |
| "$40M repriced" is not fabricated | `financial_impact.model` + `test_financial_impact_is_defensible_not_invented` |
| "sealed before the outcome" | `GET /v1/verify/{id}`, `verify.html`, `test_ledger.py` |
| "the twin learns" | `learning.falsification_rate_*` + `test_v12_learning.py` |
| "controls stay untouched" | `unaffected_decisions` + `test_controls_are_unaffected` |
