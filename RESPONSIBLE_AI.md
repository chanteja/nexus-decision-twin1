# Responsible AI

NEXUS is built so that trust is a property of the *construction*, not a promise. The
core principle: **the system never fabricates foresight.**

## 1 · Honesty by construction (no fabrication)
- Decision Confidence is **unscored until real outcomes exist** — a fresh twin reports zero
  and says so (`api/twin.py: decision_confidence`).
- Forecasts are **sealed before the outcome exists** and settled by an **oracle the predictor
  does not control**; the seal-before-resolution ordering is enforced in code
  (`ledger.resolve` raises if resolution precedes the seal).
- Model output is **strictly validated** before it can influence a verdict: out-of-range
  "fabricated certainty" is rejected and weights are renormalised to a real distribution
  (`ensemble._validate_vote`, `test_responsible_ai.py`).

## 2 · Transparency & explainability
- Every recommendation is an **executive memo** — action, reason, dollar impact (with its
  model), why-now, evidence, and the alternative — never an unexplained number.
- Future Explorer reports **why**: a per-assumption sensitivity ranking (tornado swing +
  first-order Sobol variance share) showing exactly which beliefs drive an outcome
  (`forward_ledger/simulation.py`).
- Dollar figures are labelled **estimates** with the formula attached; measured facts and
  estimates are never conflated (`forward_ledger/value.py`).

## 3 · Human-in-the-loop
- Exploration never auto-commits: simulating a decision (`/twin/futures`) and sealing it
  (`/v1/commit`) are separate, deliberate steps.
- The system **recommends and prices**; a human commits. Autonomous components (settlement,
  anchoring) only act on the verifiable record, never invent outcomes.

## 4 · Safety guardrails on the model path
- **Prompt-injection defense:** user decision/constraint text is sanitised (control-char
  strip, length cap) and fenced as untrusted data the model is told never to obey.
- **Bedrock Guardrails** (CDK `CfnGuardrail`): hate/insults/violence/misconduct/prompt-attack
  content filters + PII anonymisation, applied on every Converse call when configured.
- One model failing never blocks the ensemble; zero valid votes → fall back to the local
  model rather than emit a low-quality or unsafe verdict.

## 5 · Privacy & data governance
- **Differential privacy** (ε-Laplace) on all cross-tenant federated aggregates, plus
  k-anonymity min-cell suppression (`infra/clean_rooms/federation.py`).
- **Tenant isolation** bound to identity; no read crosses a tenant boundary.
- **Crypto-shred erasure** model for GDPR right-to-erasure (`RETENTION.md`).
- PII is anonymised by Guardrails; logs carry hashed principals, never secrets.

## 6 · Auditability
- Append-only, hash-chained record with tamper-evident settlement; Merkle + settlement
  roots externally anchored. A structured **security audit log** records every mutation
  (actor, tenant, request id) and every auth decision.

## 7 · Limitations (stated plainly)
- The local reasoning fallback is a deterministic heuristic, not a frontier model; the
  Bedrock ensemble is the production reasoner and is the path under guardrails.
- The learning flywheel needs resolved outcomes to sharpen; early on it is honestly thin.
- Differential privacy trades exactness for protection — released aggregates carry noise by
  design, with the ε budget reported on every response.
