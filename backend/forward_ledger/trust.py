# backend/forward_ledger/trust.py
"""
The Trust Graph — quantified, public, per-forecaster credibility. It is a pure
aggregation over *resolved forward* entries: you earn a calibration score only by
making sealed calls that later get settled by an oracle. This cannot be faked and
cannot be backfilled, which is exactly why it compounds into a moat.

A latecomer can copy the UI; they cannot copy a year of your resolved calls.
"""
from __future__ import annotations

from collections import defaultdict

from .calibration import _survival_prob
from .ledger import Entry, Kind, Ledger
from .questions import canonical_id


def _brier_acc(entries: list[Entry]) -> tuple[float, float]:
    n = len(entries)
    if n == 0:
        return 0.0, 0.0
    correct = brier = 0.0
    for e in entries:
        p = _survival_prob(e)
        actual = bool(e.survived)
        correct += 1.0 if (p >= 0.5) == actual else 0.0
        brier += (p - (1.0 if actual else 0.0)) ** 2
    return correct / n, brier / n


def trust_graph(ledger: Ledger) -> dict:
    resolved = ledger.resolved(Kind.FORWARD)
    by_author: dict[str, list[Entry]] = defaultdict(list)
    by_author_domain: dict[tuple[str, str], list[Entry]] = defaultdict(list)
    pending_by_author: dict[str, int] = defaultdict(int)

    for e in resolved:
        a = e.prediction.get("author", "anon")
        d = e.prediction.get("domain", "general")
        by_author[a].append(e)
        by_author_domain[(a, d)].append(e)
    for e in ledger.pending():
        if e.prediction.get("kind") == Kind.FORWARD.value:
            pending_by_author[e.prediction.get("author", "anon")] += 1

    diff = question_difficulty(ledger)
    first = {c["author"]: c["first_right"] for c in first_to_call(ledger)["first_movers"]}

    authors = []
    for a, es in by_author.items():
        acc, brier = _brier_acc(es)
        eff_brier, n = _difficulty_weighted_brier(ledger, es, diff)
        domains = {}
        for (aa, dd), des in by_author_domain.items():
            if aa == a:
                dacc, dbrier = _brier_acc(des)
                domains[dd] = {"n": len(des), "accuracy": round(dacc, 4), "brier": round(dbrier, 4)}
        authors.append({
            "author": a,
            "resolved": len(es),
            "pending": pending_by_author.get(a, 0),
            "accuracy": round(acc, 4) if len(es) > 0 else None,
            "brier": round(brier, 4) if len(es) > 0 else None,
            # calibration-weighted trust: low Brier (well-calibrated) → high weight,
            # damped by sample size so a 1/1 lucky call doesn't top the board.
            "trust": round(_trust_weight(brier, len(es)), 4),
            # difficulty-weighted: being right on questions the crowd was split on is
            # worth more than farming near-certain calls. This is the leaderboard sort.
            "effective_trust": round(_trust_weight(eff_brier, len(es)), 4),
            "first_right": first.get(a, 0),
            "domains": domains,
        })
    # leaderboard by difficulty-weighted trust, not volume or easy wins — quality wins
    authors.sort(key=lambda x: (x["effective_trust"], x["first_right"]), reverse=True)
    return {"authors": authors, "scored_on": len(resolved),
            "weighting": "difficulty-weighted calibration · first-to-be-right credited"}


def _trust_weight(brier: float, n: int) -> float:
    # 0 (worthless) .. 1 (perfectly calibrated, well-sampled).
    # Brier 0.25 == coin-flip baseline → weight ~0. Better than 0.25 earns weight.
    base = max(0.0, (0.25 - brier) / 0.25)
    confidence = n / (n + 8.0)          # shrink toward 0 until a track record exists
    return base * confidence


def author_weight(ledger: Ledger, author: str) -> float:
    es = [e for e in ledger.resolved(Kind.FORWARD)
          if e.prediction.get("author", "anon") == author]
    _, brier = _brier_acc(es)
    return _trust_weight(brier, len(es))


def question_difficulty(ledger: Ledger) -> dict[str, float]:
    """Per canonical question, how hard it was: 1 - |2*crowd_mean - 1| over every
    forward forecast on it. A question the crowd is split on (~0.5) scores ~1.0
    (hard); a near-unanimous one scores ~0.0 (easy). Difficulty weights the trust
    score, so farming volume on near-certain calls no longer climbs the board."""
    by_q: dict[str, list[float]] = defaultdict(list)
    for e in ledger.all():
        p = e.prediction
        if p.get("kind") != Kind.FORWARD.value:
            continue
        qid = canonical_id(p.get("decision", ""), p.get("oracle_ref", ""))
        by_q[qid].append(_survival_prob(e))
    return {qid: round(1.0 - abs(2.0 * (sum(ps) / len(ps)) - 1.0), 4)
            for qid, ps in by_q.items() if ps}


def _difficulty_weighted_brier(ledger: Ledger, entries: list[Entry],
                               diff: dict[str, float]) -> tuple[float, int]:
    num = den = 0.0
    for e in entries:
        qid = canonical_id(e.prediction.get("decision", ""), e.prediction.get("oracle_ref", ""))
        w = diff.get(qid, 0.5) + 0.1                       # floor so easy calls still count a little
        p = _survival_prob(e)
        actual = 1.0 if bool(e.survived) else 0.0
        num += w * (p - actual) ** 2
        den += w
    return (num / den if den else 0.0), len(entries)


def first_to_call(ledger: Ledger, top: int = 12) -> dict:
    """Who was provably RIGHT FIRST on each resolved canonical question — the single
    most valuable reputational fact, and one only a seal-time-anchored chain can
    compute. For each resolved question we find the earliest-sealed forecast whose
    predicted side matched the outcome, and credit its author with lead time over the
    median seal on that question."""
    res = ledger.resolved(Kind.FORWARD)
    by_q: dict[str, list[Entry]] = defaultdict(list)
    for e in res:
        by_q[canonical_id(e.prediction.get("decision", ""), e.prediction.get("oracle_ref", ""))].append(e)

    credits: dict[str, dict] = {}
    calls = []
    for qid, es in by_q.items():
        outcome = bool(es[0].survived)
        correct = [e for e in es if (_survival_prob(e) >= 0.5) == outcome]
        if not correct:
            continue
        correct.sort(key=lambda e: e.created_at)
        first = correct[0]
        seals = sorted(e.created_at for e in es)
        median_seal = seals[len(seals) // 2]
        lead = round(median_seal - first.created_at, 2)    # seconds earlier than the median call
        a = first.prediction.get("author", "anon")
        c = credits.setdefault(a, {"author": a, "first_right": 0, "total_lead": 0.0})
        c["first_right"] += 1
        c["total_lead"] += max(0.0, lead)
        calls.append({"question_id": qid, "author": a,
                      "question": first.prediction.get("decision", "")[:72],
                      "lead_over_median_s": lead, "outcome_survived": outcome})

    board = sorted(credits.values(), key=lambda x: (x["first_right"], x["total_lead"]), reverse=True)
    return {"first_movers": board[:top], "calls": calls[:top],
            "note": "earliest-sealed correct forecast per resolved question — provable "
                    "only because every seal is externally time-stamped."}
