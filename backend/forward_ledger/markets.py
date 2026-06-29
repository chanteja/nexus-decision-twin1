# backend/forward_ledger/markets.py
"""
Reality Markets — collective intelligence that is structurally better than a naive
prediction market. A plain market weights every voice equally; NEXUS weights each
forecaster by their *resolved* calibration (the Trust Graph). Good forecasters
count more, and the weighting function is trained on our private resolved history —
so the consensus sharpens as more *good* forecasters join, and a competitor cannot
reproduce the weighting without the same history. This is the multi-sided network
effect with a defensible twist.
"""
from __future__ import annotations

from collections import defaultdict

from .calibration import _survival_prob
from .ledger import Entry, Kind, Ledger
from .questions import canonical_id, is_bound
from .trust import author_weight

# The crowd consensus is published as its own forecaster with its own track record,
# rather than blended into everyone's sealed call (which would herd the record).
# It is excluded from its own input so it never feeds on itself.
CONSENSUS_AUTHOR = "nexus-consensus"


def _peers_on(ledger: Ledger, qid: str, exclude_author: str | None = None) -> list[Entry]:
    out = []
    for e in ledger.pending():
        p = e.prediction
        if p.get("kind") != Kind.FORWARD.value:
            continue
        if not is_bound(p.get("oracle_ref", "")):
            continue                                  # provisional → never a peer
        if p.get("author") == CONSENSUS_AUTHOR:
            continue                                  # consensus never feeds on itself
        if exclude_author and p.get("author") == exclude_author:
            continue
        if canonical_id(p.get("decision", ""), p.get("oracle_ref", "")) == qid:
            out.append(e)
    return out


def _weighted_consensus(ledger: Ledger, entries: list[Entry], cache: dict[str, float]) -> tuple[float, float]:
    """Calibration-weighted mean survival over a set of sealed forward predictions,
    plus the total trust mass backing it (a proxy for evidence strength)."""
    num = den = 0.0
    for e in entries:
        a = e.prediction.get("author", "anon")
        if a not in cache:
            cache[a] = author_weight(ledger, a)
        tw = cache[a] + 0.05                      # floor so anons still count a little
        num += _survival_prob(e) * tw
        den += tw
    return (num / den if den else 0.0), den


def question_consensus(ledger: Ledger, qid: str) -> tuple[float | None, float]:
    """The calibration-weighted consensus for one canonical question over sealed
    forward peers (bound only, consensus author excluded), and an evidence weight in
    [0, ~). Returns (None, 0.0) when no peers exist. This is now a READ surface for
    the consensus forecaster — it is no longer blended into anyone's sealed verdict."""
    cache: dict[str, float] = {}
    peers = _peers_on(ledger, qid)
    if not peers:
        return None, 0.0
    consensus, mass = _weighted_consensus(ledger, peers, cache)
    evidence = len(peers) / (len(peers) + 4.0)
    return round(consensus, 4), round(evidence, 4)


def consensus_forecast(ledger: Ledger, decision: str, oracle_ref: str) -> dict | None:
    """Build the crowd-consensus call for a bound question, to be sealed as its OWN
    forecaster (author=nexus-consensus). Returns None if the question is unbound or
    has no (non-consensus) peers yet — so the consensus only ever competes on real
    questions where a crowd actually exists. The companion seal accrues an independent
    track record, giving the record a second scoreboard: crowd vs. each individual."""
    if not is_bound(oracle_ref):
        return None
    qid = canonical_id(decision, oracle_ref)
    prior, evidence = question_consensus(ledger, qid)
    if prior is None:
        return None
    return {
        "author": CONSENSUS_AUTHOR,
        "survival": prior,
        "evidence": evidence,
        "question_id": qid,
        "n_peers": len(_peers_on(ledger, qid)),
    }


def markets(ledger: Ledger) -> dict:
    # group sealed (pending) forward predictions by CANONICAL question, so two
    # phrasings of the same question pool into one consensus node (the accretion
    # point of the network effect) instead of fragmenting.
    by_q: dict[str, list[Entry]] = defaultdict(list)
    for e in ledger.pending():
        p = e.prediction
        if p.get("kind") != Kind.FORWARD.value:
            continue
        if not is_bound(p.get("oracle_ref", "")):
            continue                                  # provisional questions never list
        qid = canonical_id(p.get("decision", ""), p.get("oracle_ref", ""))
        by_q[qid].append(e)

    cache: dict[str, float] = {}
    out = []
    for qid, es in by_q.items():
        consensus, _ = _weighted_consensus(ledger, es, cache)
        naive = sum(_survival_prob(e) for e in es) / len(es)
        out.append({
            "question_id": qid,
            "question": es[0].prediction.get("decision", qid),
            "oracle_ref": es[0].prediction.get("oracle_ref", ""),
            "n_forecasts": len(es),
            "consensus_weighted": round(consensus, 4),
            "consensus_naive": round(naive, 4),
            "resolves_at": es[0].prediction.get("resolves_at", 0),
        })
    out.sort(key=lambda m: m["n_forecasts"], reverse=True)
    return {"markets": out, "weighting": "calibration-weighted (trust graph) · canonical-question keyed"}
