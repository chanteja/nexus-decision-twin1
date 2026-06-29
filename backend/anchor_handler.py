# Lambda entrypoint for the daily EXTERNAL ANCHOR (EventBridge cron), all tenants.
# Publishes each tenant's Merkle root to OpenTimestamps and mirrors the anchor record to
# an S3 Object Lock (WORM) bucket — neither of which NEXUS can rewrite after the fact,
# making "sealed before the outcome" verifiable by a stranger who does not trust us.
import datetime as _dt
import json
import os
import tempfile

from forward_ledger import AnchorLog, Ledger, anchor, build_store, list_tenants


def _anchor_path(tenant: str) -> str:
    base = os.environ.get("NEXUS_ANCHOR_PATH",
                          os.path.join(tempfile.gettempdir(), "nexus", "anchor.jsonl"))
    return f"{base}.{tenant}"


def _mirror_to_s3_worm(tenant: str, record: dict) -> dict | None:
    """Write the anchor record to an S3 Object Lock bucket (compliance mode), keyed per
    tenant. The object cannot be overwritten or deleted for the retention period, so the
    seal time cannot be backdated even by us. No-op if the bucket isn't configured."""
    bucket = os.environ.get("ANCHOR_BUCKET")
    if not bucket:
        return None
    try:
        import boto3
        s3 = boto3.client("s3")
        ts = int(record["anchored_at"])
        key = f"anchors/{tenant}/{ts}-{record['merkle_root'][:16]}.json"
        retain_until = _dt.datetime.fromtimestamp(
            record["anchored_at"] + 86400 * 3650, tz=_dt.UTC)  # 10-year WORM
        s3.put_object(
            Bucket=bucket, Key=key,
            Body=json.dumps(record, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=retain_until)
        return {"bucket": bucket, "key": key, "object_lock": "COMPLIANCE"}
    except Exception as ex:   # never block the anchor on a mirror failure
        return {"error": str(ex)}


def handler(event, context):
    results = []
    for tenant in list_tenants():
        try:
            lg = Ledger(build_store(tenant=tenant))
            record = anchor(lg, AnchorLog(_anchor_path(tenant)))["anchored"]
            results.append({"tenant": tenant, "merkle_root": record["merkle_root"],
                            "ots_status": record["ots_status"],
                            "s3_worm": _mirror_to_s3_worm(tenant, record),
                            "anchored_at": record["anchored_at"]})
        except Exception as ex:
            results.append({"tenant": tenant, "error": str(ex)})
    return {"tenants": len(results), "results": results}
