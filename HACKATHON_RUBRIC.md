# AWS Global Hackathon — Rubric Self-Assessment

Each category mapped to concrete, verifiable evidence in this repository. Gates: **111
tests pass**, `ruff` clean, `bandit -ll` clean, CDK **synth-verified**.

## Business Impact
- A clear buyer (enterprise strategy office) and a recurring, expensive pain (`BUSINESS_CASE.md`).
- **Measured** value computed from the record — assumption coverage, verification rate, audit
  readiness, capital repriced — plus a declared-input ROI estimate: `GET /twin/value`
  (`forward_ledger/value.py`, `test_value.py`).
- The "$40M repriced from one broken belief" cascade is deterministic and defensible
  (`enterprise.propagate`, `test_propagation.py`).

## Innovation
- A category competitors structurally cannot copy: a **verified, sealed-before-outcome
  decision record** + an **assumption ledger** that scores the beliefs reality keeps breaking.
- **Provably right-first** (computable only from seal-time-anchored chains), and a **learning
  flywheel** where each resolved outcome sharpens the next simulation.
- "ChatGPT answers and forgets; the Decision Twin remembers, verifies, and compounds."

## Technical Excellence
- Real **Monte-Carlo simulation engine** with closed-form moments + Sobol sensitivity
  (`forward_ledger/simulation.py`, `test_simulation.py`), not a score.
- Tamper-evident hash chain with settlement integrity (`ledger.py`, `test_ledger.py`).
- 111 tests, typed config, ruff + bandit + pip-audit + gitleaks in CI, moto-tested DynamoDB store.

## AWS-native Architecture
- Bedrock (guardrailed reasoning), Lambda + EventBridge (autonomous settle/anchor), DynamoDB
  (tenant-partitioned store, CMK, PITR), S3 Object Lock (WORM evidence), KMS, Secrets Manager,
  CloudWatch (alarms + X-Ray), API Gateway (throttled, access-logged) — all in `infra/cdk`,
  **synth-verified**. Remove EventBridge+Lambda+S3 Object Lock and the verify-and-learn loop stops.

## Responsible AI
- Honesty by construction (no fabricated foresight), strict model-output validation,
  prompt-injection defense, **Bedrock Guardrails** (content + PII), human-in-the-loop,
  explainable sensitivity, differential privacy, immutable audit log — `RESPONSIBLE_AI.md`,
  `test_responsible_ai.py`.

## Demo
- Zero-AWS, zero-keys local run; `python run_demo.py --check` walks seal → settle → propagate →
  **simulate** → value live. Offline standalone aha screen. Judge can verify a seal on their
  own phone (`/v1/verify/{id}/qr`). Scripts: `demo/JUDGE_SCRIPT.md`, `demo/90_SECOND_DEMO.md`.
