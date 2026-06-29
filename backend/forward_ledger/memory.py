# backend/forward_ledger/memory.py
"""
Decision Memory — related initiatives REUSE and EXTEND an existing Decision Graph.

Without this, every sealed decision is an island. Decision Memory matches a new decision
to the graph it belongs to by SHARED ASSUMPTIONS: if a new bet leans on beliefs an existing
initiative already rests on, it joins that graph (so a falsified belief later cascades
across the whole connected strategy) instead of forking an isolated graph.
"""
from __future__ import annotations

import hashlib

from .assumptions import _norm, assumption_key
from .ledger import Ledger


def _graph_assumption_keys(ledger: Ledger) -> dict[str, set[str]]:
    graphs: dict[str, set[str]] = {}
    for e in ledger.all():
        gid = e.prediction.get("graph_id")
        if not gid:
            continue
        keys = graphs.setdefault(gid, set())
        for a in e.prediction.get("assumptions") or []:
            keys.add(assumption_key(a))
    return graphs


def find_graph(ledger: Ledger, assumptions: list[str], min_shared: int = 1) -> str | None:
    """The existing graph that shares the most assumptions with this decision (>= min_shared),
    so a related initiative extends it rather than starting a disconnected one."""
    want = {assumption_key(a) for a in (assumptions or [])}
    if not want:
        return None
    best, best_n = None, 0
    for gid, keys in _graph_assumption_keys(ledger).items():
        n = len(want & keys)
        if n > best_n:
            best, best_n = gid, n
    return best if best_n >= min_shared else None


def assign_graph_id(ledger: Ledger, decision: str, assumptions: list[str]) -> str:
    """Reuse a related graph if one exists; otherwise mint a stable new graph id."""
    existing = find_graph(ledger, assumptions)
    if existing:
        return existing
    return "g:" + hashlib.sha256(_norm(decision).encode("utf-8")).hexdigest()[:12]


def graph_decisions(ledger: Ledger, graph_id: str) -> list:
    return [e for e in ledger.all() if e.prediction.get("graph_id") == graph_id]


def graphs_summary(ledger: Ledger) -> dict:
    """All Decision Graphs in the record, with size and the beliefs they rest on."""
    graphs: dict[str, dict] = {}
    for e in ledger.all():
        gid = e.prediction.get("graph_id")
        if not gid:
            continue
        g = graphs.setdefault(gid, {"graph_id": gid, "decisions": 0, "assumptions": set()})
        g["decisions"] += 1
        for a in e.prediction.get("assumptions") or []:
            g["assumptions"].add(a)
    rows = [{"graph_id": g["graph_id"], "decisions": g["decisions"],
             "assumptions": sorted(g["assumptions"])} for g in graphs.values()]
    rows.sort(key=lambda r: r["decisions"], reverse=True)
    return {"graphs": rows, "count": len(rows)}
