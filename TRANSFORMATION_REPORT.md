# NEXUS — Production-Hardening Transformation Report (v18 → v18.1)

This pass took the v18 repository from a beautifully-narrated demo into a defensibly
production-grade codebase, addressing a ruthless multi-lens review (AWS Distinguished /
Google Principal / Apple Staff / Principal Security / Series-A CTO). Work was done as
**atomic, test-gated commits**. The suite grew **70 → 88 passing**; `ruff` is clean and the
CDK stack **synthesizes** verified.

> Delivery note: the connected folders are cloud-synced and block in-place file deletion,
> so git cannot run there. The transformation was executed in a sandbox working copy with
> full git history and is delivered here as a **zip** (working tree) + **git bundle** (all
> 11 commits). `git clone nexus-decision-twin-v18.1.gitbundle` reconstructs the history.

## What changed, by commit
| # | Commit | Area |
|---|--------|------|
| 0 | baseline (v18 as-received, 70 tests) | — |
| 1 | `build:` pyproject + ruff/mypy/pytest + CI | DX / Foundation |
| 2 | `refactor:` retire RIN/OIOS naming; version → 18.0 | Naming |
| 3 | `feat(store):` replace retired QLDB with tenant-scoped **DynamoDBStore** | Architecture / AWS |
| 4 | `test(store):` moto-backed store contract + tenant isolation | Testing |
| 5 | `feat(security):` authn, input validation, CORS allowlist, tenancy | Security / Multi-tenancy |
| 6 | `feat(integrity):` tamper-evident settlement (bind outcomes to seal) | Security / Compliance |
| 7 | `feat(observability):` JSON logging, request IDs, health/version | Observability |
| 8 | `feat(infra):` KMS, Secrets Manager, least-priv roles, throttling, alarms | Infrastructure / AWS |
| 9 | `docs:` reconcile contradictions; document production posture | Documentation |
| 10 | `style:` ruff-clean backend | DX |

## Review findings → resolution
**Resolved**
- *No durable store / DynamoDB unimplemented* → `DynamoDBStore` (full contract, tenant
  partitions, PITR/CMK), selected by `build_store()`; the unused `NEXUS_DDB_TABLE` is now read.
- *Broken QLDBStore (missing asm methods) + QLDB contradiction* → adapter deleted; QLDB
  references purged; verifiability documented as chain + S3 Object Lock.
- *No auth / open write surface* → API-key auth on all mutating endpoints; fail-closed in prod.
- *Multi-tenancy nonexistent (tenant ignored)* → per-tenant isolated ledgers; no cross-tenant reads.
- *Mutable outcomes outside the hash* → settlement hash + `settlement_root`; flips caught by `verify()`.
- *Unbounded inputs / DoS* → bounded, validated schemas.
- *CORS `*`* → explicit allowlist; wildcard refused in prod.
- *Claimed-but-absent KMS/Secrets/least-priv* → all provisioned in CDK (synth-verified).
- *No observability* → structured logs, correlation ids, health/version, CloudWatch alarms.
- *Naming/version drift (RIN/OIOS/16.0)* → unified to the Decision Twin, v18.0.
- *Doc contradictions* ($126M, five-vs-six, QLDB, uPhase) → reconciled to match code.

**Remaining roadmap (next iterations — not yet done)**
- Performance: cache the O(n) `verify()`/`merkle_root()`/trust-graph hot paths; the hash chain
  is serial by construction — shard per tenant/time-window for write throughput at scale.
- Bedrock ensemble: schema-validate model output, add retries/timeouts/guardrails, defend the
  prompt against injection from decision text.
- Generalize the propagation engine beyond the hardcoded Brazil fixture (data-driven graph + edges).
- Persist the actual OpenTimestamps `.ots` proof (currently the attempt is recorded, not the proof).
- WAF on API Gateway; per-tenant rate limits/quotas; X-Ray spans through the ledger.
- Folder restructure to a clean `src/` layout; full mypy typing; OpenAPI doc curation.
- Landing/product unification (the consumer "Tree of Futures" art vs. the enterprise surface).

## Gates
- Tests: `pytest` → **88 passed**.
- Lint: `ruff check backend` → clean.
- Infra: `python infra/cdk/app.py` → synth OK (KMS✓ Secrets✓ DDB CMK+PITR✓ S3 ObjectLock+KMS✓
  3 least-priv roles✓ throttling 50/100✓ 3 alarms✓).
