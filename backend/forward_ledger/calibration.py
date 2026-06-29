# backend/forward_ledger/calibration.py
"""
Calibration scored ONLY from resolved entries. Two surfaces, never conflated:

  * forward  — sealed before the outcome existed. This is the real test. A fresh
               ledger reports 0 resolved and says so honestly ("the clock just
               started"); that honesty is the credibility, not a liability.
  * backtest — historical, hindsight, explicitly labeled. Context only. Never the
               headline number, never mixed into the forward score.

Metrics: accuracy (thresholded at 0.5), Brier score (proper scoring rule), and a
reliability curve (mean actual survival per predicted-probability bucket).
"""
from __future__ import annotations

from .ledger import Entry, Kind, Ledger


def _survival_prob(e: Entry) -> float:
    p = e.prediction
    w = p.get("weights") or []
    s = int(p.get("survivor", 0))
    if w and 0 <= s < len(w):
        return float(w[s])
    return float(p.get("confidence", 0.5))


def _score(entries: list[Entry]) -> dict:
    n = len(entries)
    if n == 0:
        return {"n": 0, "accuracy": None, "brier": None, "reliability": [],
                "samples": [], "pending_only": True}
    correct = 0
    brier = 0.0
    buckets = [[0, 0] for _ in range(10)]  # [sum_actual, count] per 0.1 band
    samples = []
    for e in entries:
        p = _survival_prob(e)
        actual = bool(e.survived)
        if (p >= 0.5) == actual:
            correct += 1
        brier += (p - (1.0 if actual else 0.0)) ** 2
        b = min(9, int(p * 10))
        buckets[b][0] += 1 if actual else 0
        buckets[b][1] += 1
        samples.append({
            "decision": e.prediction.get("decision", ""),
            "predicted": round(p, 3),
            "survived": actual,
            "sealed_at": e.created_at,
            "resolved_at": e.resolved_at,
            "id": e.id,
        })
    reliability = [round(s / c, 3) if c else None for s, c in buckets]
    return {
        "n": n,
        "accuracy": round(correct / n, 4),
        "brier": round(brier / n, 4),
        "reliability": reliability,
        "samples": samples[-24:],
        "pending_only": False,
    }


def calibration(ledger: Ledger) -> dict:
    from .recalibrate import MIN_N, reliability_band, reliability_map  # local import avoids a cycle
    fwd = ledger.resolved(Kind.FORWARD)
    bt = ledger.resolved(Kind.BACKTEST)
    pending_fwd = [e for e in ledger.pending()
                   if e.prediction.get("kind") == Kind.FORWARD.value]
    next_resolves = min((float(e.prediction.get("resolves_at", 0)) for e in pending_fwd),
                        default=None)
    rmap = reliability_map(ledger)
    band = reliability_band(ledger)
    real_fwd = [e for e in fwd if not _is_demo_ref(e.prediction.get("oracle_ref", ""))]
    demo_fwd = [e for e in fwd if _is_demo_ref(e.prediction.get("oracle_ref", ""))]
    learning = {
        # the L1 flywheel state: is the recalibration curve live yet, and how close
        # are we to it bending? This is the "smarter with every outcome" indicator.
        "recalibration_active": any(v is not None for v in rmap),
        "fitted_reliability": rmap,
        "reliability_band": band["bands"],          # observed survival + 95% Wilson CI
        "significant": band["significant"],          # has the curve earned its shape?
        "resolved_forward": len(fwd),
        "needed_for_recalibration": MIN_N,
    }
    return {
        "live": True,
        "forward": {
            **_score(fwd),
            "sealed_pending": len(pending_fwd),
            "next_resolution_at": next_resolves,
        },
        "backtest": {
            **_score(bt),
            "note": "historical · hindsight · context only — never the forward claim",
        },
        "learning": learning,
        "cohorts": {
            "real_forward_resolved": len(real_fwd),
            "demo_forward_resolved": len(demo_fwd),
            "note": ("'real' = genuine externally-anchorable forward calls; 'demo' = the "
                     "backdated Human-vs-AI arena cohort, illustrative only. The headline "
                     "accuracy is honest about including the demo cohort."),
        },
        "digest": ledger.digest(),
        # the honest one-liner the proof panel should say:
        "headline": _headline(fwd, pending_fwd),
    }


def _is_demo_ref(ref: str) -> bool:
    # arena/demo-horizon forwards are illustrative: real mechanism, backdated seals.
    return (ref or "").startswith(("arena:", "demo:"))


def _headline(fwd_resolved: list[Entry], pending: list[Entry]) -> str:
    if not fwd_resolved:
        return (f"{len(pending)} forecasts sealed and time-stamped before their outcomes. "
                f"0 resolved yet — the forward record has just begun. Verify the seal against "
                f"the published Merkle root; nothing here is graded by us.")
    s = _score(fwd_resolved)
    demo_present = any(_is_demo_ref(e.prediction.get("oracle_ref", "")) for e in fwd_resolved)
    illustrative = s["n"] < 30 or demo_present
    caveat = (" (illustrative — includes a backdated demo/arena cohort and/or too few resolved "
              "rows to be statistically meaningful; the genuine long-horizon, externally-anchored "
              "record is still sealed and pending)") if illustrative else ""
    return (f"{s['n']} forward forecasts sealed before their outcomes and since resolved by "
            f"external oracles: {round(s['accuracy']*100)}% correct, Brier {s['brier']}{caveat}. "
            f"{len(pending)} still sealed and pending. Every seal predates its resolution — "
            f"check the chain.")
