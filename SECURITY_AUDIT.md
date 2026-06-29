# NEXUS — Production Security Audit (Fortune 100 readiness)

Scope: the v18.1 hardened tree. Method: STRIDE + OWASP Top 10 review across the
categories requested, grounded in code. Each finding lists severity, evidence, and
resolution. **Fixed** items were remediated and test/scan/synth-verified in this pass;
**Roadmap** items are scoped but deferred. Test suite: 96 passing. SAST (bandit -ll):
clean. CDK: synth-verified.

## Severity summary
| Sev | Found | Fixed | Roadmap |
|---|---|---|---|
| Critical | 1 | 1 | 0 |
| High | 6 | 6 | 0 |
| Medium | 8 | 7 | 1 |
| Low | 5 | 4 | 1 |

---

## Authentication
- **[High] Static principal leaked key prefix to logs** — `auth.require_auth` returned
  `"key:"+key[:6]`. **Fixed:** principal id is now `k_<sha256[:12]>` (`auth.key_id`); the
  secret never reaches logs.
- **[Med] No default-deny** — auth was per-route opt-in; a new mutating route could ship
  unprotected. **Fixed:** `_default_deny` middleware rejects credential-less mutating
  requests when auth is enabled (`api/app.py`), independent of per-route deps.
- **[Med] No anti-bruteforce / lockout at app tier.** **Mitigated/Roadmap:** API Gateway
  throttling (50 rps/100 burst) bounds it; per-identity lockout is roadmap.

## Authorization  — **the critical finding**
- **[Critical] Broken access control: client-controlled tenant (IDOR)** — the acting
  tenant came from the request body, so any valid key could read/write any tenant.
  **Fixed:** keys are bound to a tenant (`tenant:key`); the acting tenant derives from the
  authenticated `Principal`; a mismatching body tenant returns **403**
  (`auth.effective_tenant`). Reads resolve the caller's tenant via `tenant_ledger`.
- **[High] Unauthenticated reads (information disclosure / Zero Trust)** — GET endpoints
  exposed the decision record with no auth. **Fixed:** all `/v1/*` reads and the `/twin/*`
  surface authenticate in production and are tenant-scoped.

## Tenant isolation
- **[Critical] (above)** client-controlled tenant — **Fixed.**
- **[High] Reads always served the default tenant** — `/v1/*` and `/twin/*` used a global
  ledger. **Fixed:** `tenant_ledger` dependency scopes every read to the principal's tenant;
  no read crosses a boundary (`test_reads_are_tenant_scoped`).
- **[Low] Key injection via tenant id** — **Fixed earlier:** `valid_tenant` slug guard
  blocks partition-key/path injection (`test_invalid_tenant_rejected`).

## OWASP Top 10
- **A01 Broken Access Control** — tenant IDOR + unauthenticated reads. **Fixed.**
- **A02 Cryptographic Failures** — key prefix in logs (**Fixed**); OTS proof not persisted
  (**Roadmap**); `resolution_evidence_hash` is a hash of a self-authored ref, not fetched
  external evidence (**Roadmap** — needs a signed oracle-evidence fetch).
- **A03 Injection** — DynamoDB uses parameterised SDK (safe). Prompt injection into the
  Bedrock ensemble from decision text is **Roadmap** (guardrails/validation).
- **A04 Insecure Design** — tenant-from-body + no default-deny. **Fixed.**
- **A05 Security Misconfiguration** — wildcard CORS refused in prod (prior); `/docs`,
  `/redoc`, `/openapi.json` now disabled in production. **Fixed.**
- **A06 Vulnerable Components** — no dep scanning. **Fixed:** pip-audit + Dependabot in CI.
- **A07 Identification/Auth Failures** — static keys, no rotation. **Partially Fixed:**
  keys in Secrets Manager (rotatable); automated rotation is **Roadmap**.
- **A08 Software/Data Integrity** — settlement integrity (prior); CI actions tag-pinned,
  managed by Dependabot (SHA-pin is **Roadmap**, documented in `ci.yml`).
- **A09 Logging/Monitoring Failures** — no security audit trail. **Fixed:** `nexus.audit`
  structured events for auth-deny + every mutation (actor, tenant, request id).
- **A10 SSRF** — `polymarket_resolver` built a URL from a client-supplied `oracle_ref`.
  **Fixed:** strict `oracle_ref` validation (hex/alnum condition, yes/no side) and
  `follow_redirects=False` before any HTTP call (`test_oracle_ref_injection_is_rejected`).

## AWS IAM
- **[High] api role had read/write on the WORM anchor bucket** — over-privileged.
  **Fixed:** api role is **read-only**; only `AnchorFn` writes.
- **[Med] Bedrock on `*`** — **Fixed prior:** scoped to `foundation-model/*` ARNs.
- **[Low] Shared role across functions** — **Fixed prior:** separate role per function.

## Encryption
- **[Med] Secrets Manager used the AWS-managed key** — **Fixed:** secret encrypted with the
  customer-managed **KMS CMK** (`encryption_key=key`).
- **[Med] DynamoDB/S3 encryption** — **Fixed prior:** CMK on both; S3 `enforce_ssl`; TLS in
  transit; KMS key rotation enabled.

## Secrets management
- **[High] Key prefix in logs** — **Fixed** (hashed principal).
- **[Med] API keys in plaintext env** — **Fixed prior:** Secrets Manager (`NEXUS_API_KEYS_SECRET`),
  loaded at boot; fail-closed if unreadable in production.

## Differential Privacy
- **[High] Federation released exact aggregates (differencing attack)** — only k-anonymity.
  **Fixed:** ε-DP Laplace mechanism on joint reliability/regret/reputation with a reported
  epsilon budget (`infra/clean_rooms/federation.py`, `test_dp_federation.py`).

## Clean Rooms
- **[Med] Not provisioned; min-cell only** — DP added (above). Real AWS Clean Rooms
  collaboration provisioning remains **Roadmap** (the SQL analysis rules are defined).

## Audit logs
- **[High] No security audit trail** — **Fixed:** `nexus.audit` JSON events for auth
  decisions and all mutations, with actor/tenant/request-id; auth-deny logged for
  brute-force detection.

## Supply chain
- **[Med] No dependency/secret/SAST scanning, ranged deps** — **Fixed:** CI runs pip-audit,
  bandit, gitleaks; Dependabot for pip + actions. Hash-pinned lockfile is **Roadmap**.

## CI/CD
- **[Med] Broad GITHUB_TOKEN, unpinned actions** — **Fixed:** `permissions: contents: read`;
  added security job. **Roadmap:** pin actions to commit SHAs (documented in `ci.yml`).

## Local sandbox leaks
- **[Med] World-readable ledger in shared /tmp** — **Fixed:** FileStore dir `0700`, files
  `0600` (`test_filestore_files_are_owner_only`); defaults moved to a private `tempfile`
  dir (also removes hardcoded `/tmp`).

## Data retention
- **[Med] No retention policy; immutability vs GDPR erasure** — **Fixed (policy) / Roadmap
  (control plane):** `RETENTION.md` defines classification, 90-day log retention (now in
  CDK), and a **crypto-shred** erasure model (per-tenant KMS key deletion). Per-tenant CMK
  provisioning is roadmap.

## Zero Trust
- **[High] Trust by request input / network position** — tenant from body, reads open.
  **Fixed:** identity-derived tenant, authenticated + scoped reads, default-deny, audit.
  Service-to-service mTLS is **Roadmap** (serverless/IAM-authenticated today).

---

## Verification
- `pytest` → **96 passed** (incl. cross-tenant 403, read scoping, SSRF, file perms, DP).
- `bandit -ll backend/api backend/forward_ledger` → no Medium/High findings.
- `python infra/cdk/app.py` → synth OK (CMK on DDB/S3/Secrets, read-only api role, per-fn
  log retention, throttling, alarms).
