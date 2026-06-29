# backend/forward_ledger/resolver.py
"""
The autonomous resolution loop. In production this is a Lambda on an EventBridge
cron (see infra/cdk). It walks PENDING entries whose resolve_at has passed, asks
the oracle, and — only if the oracle answers — records the outcome. Decision →
outcome → score, with no human and no self-grading in the loop.
"""
from __future__ import annotations

import time

from .ledger import Ledger
from .oracles import Oracle


def resolve_due(ledger: Ledger, oracle: Oracle, now: float | None = None) -> list[dict]:
    now = now if now is not None else time.time()
    settled = []
    for e in ledger.due(now):
        ref = e.prediction.get("oracle_ref", "")
        ans = oracle.settle(ref)
        if ans is None:
            continue  # not settleable yet → stays PENDING (never invented)
        survived, evidence = ans
        ledger.resolve(e.id, survived, evidence, at=now)
        settled.append({"id": e.id, "survived": survived, "evidence": evidence})
    return settled
