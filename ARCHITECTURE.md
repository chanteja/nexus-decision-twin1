# NEXUS — Architecture

This document is ordered the way the product is: **capabilities first, infrastructure
last.** The first half is what the Decision Twin does. The second half is the engineering
that makes it trustworthy — the verification and learning machinery, and the AWS
deployment. Implementation vocabulary is confined to the second half on purpose.

---

# Part I — The product capabilities

The primary asset is the **Decision Twin**: a living model of how an organization decides,
the assumptions under each decision, and how often reality has agreed. Everything else
exists to capture it, verify it, and compound it.

```
                          ┌──────────────────────────┐
   strategy team ────────▶│       DECISION TWIN       │   one product, one number
                          └────────────┬─────────────┘
            ┌──────────────┬───────────┼───────────┬──────────────┐
            ▼              ▼           ▼           ▼              ▼
      Decision Graph   Future     Reality      Decision      Organizational
       (alive)         Explorer   Verification Timeline      Learning
            │              │           │           │              │
            └──────────────┴─────┬─────┴───────────┴──────────────┘
                                 ▼   (Part II — the engineering, hidden behind the product)
            verification mechanism · learning loop · decision store · AWS
```

## 1 · Decision Twin

The living state of how the org decides, projected onto one **Decision Confidence** number
with four honest sub-signals (forecast accuracy, historical calibration, evidence quality,
assumption stability). Unscored until real outcomes exist. `GET /twin`.

## 2 · Decision Graph (the living system)

Every decision is a node wired to the assumptions, evidence, and outcomes it depends on.
The graph **reacts**: when an assumption is falsified, `propagate()` walks the connected
decisions, drops each one's confidence in proportion to how load-bearing the broken belief
was, ranks the required revisions by business impact, and records what the twin learned.

```
GET /twin/graph              the decisions ↔ assumptions ↔ outcomes structure
GET /twin/graph/propagate    feed it a falsified belief → the live cascade (the aha)
GET /twin/graph/scenario     the canonical enterprise scenario the demo drives
```

Deterministic and read-only over the verified record, so it is safe to run live on stage.

## 3 · Future Explorer

Reason about a decision before committing it: best / expected / worst futures, the
assumptions that matter, confidence, and a recommended action. `GET /twin/futures`.

## 4 · Reality Verification

Every decision is sealed before its outcome exists and settled later against reality, so a
stranger can check it without trusting us. The proof surface: `GET /twin/verification`,
`GET /v1/verify/{id}`, `GET /v1/verify/{id}/qr`. *(Mechanism in Part II.)*

## 5 · Decision Timeline

One time axis that opens on **"What's changed today?"** — newly settled decisions, the
ones that broke expectation, forecasts at risk, and the actions that follow.
`GET /twin/timeline`.

## 6 · Organizational Learning

Outcomes feed back: a falsified belief's falsification rate rises, the twin's calibration
sharpens, and future strategies leaning on that belief inherit lower confidence
automatically. Learning is surfaced, not hidden — the team watches the twin improve.

---

# Part II — The engineering (how the capabilities are made trustworthy)

Everything below is implementation. It never surfaces in a product response; it lives here
so a CTO can audit exactly how verification and learning work.

## The verification mechanism

Decisions are written to an **append-only, hash-chained record** (`forward_ledger/`). Each
entry hashes its immutable core (sequence, id, decision, timestamp, previous hash) and
carries the prior entry's hash — edit any sealed decision and every later hash breaks. The
whole record reduces to a **Merkle root** that is published to an external time authority
and mirrored to **S3 Object Lock (WORM)** — the always-on, AWS-native external anchor that
NEXUS cannot rewrite after the fact. An **OpenTimestamps** (Bitcoin) submission is also made
when network egress is available; persisting and upgrading the `.ots` proof to a confirmed
Bitcoin attestation is tracked as roadmap, so today S3 Object Lock is the anchor a stranger
relies on, with OTS as a best-effort second source.

Outcomes are settled by an **oracle the predictor does not control** (live: Polymarket /
financial / RSS sources; demo/tests: a fixed dated answer key the record never sees at
seal time). The ordering invariant — resolution can never precede the seal — is enforced
in code. Settlement records a hash of the external evidence and a **settlement hash** that binds the
outcome to the immutable seal — so a later edit to `survived` or `resolved_at` is detected by
`verify()`, and the per-record **settlement root** can be anchored alongside the seal root.
This closes the last "trust us" gap and makes both the seal AND the outcome checkable by a
stranger.

## The learning loop

- **Calibration** is computed only over resolved decisions; a fresh record honestly
  reports zero. **Recalibration** fits a monotone reliability curve (with shrinkage and
  95% confidence bands) so stated confidence converges on what each band actually
  achieved — and stays the identity map until enough outcomes exist to earn a bend.
- **The Assumption Ledger** (`assumptions.py`) is the honest causal asset: each sealed
  decision's named assumptions are timestamped into the record, and an assumption accrues
  signal only when a bet that leaned on it failed. Aggregated, it ranks the beliefs reality
  keeps falsifying — and it is exactly what `propagate()` reads to drive the cascade.
- **Reputation** (`trust.py`, surfaced as the Reality Score) ranks forecasters by
  difficulty-weighted, calibration-shrunk accuracy over sealed-before-outcome calls — a
  number that can only rise by living through time on the record.

## The decision store

The chain logic is the asset; the store is swappable behind one Protocol. Production uses
**`DynamoDBStore`** (`forward_ledger/dynamo_store.py`) — a single-table, **tenant-partitioned**
durable store (CMK-encrypted, PITR-enabled) holding the entries plus the counterfactual and
assumption sibling logs; **S3 Object Lock** holds the write-once anchor; a `FileStore` covers
zero-infra local runs. `build_store()` selects one from the environment (`NEXUS_DDB_TABLE`),
so the product contract never changes with the backend — the demo is bulletproof and
production is one env var away. Every tenant is isolated under its own partition; no query
crosses a tenant boundary.

> Note: Amazon QLDB was retired on 2025-07-31. The verifiability never lived in a managed
> journal — it lives in the application-level hash chain + S3 Object Lock + OpenTimestamps.
> Nothing breaks because a single service was sunset.

## Why AWS (each service maps to a business capability)

| Business capability | AWS service | Why it is essential |
|---|---|---|
| Enterprise reasoning over a decision | **Bedrock** | the multi-model panel that reasons each decision and its assumptions |
| Continuous verification | **EventBridge** | the hourly cron that settles assumptions against reality — no human |
| Autonomous execution | **Lambda** | settles outcomes and anchors the record on its own |
| The living Decision Graph | **DynamoDB** | the decisions, assumptions, and edges `propagate()` walks |
| Immutable evidence | **S3 Object Lock** | write-once anchor; a seal cannot be backdated, even by us |
| Enterprise observability | **CloudWatch** | every settlement and propagation is auditable |
| Governance & security | **IAM · Secrets Manager · KMS** | the controls a CIO requires |
| Privacy-preserving partner data | **Clean Rooms** *(roadmap; modeled in `infra/clean_rooms/`)* | orgs pool calibration without exposing a single raw decision |

> *(The model layer is provider-agnostic: production reasons via Bedrock or any OpenAI-compatible endpoint; the zero-key offline demo uses a deterministic local reasoner so it always runs — the differentiated value is the verified record, propagation, simulation, and calibration, not the model.)*

Remove EventBridge + Lambda + S3 Object Lock and the autonomous verify-and-learn loop
stops — that is what makes AWS inevitable here, not incidental.

## Data flow

```
strategy team
    │  commit a decision (+ its assumptions)  ─▶  reason (Bedrock panel)  ─▶  SEAL
    ▼
append-only record  ─▶  DynamoDB / FileStore
        │
EventBridge (hourly) ─▶ Lambda ─▶ oracle settles outcome ─▶ score it
        │                                   │
        │                                   ├─▶ Assumption Ledger updates (drives the cascade)
        │                                   └─▶ reliability curve bends (the twin learns)
EventBridge (daily)  ─▶ Lambda ─▶ Merkle root ─▶ OpenTimestamps + S3 Object Lock
        │
GET /twin/graph/propagate  ◀── a falsified belief re-scores the connected strategy (the aha)
GET /twin/timeline         ◀── "what's changed today?"
GET /v1/verify/{id}        ◀── seal predates outcome + hash intact + external anchor
```

## Graceful degradation

No DynamoDB → `FileStore`. No Bedrock → local reasoning ensemble. `NEXUS_DEMO=1` → seeded
scenario + dated answer key. The product contract is identical across all of them, so the
landing and demo cannot tell which backend is mounted.

## The product / engineering boundary

The five capabilities (`backend/api/twin.py`) are the only thing a user understands. The
`/v1/*` contract (`backend/api/app.py`) is the internal surface the landing and demo
speak; the `forward_ledger/` package is the verification and learning core. Internal module
names (ledger, oracle, calibration, anchor, trust) are deliberately confined to this
package and this document — they are never product concepts.

## Security & operability (production posture)

The write surface is authenticated (API key via `Authorization: Bearer` / `X-API-Key`,
constant-time compared; keys sourced from **Secrets Manager** in production). The service
**fails closed**: `NEXUS_ENV=production` without configured keys, or with wildcard CORS,
refuses to boot. All inputs are bounded and validated at the edge (branch count, text
lengths, tenant slug pattern, probability ranges). CORS is an explicit allowlist. Every
request carries a correlation id (`X-Request-ID`) and emits a structured JSON log line
(method, path, status, latency); `/healthz` reports chain integrity and `/version` the
build. IAM is least-privilege **per function** (api/resolver/anchor each have their own
role; Bedrock is scoped to foundation-model ARNs). Encryption at rest is a customer-managed
**KMS** key for DynamoDB and S3; TLS is enforced; CloudWatch alarms fire on function errors.
