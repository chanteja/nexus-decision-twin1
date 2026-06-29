# backend/forward_ledger/store.py
"""
Storage is swappable infrastructure; the chain is the asset.

  * FileStore       — durable JSON-lines, zero dependencies, runs anywhere. Default
                      for local + the offline demo.
  * DynamoDBStore   — AWS DynamoDB adapter (see dynamo_store.py). Durable, horizontally
                      scalable, PITR-enabled, tenant-partitioned. The verifiability lives
                      in the hash chain + external anchor, not in the store, so any
                      durable store works; DynamoDB is the production default.

All satisfy the same interface, so the API never knows which is mounted. Use
``build_store()`` to select one from the environment.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
from typing import Protocol


class SequenceConflict(Exception):
    """Raised by a store when another writer already claimed this sequence number —
    the optimistic-locking signal that the ledger must re-sync its tail and retry."""


class LedgerStore(Protocol):
    def load(self) -> list[dict]: ...
    def append(self, entry: dict) -> None: ...
    def update(self, entry: dict) -> None: ...
    def append_cf(self, rows: list[dict]) -> None: ...   # L2 counterfactual corpus
    def load_cf(self) -> list[dict]: ...
    def append_asm(self, rows: list[dict]) -> None: ...   # assumption ledger (causal corpus)
    def load_asm(self) -> list[dict]: ...


class FileStore:
    """Append-only JSON-lines on disk. update() rewrites in place (resolution is a
    separate event from the immutable seal, so rewriting the resolution fields does
    not alter any hashed core — Ledger.verify() still passes)."""

    def __init__(self, path: str):
        self.path = path
        self.cf_path = path + ".cf"          # sibling append-only counterfactual log
        self.asm_path = path + ".asm"        # sibling append-only assumption ledger
        self.ckpt_path = path + ".ckpt"      # integrity checkpoint (head + merkle root)
        self._lock = threading.Lock()
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
        with contextlib.suppress(OSError):
            os.chmod(d, 0o700)  # private dir — the local record is not world-readable
        for fp in (path, self.cf_path, self.asm_path):
            if not os.path.exists(fp):
                # create with 0600 so the ledger is owner-only from the first byte
                os.close(os.open(fp, os.O_CREAT | os.O_WRONLY, 0o600))
            else:
                with contextlib.suppress(OSError):
                    os.chmod(fp, 0o600)

    def load(self) -> list[dict]:
        out: list[dict] = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        out.sort(key=lambda e: e["seq"])
        return out

    def append(self, entry: dict) -> None:
        with self._lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def update(self, entry: dict) -> None:
        with self._lock:
            rows = self.load()
            for i, r in enumerate(rows):
                if r["id"] == entry["id"]:
                    rows[i] = entry
                    break
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            os.replace(tmp, self.path)

    def append_cf(self, rows: list[dict]) -> None:
        with self._lock, open(self.cf_path, "a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def load_cf(self) -> list[dict]:
        out: list[dict] = []
        with open(self.cf_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def append_asm(self, rows: list[dict]) -> None:
        with self._lock, open(self.asm_path, "a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def load_asm(self) -> list[dict]:
        out: list[dict] = []
        with open(self.asm_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out


class MemoryStore:
    """For tests."""
    def __init__(self) -> None:
        self._rows: list[dict] = []
        self._cf: list[dict] = []
        self._asm: list[dict] = []
        self._checkpoint: dict | None = None

    def tail(self) -> dict | None:
        rows = sorted(self._rows, key=lambda e: e["seq"])
        return dict(rows[-1]) if rows else None

    def count(self) -> int:
        return len(self._rows)

    def save_checkpoint(self, cp: dict) -> None:
        self._checkpoint = dict(cp)

    def load_checkpoint(self) -> dict | None:
        return dict(self._checkpoint) if self._checkpoint else None

    def load(self) -> list[dict]:
        return [dict(r) for r in sorted(self._rows, key=lambda e: e["seq"])]

    def append(self, entry: dict) -> None:
        self._rows.append(dict(entry))

    def update(self, entry: dict) -> None:
        for i, r in enumerate(self._rows):
            if r["id"] == entry["id"]:
                self._rows[i] = dict(entry)
                return

    def append_cf(self, rows: list[dict]) -> None:
        self._cf.extend(dict(r) for r in rows)

    def load_cf(self) -> list[dict]:
        return [dict(r) for r in self._cf]

    def append_asm(self, rows: list[dict]) -> None:
        self._asm.extend(dict(r) for r in rows)

    def load_asm(self) -> list[dict]:
        return [dict(r) for r in self._asm]


def build_store(tenant: str = "default", path: str | None = None):
    """Select the durable store from the environment.

    ``NEXUS_DDB_TABLE`` set  -> DynamoDBStore (production, tenant-scoped).
    otherwise                -> FileStore (local + offline demo).
    The product contract is identical across both, so callers never branch on it.
    """
    table = os.environ.get("NEXUS_DDB_TABLE")
    if table:
        from .dynamo_store import DynamoDBStore
        return DynamoDBStore(table_name=table, tenant=tenant)
    if os.environ.get("NEXUS_SQL_PATH"):
        from .sql_store import SqliteStore
        return SqliteStore(tenant=tenant)
    base = path or os.environ.get("NEXUS_LEDGER_PATH", default_path("ledger.jsonl"))
    # local/file multi-tenancy: the default tenant keeps the base file (so the seeded demo
    # lives there); every other tenant gets an isolated sibling file.
    if path is None and tenant and tenant != os.environ.get("NEXUS_TENANT", "demo_corp"):
        base = f"{base}.{tenant}"
    return FileStore(base)


def valid_tenant(t: str) -> bool:
    """A tenant id is a short, key-safe slug — prevents partition-key injection."""
    return bool(t) and len(t) <= 64 and all(c.isalnum() or c in "-_" for c in t)


def default_path(name: str) -> str:
    """A private, OS-appropriate default location for the local record (honours TMPDIR).
    Production uses DynamoDB; this is only the zero-infra local/demo store."""
    return os.path.join(tempfile.gettempdir(), "nexus", name)


def register_tenant(store) -> None:
    """Register a tenant in the durable store, if the backend supports it (idempotent)."""
    fn = getattr(store, "register_tenant", None)
    if fn:
        with contextlib.suppress(Exception):
            fn()


def list_tenants() -> list[str]:
    """Every tenant the autonomous loop must process. DynamoDB enumerates its registry;
    local/file backends use NEXUS_TENANTS (comma-separated) or the default tenant."""
    table = os.environ.get("NEXUS_DDB_TABLE")
    if table:
        try:
            from .dynamo_store import list_registered_tenants
            tenants = list_registered_tenants(table)
            if tenants:
                return tenants
        except Exception:
            pass
    env = [t.strip() for t in os.environ.get("NEXUS_TENANTS", "").split(",") if t.strip()]
    return env or [os.environ.get("NEXUS_TENANT", "demo_corp")]
