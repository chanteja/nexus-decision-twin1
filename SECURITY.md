# Security

## Posture
- **Authentication.** Every mutating endpoint (`/v1/decide`, `/v1/commit`, `/v1/prove`,
  `/v1/anchor`, `/v1/demo/*`) requires an API key (`Authorization: Bearer <key>` or
  `X-API-Key`), constant-time compared. Keys come from `NEXUS_API_KEYS` (local) or AWS
  Secrets Manager (`NEXUS_API_KEYS_SECRET`, production).
- **Fail closed.** With `NEXUS_ENV=production`, the service refuses to boot without
  configured keys or with wildcard CORS.
- **Input validation.** Branch counts, text lengths, probability ranges, and tenant slugs
  are bounded at the edge (`backend/api/app.py` schemas).
- **Tenant isolation.** Each tenant has its own ledger partition; no read crosses a tenant
  boundary (`forward_ledger/dynamo_store.py`, `get_ledger`).
- **Integrity.** Decisions are hash-chained; outcomes are bound to the seal via a settlement
  hash, so a flipped outcome is detected by `Ledger.verify()`. The Merkle root and settlement
  root are externally anchored (OpenTimestamps) and mirrored to S3 Object Lock (WORM).
- **Encryption.** Customer-managed KMS key for DynamoDB and S3; TLS enforced in transit.
- **Least privilege.** Separate IAM role per Lambda; Bedrock scoped to foundation-model ARNs.
- **Observability.** Structured JSON logs with per-request correlation ids; CloudWatch error
  alarms per function.

## Configuration (environment)
| Variable | Purpose | Default |
|---|---|---|
| `NEXUS_ENV` | `demo` / `production` (production fails closed) | `demo` |
| `NEXUS_API_KEYS` | comma-separated keys (local) | empty |
| `NEXUS_API_KEYS_SECRET` | Secrets Manager ARN (production) | unset |
| `NEXUS_CORS_ORIGINS` | comma-separated allowlist | localhost |
| `NEXUS_DDB_TABLE` | DynamoDB table → DynamoDBStore | unset → FileStore |
| `NEXUS_TENANT` | default tenant for the product surface | `demo_corp` |

## Reporting
Email security@nexus.example with details and a reproduction. Do not open public issues for
vulnerabilities.
