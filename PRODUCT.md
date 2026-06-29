# NEXUS — Product

> One product: the **Decision Twin**. One buyer: the **enterprise strategy team**.
> One job: make every strategic decision remembered, verified, and improving.

This document is organized the way the customer experiences the product — as a sequence
of workflows, not a list of features. Each capability answers a question a Head of
Strategy actually asks.

---

## The customer: the enterprise strategy office

A Head of Strategy (or Corp Dev, or the office of the COO) owns a portfolio of bets —
market entries, build/buy decisions, pricing moves, org changes. Their pain is specific:

- decisions rest on assumptions that are never written down;
- when a bet fails, no one can say which belief broke or what else depended on it;
- last year's reasoning is gone — it left with the analyst who built the deck;
- nobody can prove a forecast was made *before* the outcome, so no one learns from it.

Every workflow below removes one of those pains.

---

## Workflow 1 · Capture a decision → the **Decision Twin**

*"Hold what we decided and why, so it doesn't evaporate."*

The strategy team puts a decision into the twin with the assumptions it rests on. The
twin holds the living state of how the organization decides and surfaces one number:

**Decision Confidence** — a single, honest signal built from four sub-signals:

```
Decision Confidence
├── forecast accuracy        how often sealed calls matched reality
├── historical calibration   has the track record earned its shape?
├── evidence quality         are outcomes backed by checkable evidence?
└── assumption stability     how often do the beliefs we bet on hold up?
```

It is **unscored until real outcomes exist.** A fresh twin says so instead of inventing a
number — and that honesty is what lets a CIO trust the number once it appears.

`GET /twin`

---

## Workflow 2 · Connect the decisions → the **Decision Graph** (alive)

*"Show me everything standing on the same belief — and react when one breaks."*

Every decision is wired to its assumptions, the evidence behind them, and the outcomes
that settle them. The graph is not a diagram you read once. It is **a living system**:

```
evidence arrives ─▶ assumption falsified ─▶ confidence drops ─▶ forecasts change
       ─▶ recommendations change ─▶ timeline updates ─▶ the twin learns
```

When reality falsifies one assumption, NEXUS walks the graph and re-scores every
connected decision — ranking the revisions each one needs by business impact, and
recording what the twin learned. This is the product's signature moment.

`GET /twin/graph` · `GET /twin/graph/propagate` · `GET /twin/graphs` (Decision Memory: reuse & extend graphs)

> **The aha, concretely.** Brazil GTM was sealed on *"demand grows >18% YoY."* Reality
> said ~6%. Four other decisions stood on that belief — with the failed Brazil launch,
> **$126M of committed capital** rode on it in total;
> their confidence drops live, the recommendations re-rank with the exposure each one
> re-prices (**~$40M repriced in total**), and the assumption's falsification rate rises so
> future bets inherit the lesson. Two unrelated decisions are correctly left untouched.

---

## Workflow 3 · Reason about a bet → the **Future Explorer**

*"Should we open Mexico next?"*

Future Explorer answers an executive decision — not a generic forecast. For any question
it returns the recommended action and the futures around it:

- **best / expected / worst** outcome
- the **assumptions that matter most** to the call
- **confidence**, and what would change it
- a **recommended action**

Under the hood this is a **real probabilistic simulation**, not a single score: name the
assumptions a decision rests on and Future Explorer runs a Monte-Carlo model
(`forward_ledger/simulation.py`) — exact closed-form expected survival and variance,
sampled best/expected/worst tails, and a per-assumption sensitivity ranking (which beliefs
actually drive the outcome). Each assumption's probability is **learned** from the verified
record (1 − its falsification rate), so the simulation sharpens every time reality settles
a call. `GET /twin/futures?decision=...&assumptions=a,b,c`.

You explore a decision here *before* you commit it; sealing it is a separate, deliberate
step (Workflow 4). Exploration never quietly becomes a commitment.

`GET /twin/futures?decision=...`  ·  the whole flow in one call: `GET /twin/pipeline`

---

## Workflow 4 · Put it on the record → **Reality Verification**

*"Prove this call was made before we knew the answer."*

When the team commits a decision, NEXUS seals it on the record before its outcome exists,
then settles it later against reality. The proof is the product's spine:

```
evidence ─▶ verification ─▶ Decision Confidence ─▶ certificate ─▶ learning
```

A stranger can verify a sealed decision on their own phone — recomputing it on their own
device, confirming the seal predates the outcome, with nothing taken on our word. Every
hackathon team can claim a "twin." Almost none can hand a judge a decision their own
phone verifies. *(How the seal works is in `ARCHITECTURE.md`.)*

`GET /twin/verification` · `GET /v1/verify/{id}` · `GET /v1/verify/{id}/qr`

---

## Workflow 5 · Start the day → the **Decision Timeline**

*"What's changed today?"*

The Timeline opens on exactly that question. Every morning the strategy team sees:

- decisions reality **settled** since yesterday
- the ones that settled **against expectation**
- forecasts **drifting** and decisions now **at risk**
- the **recommended actions** that follow

This is the daily-habit surface: a reason to open NEXUS every morning, not just at the
quarterly review. Past (resolved), present (sealed & waiting), future (next outcomes due)
on one axis.

`GET /twin/timeline`

---

## Workflow 6 · Compound it → **Organizational Learning**

*"Get smarter every time we're right or wrong."*

Learning is visible, not buried. When an outcome lands, the twin updates: the belief that
broke carries a higher falsification rate, the calibration of the whole twin sharpens, and
every future strategy that leans on that belief inherits the lesson automatically. The
team watches the twin say: *we were wrong here, the twin learned, future confidence on
this belief is now lower.* That visible improvement is what makes the product compound.

---

## Decision Confidence is never passive

Whenever confidence moves, NEXUS says **why** and **what to do**. Every recommendation is
an executive memo, not a number that just dropped:

```
Recommended action   Hold the Mexico expansion (FY+1)
Reason               Leans on the belief reality disproved: "demand grows >18% YoY"
Confidence           59% → 9%
Expected impact      ~$24.1M repriced  ($48M committed × the drop in survival probability)
Why now              A shared upstream belief settled false this cycle; the window is open
Evidence             Brazil demand settled ~6% (independent oracle) · sealed 45 days early
Alternative          Redeploy the budget to the validated EU platform — decorrelated thesis
```

A number that just drops is anxiety; a number that drops *and tells you what to change,
what it's worth, and what to do instead* is enterprise software. The dollar figure is an
**estimate** with its model attached — never invented precision.

---

## What the strategy team never sees

The product surface is five capabilities. The verification mechanism, the learning math,
the storage, and the cloud plumbing are **implementation** — they never appear in a
response a user reads, and they live only in `ARCHITECTURE.md`. If a thing does not
strengthen one of the five capabilities, it is a module, and it stays hidden.

---

## Run the workflows (no AWS, no keys)

```bash
cd backend
pip install -r requirements.txt
python -m pytest -q                 # full suite: capabilities, concurrency, multi-tenant, pipeline, security
python run_demo.py                  # serves http://localhost:8000

curl localhost:8000/twin                  # Workflow 1 — Decision Twin + Confidence
curl localhost:8000/twin/graph/propagate  # Workflow 2 — the living graph (the aha)
curl "localhost:8000/twin/futures?decision=Should%20we%20open%20Mexico%20next%3F"  # Workflow 3
curl localhost:8000/twin/verification     # Workflow 4 — the proof
curl localhost:8000/twin/timeline         # Workflow 5 — "What's changed today?"
```
