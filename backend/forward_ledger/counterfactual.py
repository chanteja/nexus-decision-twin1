# backend/forward_ledger/counterfactual.py
"""
L2 — the counterfactual corpus. The headline asset, made real.

v11's ensemble docstring claimed the six untaken branches "become scored
counterfactuals." Nothing persisted them. This module defines the scoring and the
reads; ledger.resolve() now emits the rows (one per branch) into a sibling
append-only log the instant an outcome lands.

What we can honestly know at resolution:
  * the TAKEN path's outcome (survived: bool) — graded by an oracle we don't control;
  * the sealed survival weight every branch was given BEFORE the outcome existed.

What we cannot know: whether an untaken branch "would have survived" — that future
never happened. So `regret` is defined as a real, computable decision signal rather
than a fabricated counterfactual outcome:

    regret(branch_i) = 0.0                if the taken path survived
                     = branch_prob_i      if the taken path FAILED

i.e. when the chosen path failed, every alternative we passed on carries regret in
proportion to how plausible the model had rated it. High-regret rows are exactly the
decisions worth learning from — we failed and had a credible alternative on record.
Aggregated by domain (and later by assumption), this surfaces the patterns a single
win/loss bit cannot. The corpus only forms if persisted from day one — which is the
entire moat.
"""
from __future__ import annotations

from collections import defaultdict

from .ledger import Entry, Ledger


def regret(was_taken: bool, branch_prob: float, taken_survived: bool) -> float:
    """The learning signal for one branch row (see module docstring)."""
    if taken_survived:
        return 0.0
    return round(float(branch_prob), 4)


def counterfactual_rows(e: Entry) -> list[dict]:
    """Score the full branch vector of a just-resolved entry into corpus rows.
    Called by Ledger.resolve(); also usable standalone for backfill/tests."""
    p = e.prediction
    weights = p.get("weights") or []
    branches = p.get("branches") or []
    survivor = int(p.get("survivor", 0))
    taken_survived = bool(e.survived)
    rows = []
    for i, branch in enumerate(branches):
        bp = round(float(weights[i]), 4) if i < len(weights) else None
        rows.append({
            "entry_id": e.id,
            "question": p.get("decision", ""),
            "branch_index": i,
            "branch": branch,
            "branch_prob": bp,
            "was_taken": (i == survivor),
            "taken_survived": taken_survived,
            "regret": regret(i == survivor, bp if bp is not None else 0.0, taken_survived),
            "domain": p.get("domain", "general"),
            "author": p.get("author", "anon"),
            "oracle_ref": p.get("oracle_ref", ""),
            "resolved_at": e.resolved_at,
            "sealed_at": e.created_at,
        })
    return rows


def counterfactuals(ledger: Ledger, domain: str | None = None,
                    min_regret: float = 0.0, limit: int = 200) -> dict:
    """Read surface for /v1/counterfactuals. Returns scored untaken-branch rows
    plus a domain-level regret aggregation — the queryable reality dataset."""
    rows = ledger.counterfactual_rows()
    if domain:
        rows = [r for r in rows if r.get("domain") == domain]
    untaken = [r for r in rows if not r.get("was_taken")]
    flagged = [r for r in untaken if r.get("regret", 0.0) >= min_regret]
    flagged.sort(key=lambda r: r.get("regret", 0.0), reverse=True)

    by_domain: dict[str, list[float]] = defaultdict(list)
    for r in untaken:
        by_domain[r.get("domain", "general")].append(r.get("regret", 0.0))
    domain_regret = [
        {"domain": d, "branches": len(rs), "mean_regret": round(sum(rs) / len(rs), 4)}
        for d, rs in by_domain.items() if rs
    ]
    domain_regret.sort(key=lambda x: x["mean_regret"], reverse=True)

    return {
        "rows": flagged[:limit],
        "total_branches": len(rows),
        "scored_untaken": len(untaken),
        "domain_regret": domain_regret,
        "note": "the roads not taken, scored against what actually happened. NOTE: "
                "branch regret is a weak signal (the model's own prior conditioned on a "
                "loss); the causal headline is now the Assumption Ledger (/v1/assumptions), "
                "which scores the sealed assumptions that recur in failed bets.",
    }
