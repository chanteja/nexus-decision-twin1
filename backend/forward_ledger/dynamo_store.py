# backend/forward_ledger/dynamo_store.py
"""
DynamoDB durable store — the production LedgerStore.

The hash-chain logic (ledger.py) is the asset; the store is swappable infrastructure.
This adapter satisfies the same ``LedgerStore`` Protocol as ``FileStore`` (entries +
the counterfactual and assumption sibling logs), so the API never knows which is
mounted. It is tenant-scoped: every item is partitioned under the owning tenant, so
one table isolates many tenants without cross-tenant reads.

Why DynamoDB (not a managed ledger DB): Amazon QLDB was retired on 2025-07-31, so
verifiability does NOT depend on a managed journal. It lives in the application-level
hash chain + Merkle root, externally anchored to OpenTimestamps and mirrored to S3
Object Lock (WORM). DynamoDB supplies a durable, horizontally-scalable, point-in-time-
recoverable store for that chain and the Decision Graph metadata.

Schema (single table, composite key ``pk``/``sk``):
    pk = "T#{tenant}#LEDGER"   sk = "E#{seq:012d}"   one item per sealed entry
    pk = "T#{tenant}#CF"       sk = "{uuid}"          counterfactual rows (append-only)
    pk = "T#{tenant}#ASM"      sk = "{uuid}"          assumption-ledger rows (append-only)
Each item stores the record as a JSON string in ``body`` (avoids float/Decimal
coercion) plus a few projected attributes for operability.

boto3 is imported lazily so the rest of the system runs with zero AWS dependency.
Mount this store only when ``NEXUS_DDB_TABLE`` is set; otherwise ``FileStore`` is used.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any

from botocore.exceptions import ClientError

from .store import SequenceConflict, valid_tenant


class DynamoDBStore:
    def __init__(self, table_name: str | None = None, tenant: str = "default",
                 region: str | None = None):
        self.table_name = table_name or os.environ["NEXUS_DDB_TABLE"]
        if not valid_tenant(tenant):
            raise ValueError(f"invalid tenant id: {tenant!r}")
        self.tenant = tenant
        import boto3  # lazy
        self._ddb = boto3.resource(
            "dynamodb", region_name=region or os.environ.get("AWS_REGION", "us-east-1"))
        self._table = self._ddb.Table(self.table_name)

    def register_tenant(self) -> None:
        """Record this tenant in the registry so the autonomous loop can enumerate it."""
        self._table.put_item(Item={"pk": "REGISTRY", "sk": f"T#{self.tenant}",
                                   "tenant": self.tenant})

    # ── key helpers ───────────────────────────────────────────────────────
    def _pk(self, suffix: str) -> str:
        return f"T#{self.tenant}#{suffix}"

    # ── entries ───────────────────────────────────────────────────────────
    def load(self) -> list[dict]:
        rows = self._query_all(self._pk("LEDGER"))
        out = [json.loads(r["body"]) for r in rows]
        out.sort(key=lambda e: e["seq"])
        return out

    def append(self, entry: dict) -> None:
        # Append-only under concurrency: the write succeeds ONLY if no item already
        # holds this (tenant, seq). Two Lambdas racing on the same seq -> the second
        # gets ConditionalCheckFailedException, surfaced as SequenceConflict so the
        # ledger re-syncs its tail and retries at the next seq. No silent overwrite.
        try:
            self._table.put_item(
                Item=self._entry_item(entry),
                ConditionExpression="attribute_not_exists(sk)")
        except ClientError as ex:
            if ex.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise SequenceConflict(f"seq {entry['seq']} already sealed") from ex
            raise

    def update(self, entry: dict) -> None:
        # resolution is a put on the SAME pk/sk (keyed by seq), so it overwrites the
        # mutable resolution fields in place; the hashed core is unchanged by ledger.py.
        self._table.put_item(Item=self._entry_item(entry))

    def _entry_item(self, entry: dict) -> dict:
        return {
            "pk": self._pk("LEDGER"),
            "sk": f"E#{int(entry['seq']):012d}",
            "id": entry["id"],
            "status": entry.get("status", "pending"),
            "tenant": self.tenant,
            "body": json.dumps(entry, ensure_ascii=False, separators=(",", ":")),
        }

    # ── counterfactual sibling log (append-only) ──────────────────────────
    def tail(self) -> dict | None:
        """The highest-seq entry, read cheaply (descending, limit 1) — lets the ledger
        learn the current head without loading the whole chain."""
        from boto3.dynamodb.conditions import Key
        resp = self._table.query(
            KeyConditionExpression=Key("pk").eq(self._pk("LEDGER"))
            & Key("sk").begins_with("E#"),
            ScanIndexForward=False, Limit=1)
        items = resp.get("Items", [])
        return json.loads(items[0]["body"]) if items else None

    def count(self) -> int:
        from boto3.dynamodb.conditions import Key
        resp = self._table.query(
            KeyConditionExpression=Key("pk").eq(self._pk("LEDGER")) & Key("sk").begins_with("E#"),
            Select="COUNT")
        return int(resp.get("Count", 0))

    def save_checkpoint(self, cp: dict) -> None:
        self._table.put_item(Item={"pk": self._pk("META"), "sk": "CHECKPOINT",
                                   "tenant": self.tenant,
                                   "body": json.dumps(cp, ensure_ascii=False)})

    def load_checkpoint(self) -> dict | None:
        resp = self._table.get_item(Key={"pk": self._pk("META"), "sk": "CHECKPOINT"})
        item = resp.get("Item")
        return json.loads(item["body"]) if item else None

    def append_cf(self, rows: list[dict]) -> None:
        self._batch_put(self._pk("CF"), rows)

    def load_cf(self) -> list[dict]:
        return [json.loads(r["body"]) for r in self._query_all(self._pk("CF"))]

    # ── assumption-ledger sibling log (append-only) ───────────────────────
    def append_asm(self, rows: list[dict]) -> None:
        self._batch_put(self._pk("ASM"), rows)

    def load_asm(self) -> list[dict]:
        return [json.loads(r["body"]) for r in self._query_all(self._pk("ASM"))]

    # ── internals ─────────────────────────────────────────────────────────
    def _batch_put(self, pk: str, rows: list[dict]) -> None:
        if not rows:
            return
        with self._table.batch_writer() as bw:
            for r in rows:
                bw.put_item(Item={
                    "pk": pk,
                    "sk": uuid.uuid4().hex,
                    "tenant": self.tenant,
                    "body": json.dumps(r, ensure_ascii=False, separators=(",", ":")),
                })

    def _query_all(self, pk: str) -> list[dict[str, Any]]:
        from boto3.dynamodb.conditions import Key
        items: list[dict] = []
        kwargs = {"KeyConditionExpression": Key("pk").eq(pk)}
        while True:
            resp = self._table.query(**kwargs)
            items.extend(resp.get("Items", []))
            lek = resp.get("LastEvaluatedKey")
            if not lek:
                return items
            kwargs["ExclusiveStartKey"] = lek


def list_registered_tenants(table_name: str, region: str | None = None) -> list[str]:
    """All tenants that have ever written to this table (for autonomous per-tenant jobs)."""
    import boto3
    from boto3.dynamodb.conditions import Key
    table = boto3.resource("dynamodb",
                           region_name=region or os.environ.get("AWS_REGION", "us-east-1")).Table(table_name)
    out, kwargs = [], {"KeyConditionExpression": Key("pk").eq("REGISTRY")}
    while True:
        resp = table.query(**kwargs)
        out.extend(i["tenant"] for i in resp.get("Items", []))
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            return sorted(set(out))
        kwargs["ExclusiveStartKey"] = lek
