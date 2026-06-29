# backend/forward_ledger/sql_store.py
"""
Portable SQL store — proof the chain is NOT locked to AWS.

The whole value of NEXUS is the application-level hash chain + external anchor, which run
on ANY durable store. This SQLite-backed adapter (stdlib only, zero dependencies) satisfies
the same ``LedgerStore`` contract as FileStore and DynamoDBStore, and works against any
SQL backend with trivial DDL changes (Postgres/Aurora/Cloud SQL). It is the structural
answer to a cloud incumbent commoditising "AWS-native" apps: NEXUS is cloud-portable by
construction. Tenant-scoped like the DynamoDB store.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading

from .store import valid_tenant


class SqliteStore:
    def __init__(self, path: str | None = None, tenant: str = "default"):
        self.path = path or os.environ.get(
            "NEXUS_SQL_PATH", os.path.join(tempfile.gettempdir(), "nexus", "ledger.db"))
        if not valid_tenant(tenant):
            raise ValueError(f"invalid tenant id: {tenant!r}")
        self.tenant = tenant
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self) -> None:
        with self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS entries("
                "tenant TEXT, seq INTEGER, id TEXT, body TEXT, PRIMARY KEY(tenant, seq))")
            self._db.execute("CREATE TABLE IF NOT EXISTS cf(tenant TEXT, n INTEGER, body TEXT)")
            self._db.execute("CREATE TABLE IF NOT EXISTS asm(tenant TEXT, n INTEGER, body TEXT)")
            self._db.execute("CREATE TABLE IF NOT EXISTS meta(tenant TEXT PRIMARY KEY, body TEXT)")

    # ── entries ───────────────────────────────────────────────────────────
    def load(self) -> list[dict]:
        cur = self._db.execute(
            "SELECT body FROM entries WHERE tenant=? ORDER BY seq", (self.tenant,))
        return [json.loads(r[0]) for r in cur.fetchall()]

    def append(self, entry: dict) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO entries(tenant, seq, id, body) VALUES(?,?,?,?)",
                (self.tenant, int(entry["seq"]), entry["id"],
                 json.dumps(entry, ensure_ascii=False)))

    def update(self, entry: dict) -> None:
        # resolution overwrites the same (tenant, seq) row; the hashed core is unchanged
        self.append(entry)

    def tail(self) -> dict | None:
        cur = self._db.execute(
            "SELECT body FROM entries WHERE tenant=? ORDER BY seq DESC LIMIT 1", (self.tenant,))
        row = cur.fetchone()
        return json.loads(row[0]) if row else None

    def count(self) -> int:
        cur = self._db.execute("SELECT COUNT(*) FROM entries WHERE tenant=?", (self.tenant,))
        return int(cur.fetchone()[0])

    def save_checkpoint(self, cp: dict) -> None:
        with self._lock, self._db:
            self._db.execute("INSERT OR REPLACE INTO meta(tenant, body) VALUES(?,?)",
                             (self.tenant, json.dumps(cp, ensure_ascii=False)))

    def load_checkpoint(self) -> dict | None:
        cur = self._db.execute("SELECT body FROM meta WHERE tenant=?", (self.tenant,))
        row = cur.fetchone()
        return json.loads(row[0]) if row else None

    # ── sibling append-only logs ──────────────────────────────────────────
    def append_cf(self, rows: list[dict]) -> None:
        self._append_rows("cf", rows)

    def load_cf(self) -> list[dict]:
        return self._load_rows("cf")

    def append_asm(self, rows: list[dict]) -> None:
        self._append_rows("asm", rows)

    def load_asm(self) -> list[dict]:
        return self._load_rows("asm")

    # Fixed statements keyed by a closed table set — no user input ever reaches SQL text.
    _INSERT = {"cf": "INSERT INTO cf(tenant, n, body) VALUES(?,?,?)",
               "asm": "INSERT INTO asm(tenant, n, body) VALUES(?,?,?)"}
    _SELECT = {"cf": "SELECT body FROM cf WHERE tenant=? ORDER BY rowid",
               "asm": "SELECT body FROM asm WHERE tenant=? ORDER BY rowid"}

    def _append_rows(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._db:
            self._db.executemany(
                self._INSERT[table],
                [(self.tenant, i, json.dumps(r, ensure_ascii=False)) for i, r in enumerate(rows)])

    def _load_rows(self, table: str) -> list[dict]:
        cur = self._db.execute(self._SELECT[table], (self.tenant,))
        return [json.loads(r[0]) for r in cur.fetchall()]
