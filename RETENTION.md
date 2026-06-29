# Data Retention & Erasure

## Classification
| Data | Store | Encryption | Retention |
|---|---|---|---|
| Decision records (hash chain) | DynamoDB (`DynamoDBStore`) | KMS CMK + TLS | Indefinite (immutable record) |
| Anchor evidence | S3 Object Lock (WORM) | KMS CMK | 10 years (COMPLIANCE) |
| API keys | Secrets Manager | KMS CMK | Lifecycle-managed; rotate ≤90d |
| Application logs | CloudWatch | AWS-managed | 90 days |
| API access logs | CloudWatch | AWS-managed | 30 days |

## The immutability ↔ erasure tension (GDPR Art. 17)
The decision chain is intentionally immutable, which conflicts with a right-to-erasure
request. NEXUS reconciles this with **crypto-shredding** rather than mutating the chain:

- Each tenant's data is encrypted under a **per-tenant KMS data key** (tenant-scoped
  partition + tenant key). The hash chain stores ciphertext-derived records; the chain's
  integrity proof (hashes, Merkle/settlement roots) is preserved.
- To honour an erasure request, the tenant's data key is **scheduled for deletion**. The
  ciphertext remains in the immutable store but is unrecoverable, so the personal data is
  effectively erased while the tamper-evident structure and external anchors stay intact.
- Audit logs record the erasure action (actor, tenant, timestamp) without the erased data.

## Operational retention
- DynamoDB **PITR** (35-day window) for recovery; cross-region backup is a roadmap item.
- S3 Object Lock retention is **irreversible** (COMPLIANCE) — provision deliberately; the
  anchor objects contain only Merkle roots and metadata, never personal data, by design.
- Log retention is set explicitly in the CDK stack (no never-expire groups).

## Not yet implemented (roadmap)
- Per-tenant CMK provisioning + the crypto-shred control plane (the model above is the
  target architecture; the current stack uses one shared CMK).
- Automated DSAR (data-subject access request) export tooling.
