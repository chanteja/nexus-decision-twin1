# backend/forward_ledger/assumptions.py
"""
The Assumption Ledger — the only causal asset NEXUS can hold honestly.

The grandiose version of "causal intelligence" (a Reality Genome of 10M scraped
causal chains) is not defensible: the underlying outcomes are public, so anyone can
rebuild it. What is NOT replicable is a corpus of assumptions that were *sealed
before the outcome existed* and then graded by what actually happened. That corpus
can only form if you persisted the assumptions from the first sealed call — exactly
the counterfactual-corpus moat, but with causal content instead of a branch prior.

What we can honestly say at resolution:
  * the bet's outcome (survived: bool), graded by an oracle we do not control;
  * the named assumptions the survivor branch was sealed on.

We CANNOT observe whether an assumption was "true in isolation" unless it carries
its own oracle_ref and later resolves on its own. So the learning signal is
deliberately conservative:

    an assumption accrues `failed_with` weight ONLY when the bet it underwrote FAILED.

Aggregated across the record, this surfaces the beliefs that recur in failures —
"premature scaling," "rates stay high," "this founder stays" — ranked by how often
reality falsified the bets that leaned on them. That ranking is a genuinely
proprietary, genuinely useful signal, and a year-3 competitor's ledger starts empty.

When an assumption DOES carry its own oracle_ref, the resolver settles it like any
other prediction; `assumption_truth()` then joins the two, upgrading "recurred in a
failure" to "was sealed, independently resolved false, and the bet that leaned on it
failed" — the strongest causal claim available without fabricating a counterfactual.
"""
from __future__ import annotations

import hashlib

from .ledger import Entry, Ledger


def _norm(a: str) -> str:
    return " ".join((a or "").lower().split())


def assumption_key(a: str) -> str:
    return "asm:" + hashlib.sha256(_norm(a).encode("utf-8")).hexdigest()[:16]


def assumption_rows(e: Entry) -> list[dict]:
    """One row per sealed assumption of a just-resolved entry. Emitted by
    Ledger.resolve(); also usable standalone for backfill/tests."""
    p = e.prediction
    assumptions = p.get("assumptions") or []
    taken_survived = bool(e.survived)
    rows = []
    for a in assumptions:
        rows.append({
            "key": assumption_key(a),
            "assumption": a,
            "entry_id": e.id,
            "question": p.get("decision", ""),
            "domain": p.get("domain", "general"),
            "author": p.get("author", "anon"),
            # the signal: did the bet that leaned on this assumption fail?
            "bet_failed": (not taken_survived),
            "sealed_at": e.created_at,
            "resolved_at": e.resolved_at,
        })
    return rows


def assumptions_corpus(ledger: Ledger, domain: str | None = None,
                       limit: int = 100) -> dict:
    """Read surface for /v1/assumptions. Ranks assumptions by how often the bets
    that leaned on them were falsified by reality — the queryable causal corpus."""
    rows = ledger.assumption_rows()
    if domain:
        rows = [r for r in rows if r.get("domain") == domain]

    agg: dict[str, dict] = {}
    for r in rows:
        k = r["key"]
        a = agg.setdefault(k, {"key": k, "assumption": r["assumption"],
                               "seen": 0, "failed_with": 0,
                               "domains": set()})
        a["seen"] += 1
        a["failed_with"] += 1 if r["bet_failed"] else 0
        a["domains"].add(r.get("domain", "general"))

    ranked = []
    for a in agg.values():
        # falsification rate, shrunk toward 0.5 by sample size so a single failed bet
        # cannot crown an assumption "the thing reality always breaks."
        n = a["seen"]
        rate = (a["failed_with"] + 1.0) / (n + 2.0)      # Laplace-smoothed
        ranked.append({
            "key": a["key"],
            "assumption": a["assumption"],
            "seen": n,
            "failed_with": a["failed_with"],
            "falsification_rate": round(rate, 4),
            "domains": sorted(a["domains"]),
        })
    ranked.sort(key=lambda x: (x["falsification_rate"], x["seen"]), reverse=True)

    return {
        "assumptions": ranked[:limit],
        "total_rows": len(rows),
        "distinct": len(agg),
        "note": "beliefs ranked by how often the sealed bets that leaned on them were "
                "later falsified by an external oracle — a causal corpus that only forms "
                "if assumptions are sealed before the outcome, from the first call.",
    }
