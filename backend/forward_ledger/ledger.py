# backend/forward_ledger/ledger.py
"""
The Forward Ledger — the one asset competitors cannot backfill.

A prediction becomes credible only if it can be proven to have existed *before*
its outcome did. This module implements an append-only, hash-chained log whose
integrity is independently verifiable by a stranger:

  * each entry carries the hash of the previous entry (a chain — any edit to an
    older entry breaks every hash after it),
  * the whole journal hashes to a Merkle root that can be published to a public
    anchor (OpenTimestamps / a blockchain / a dated tweet) so the seal time is
    not merely asserted by us,
  * entries are sealed at creation (status PENDING) and resolved later by an
    external oracle the predictor does not control (status RESOLVED). The seal
    time always precedes the resolution time — that ordering is the entire point.

No fabricated foresight: a freshly seeded ledger has *pending* predictions and an
honest, possibly-zero resolved accuracy. The clock starts the day this runs.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from .store import SequenceConflict

if TYPE_CHECKING:
    from .store import LedgerStore

GENESIS = "0" * 64
MAX_APPEND_RETRIES = 8   # optimistic-locking retries under concurrent writers


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(obj: Any) -> bytes:
    """Deterministic JSON used for every hash — key order fixed, no whitespace drift."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class Status(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"


class Kind(str, Enum):
    FORWARD = "forward"     # sealed before its outcome exists — the real test
    BACKTEST = "backtest"   # historical, hindsight, labeled as such — context only, never the headline


@dataclass
class Prediction:
    """The sealed content of an entry. Hashed verbatim into the chain."""
    decision: str
    branches: list[str]                 # the futures considered (named)
    weights: list[float]                # per-branch survival probability (sums ~1)
    survivor: int                       # argmax branch index
    confidence: float                   # survivor survival probability, 0..1
    why: str
    watch: str
    author: str = "anon"
    domain: str = "general"
    model: str = "nexus-local-ensemble"
    kind: Kind = Kind.FORWARD
    resolves_at: float = 0.0            # unix seconds; when the oracle can settle it
    oracle: str = "seed"               # which oracle settles this (polymarket/financial/seed/...)
    oracle_ref: str = ""               # the oracle's id for this question
    # Named assumptions the survivor branch depends on — sealed into the hashed core
    # alongside the prediction, so the claim "this is what we were betting on" is
    # itself timestamped before the outcome. Each is ideally independently resolvable
    # (an oracle_ref of its own); the Assumption Ledger scores the ones that recur in
    # failures — the only causal signal we can hold honestly (assumptions.py).
    assumptions: list[str] = field(default_factory=list)
    # The Decision Graph (initiative) this decision belongs to. Decisions that share a
    # graph_id are the same connected strategy; Decision Memory reuses an existing graph_id
    # for a related initiative instead of creating an isolated graph. Empty = ungraphed.
    graph_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d


@dataclass
class Entry:
    seq: int
    id: str
    prediction: dict
    created_at: float
    prev_hash: str
    hash: str
    status: str = Status.PENDING.value
    survived: bool | None = None     # ground truth, set only at resolution
    resolved_at: float | None = None
    resolution_ref: str = ""            # the oracle evidence (url/id) that settled it
    # sha256 of the oracle evidence payload, recorded at resolution. Lets a stranger
    # re-derive that we settled on real external evidence, not our say-so — closes the
    # last "trust us" gap in settlement. Stored OUTSIDE core(), so verify() is untouched.
    resolution_evidence_hash: str = ""
    # Binds the (mutable) outcome to the immutable sealed core. Recomputed in verify()
    # so a flipped `survived` or backdated `resolved_at` in the store is DETECTED — the
    # gap that previously let outcomes be edited without breaking the chain.
    settlement_hash: str = ""

    def settlement_core(self) -> dict:
        """The settlement event bound to this entry's immutable seal hash."""
        return {
            "entry_hash": self.hash,
            "survived": self.survived,
            "resolved_at": self.resolved_at,
            "resolution_ref": self.resolution_ref,
            "resolution_evidence_hash": self.resolution_evidence_hash,
        }

    def compute_settlement_hash(self) -> str:
        return _sha256(canonical(self.settlement_core()))

    def core(self) -> dict:
        """The immutable, hashed core. Resolution fields are appended as a separate
        signed event and never mutate this — the seal stays byte-stable forever."""
        return {
            "seq": self.seq,
            "id": self.id,
            "prediction": self.prediction,
            "created_at": self.created_at,
            "prev_hash": self.prev_hash,
        }

    def compute_hash(self) -> str:
        return _sha256(canonical(self.core()))


class TamperError(Exception):
    pass


class Ledger:
    """In-memory chain with a pluggable durable store. The chain logic is the
    asset; the store (file / DynamoDB) is swappable infrastructure."""

    def __init__(self, store: LedgerStore, verify_full: bool | None = None):
        self.store = store
        self._entries: list[Entry] = [Entry(**e) for e in store.load()]
        self._roots_dirty: bool = True
        self._merkle: str | None = None
        self._settle: str | None = None
        self._valid: bool = True
        self._valid_checked_at: float = 0.0
        # Cold-start cost control: when a checkpoint exists, re-hash only the suffix after
        # the externally-anchored checkpoint instead of the whole chain. Opt-in (production
        # sets NEXUS_INCREMENTAL_VERIFY=1); default stays full verify. The periodic anchor
        # job performs the deep, full Merkle re-check against the published root.
        if verify_full is None:
            verify_full = os.environ.get("NEXUS_INCREMENTAL_VERIFY") != "1"
        if self._entries:
            self.verify() if verify_full else self._verify_incremental()

    def _verify_incremental(self) -> bool:
        load_cp = getattr(self.store, "load_checkpoint", None)
        cp = load_cp() if load_cp else None
        n = len(self._entries)
        if not cp or cp.get("count", 0) <= 0 or cp["count"] > n \
                or self._entries[cp["count"] - 1].hash != cp.get("head_hash"):
            return self.verify()      # no usable checkpoint / prefix changed -> full check
        start = cp["count"]           # entries [0, start) are attested by the anchored checkpoint
        prev = cp["head_hash"]
        for i in range(start, n):
            e = self._entries[i]
            if e.seq != i:
                raise TamperError(f"seq gap at {i}")
            if e.prev_hash != prev:
                raise TamperError(f"broken link at seq {e.seq}")
            if e.compute_hash() != e.hash:
                raise TamperError(f"hash mismatch at seq {e.seq}")
            if e.settlement_hash and e.compute_settlement_hash() != e.settlement_hash:
                raise TamperError(f"settlement altered at seq {e.seq}")
            prev = e.hash
        return True

    def checkpoint(self) -> dict:
        """Persist an integrity checkpoint (head + Merkle root) so future cold starts can
        verify incrementally. Called by the anchor job, whose published root is the deep
        external guarantee over the attested prefix."""
        self._refresh_roots()
        last = self._entries[-1] if self._entries else None
        cp = {"count": len(self._entries),
              "head_seq": last.seq if last else -1,
              "head_hash": last.hash if last else GENESIS,
              "merkle_root": self._merkle, "at": time.time()}
        save = getattr(self.store, "save_checkpoint", None)
        if save:
            save(cp)
        return cp

    # ── append ────────────────────────────────────────────────────────────
    def append(self, pred: Prediction, created_at: float | None = None) -> Entry:
        """Append a sealed entry. Under concurrent writers the store rejects a duplicate
        sequence (SequenceConflict); we re-sync the tail and retry at the next seq, so the
        chain stays append-only and unbroken without a global lock. The seal time is fixed
        before the loop so retries don't move it."""
        cat = created_at if created_at is not None else time.time()
        pid = pred.to_dict()
        last_err: Exception | None = None
        for _ in range(MAX_APPEND_RETRIES):
            seq = len(self._entries)
            prev = self._entries[-1].hash if self._entries else GENESIS
            e = Entry(seq=seq, id=uuid.uuid4().hex, prediction=pid, created_at=cat,
                      prev_hash=prev, hash="")
            e.hash = e.compute_hash()
            try:
                self.store.append(asdict(e))
            except SequenceConflict as ex:
                last_err = ex
                self._resync()          # another writer won this seq; reload + retry
                continue
            self._entries.append(e)
            self._roots_dirty = True
            return e
        raise SequenceConflict(
            f"append failed after {MAX_APPEND_RETRIES} retries under contention") from last_err

    def _resync(self) -> None:
        """Reload the chain from the durable store (the source of truth) and re-verify —
        used to recover the true tail after a concurrent-write conflict."""
        self._entries = [Entry(**e) for e in self.store.load()]
        self._roots_dirty = True
        self._valid = True
        if self._entries:
            self.verify()

    # ── resolve ───────────────────────────────────────────────────────────
    def resolve(self, entry_id: str, survived: bool, ref: str, at: float | None = None) -> Entry:
        e = self.by_id(entry_id)
        if e is None:
            raise KeyError(entry_id)
        if e.status == Status.RESOLVED.value:
            return e  # idempotent
        at = at if at is not None else time.time()
        if at < e.created_at:
            # the ordering invariant — resolution can never precede the seal
            raise TamperError(f"resolution {at} precedes seal {e.created_at} for {entry_id}")
        e.status = Status.RESOLVED.value
        e.survived = survived
        e.resolved_at = at
        e.resolution_ref = ref
        e.resolution_evidence_hash = _sha256(ref.encode("utf-8")) if ref else ""
        e.settlement_hash = e.compute_settlement_hash()
        self._roots_dirty = True
        self.store.update(asdict(e))
        self._emit_counterfactuals(e)   # L2 — score the roads not taken
        self._emit_assumptions(e)       # the assumption ledger — the honest causal signal
        return e

    def _emit_counterfactuals(self, e: Entry) -> None:
        """At resolution, score the full branch vector into the counterfactual
        corpus. This is a SEPARATE append-only event — it never touches the hashed
        core, so verify() still passes — and it only forms if persisted from the
        first sealed call, which is the moat. Import is local to avoid a cycle."""
        from .counterfactual import counterfactual_rows
        rows = counterfactual_rows(e)
        if rows:
            self.store.append_cf(rows)

    def counterfactual_rows(self) -> list[dict]:
        """All persisted counterfactual rows (read surface for the corpus)."""
        return self.store.load_cf()

    def _emit_assumptions(self, e: Entry) -> None:
        """At resolution, score each sealed assumption into the Assumption Ledger.
        Like the counterfactual corpus this is a SEPARATE append-only event, so the
        hashed core is untouched and verify() still passes. An assumption only carries
        a learning signal when the bet it underwrote FAILED — those are the beliefs
        reality keeps falsifying. Import is local to avoid a cycle."""
        from .assumptions import assumption_rows
        rows = assumption_rows(e)
        if rows:
            self.store.append_asm(rows)

    def assumption_rows(self) -> list[dict]:
        """All persisted assumption-ledger rows (read surface for the causal corpus)."""
        return self.store.load_asm()

    # ── integrity ─────────────────────────────────────────────────────────
    def verify(self) -> bool:
        """Recompute the whole chain. Any edit to any sealed core breaks here."""
        prev = GENESIS
        for i, e in enumerate(self._entries):
            if e.seq != i:
                raise TamperError(f"seq gap at {i}")
            if e.prev_hash != prev:
                raise TamperError(f"broken link at seq {e.seq}")
            if e.compute_hash() != e.hash:
                raise TamperError(f"hash mismatch at seq {e.seq} — entry was altered after sealing")
            if e.settlement_hash and e.compute_settlement_hash() != e.settlement_hash:
                raise TamperError(f"settlement altered at seq {e.seq} — outcome edited after settlement")
            prev = e.hash
        return True

    @staticmethod
    def _merkle_of(leaves: list[bytes]) -> str:
        if not leaves:
            return GENESIS
        level = leaves
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                     for i in range(0, len(level), 2)]
        return level[0].hex()

    def _refresh_roots(self) -> None:
        """Recompute the (O(n)) Merkle + settlement roots only when the chain changed —
        not on every read. This is what makes read endpoints O(1) amortised at scale."""
        if self._roots_dirty or self._merkle is None:
            self._merkle = self._merkle_of([bytes.fromhex(e.hash) for e in self._entries])
            self._settle = self._merkle_of(
                [bytes.fromhex(e.settlement_hash) for e in self._entries if e.settlement_hash])
            self._roots_dirty = False

    def merkle_root(self) -> str:
        """Single digest over all sealed cores (cached; recomputed only on change)."""
        self._refresh_roots()
        assert self._merkle is not None
        return self._merkle

    def merkle_proof(self, entry_id: str) -> dict | None:
        """An inclusion proof: the sibling-hash path from this entry's leaf to the Merkle
        root. A third party can recompute the root from (leaf + path) with verify_inclusion()
        — proving the decision is under the anchored root WITHOUT trusting NEXUS or even
        calling the API. This is the verifiable-memory primitive a model's 'memory' cannot
        reproduce: a sealed leaf, fixed before its outcome, provable under an external anchor."""
        e = self.by_id(entry_id)
        if e is None:
            return None
        leaves = [e2.hash for e2 in self._entries]
        idx = e.seq
        level = [bytes.fromhex(h) for h in leaves]
        path: list[dict] = []
        i = idx
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])           # duplicate last (matches merkle_root)
            sib = level[i ^ 1]
            path.append({"hash": sib.hex(), "side": "right" if i % 2 == 0 else "left"})
            level = [hashlib.sha256(level[k] + level[k + 1]).digest()
                     for k in range(0, len(level), 2)]
            i //= 2
        return {"leaf": e.hash, "leaf_index": idx, "entries": len(leaves),
                "path": path, "merkle_root": level[0].hex() if level else GENESIS}

    def settlement_root(self) -> str:
        """Merkle root over settled outcomes (cached; recomputed only on change)."""
        self._refresh_roots()
        assert self._settle is not None
        return self._settle

    def is_intact(self, max_age: float = 5.0) -> bool:
        """LIVE integrity signal: actually re-verifies the chain (incrementally when a
        checkpoint exists, else fully), returning a real boolean rather than a flag set
        once at load. Result is TTL-cached (default 5s) so hot reads don't re-hash on every
        call; pass max_age=0 to force a fresh check (e.g. a health probe)."""
        now = time.time()
        if self._valid_checked_at and (now - self._valid_checked_at) < max_age:
            return self._valid
        try:
            if not self._entries:
                self._valid = True
            else:
                load_cp = getattr(self.store, "load_checkpoint", None)
                if load_cp and load_cp():
                    self._verify_incremental()
                else:
                    self.verify()
                self._valid = True
        except TamperError:
            self._valid = False
        self._valid_checked_at = now
        return self._valid

    def digest(self) -> dict:
        # chain_valid is a LIVE, bounded re-verification (TTL-cached, incremental when a
        # checkpoint exists) — not a flag set once at load.
        return {
            "entries": len(self._entries),
            "merkle_root": self.merkle_root(),
            "settlement_root": self.settlement_root(),
            "head": self._entries[-1].hash if self._entries else GENESIS,
            "chain_valid": self.is_intact(),
            "sealed_at": time.time(),
        }

    # ── reads ─────────────────────────────────────────────────────────────
    def by_id(self, entry_id: str) -> Entry | None:
        for e in self._entries:
            if e.id == entry_id:
                return e
        return None

    def all(self) -> list[Entry]:
        return list(self._entries)

    def pending(self) -> list[Entry]:
        return [e for e in self._entries if e.status == Status.PENDING.value]

    def resolved(self, kind: Kind | None = None) -> list[Entry]:
        out = [e for e in self._entries if e.status == Status.RESOLVED.value]
        if kind is not None:
            out = [e for e in out if e.prediction.get("kind") == kind.value]
        return out

    def due(self, now: float | None = None) -> list[Entry]:
        now = now if now is not None else time.time()
        return [e for e in self.pending()
                if float(e.prediction.get("resolves_at", 0)) <= now]


def verify_inclusion(leaf_hex: str, path: list[dict], root_hex: str) -> bool:
    """Recompute a Merkle root from a leaf and its inclusion path. Pure, dependency-free,
    and self-contained so anyone can verify a NEXUS decision certificate offline."""
    cur = bytes.fromhex(leaf_hex)
    for step in path:
        sib = bytes.fromhex(step["hash"])
        cur = (hashlib.sha256(cur + sib).digest() if step.get("side") == "right"
               else hashlib.sha256(sib + cur).digest())
    return cur.hex() == root_hex
