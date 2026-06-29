# backend/forward_ledger/value.py
"""
Business-impact model — measured from the record, with every estimate's model attached.

Two kinds of number, never conflated:
  * MEASURED — computed directly from the verified record (coverage, audit readiness,
    verification rate, capital tracked). These are facts about the data.
  * ESTIMATED — a parameterised value model with DECLARED inputs (labour rates, review
    cadence). Flagged ``estimate: true`` with the formula, never invented precision.
"""
from __future__ import annotations

import math

from .ledger import Kind, Ledger


def _bounded(x, default: float, lo: float, hi: float) -> float:
    """Finite + range-clamped, so absurd inputs can't overflow (e.g. 1e308 × hours → inf)."""
    v = float(x) if isinstance(x, (int, float)) and math.isfinite(x) else default
    return min(hi, max(lo, v))


def value_summary(ledger: Ledger, *, analyst_hourly_usd: float = 150.0,
                  hours_per_review: float = 40.0, reviews_per_year: int = 12,
                  automation_fraction: float = 0.7) -> dict:
    analyst_hourly_usd = _bounded(analyst_hourly_usd, 150.0, 0.0, 100_000.0)
    hours_per_review = _bounded(hours_per_review, 40.0, 0.0, 100_000.0)
    automation_fraction = _bounded(automation_fraction, 0.7, 0.0, 1.0)
    reviews_per_year = int(_bounded(reviews_per_year, 12, 0, 100_000))
    resolved = ledger.resolved(Kind.FORWARD)
    pending = [e for e in ledger.pending()
               if e.prediction.get("kind") == Kind.FORWARD.value]
    sealed = resolved + pending
    n_sealed = len(sealed)

    with_assumptions = sum(1 for e in sealed if e.prediction.get("assumptions"))
    with_evidence = sum(1 for e in resolved if getattr(e, "resolution_evidence_hash", None))

    def frac(a: int, b: int) -> float | None:
        return round(a / b, 4) if b else None

    measured = {
        "decisions_on_record": n_sealed,
        "assumption_coverage": frac(with_assumptions, n_sealed),
        "audit_readiness": frac(with_evidence, len(resolved)),
        "forecast_verification_rate": frac(len(resolved), n_sealed),
        "resolved_outcomes": len(resolved),
        "sealed_pending": len(pending),
        "note": "facts computed directly from the verified record",
    }

    # capital tracked / at risk, when the connected enterprise graph is present
    try:
        from .enterprise import propagate
        prop = propagate(ledger)
        capital = {
            "capital_repriced_usd": prop["summary"]["capital_repriced_usd"],
            "decisions_now_at_risk": prop["summary"]["now_at_risk"],
            "model": prop["impact_model"], "estimate": True,
        }
    except Exception:
        capital = None

    hours_saved = hours_per_review * reviews_per_year * automation_fraction
    estimated = {
        "review_prep_hours_saved_per_year": round(hours_saved, 1),
        "labour_value_usd_per_year": round(hours_saved * analyst_hourly_usd),
        "estimate": True,
        "inputs": {"analyst_hourly_usd": analyst_hourly_usd,
                   "hours_per_review": hours_per_review,
                   "reviews_per_year": reviews_per_year,
                   "automation_fraction": automation_fraction},
        "model": ("hours_saved = hours_per_review × reviews_per_year × automation_fraction; "
                  "labour_value = hours_saved × analyst_hourly_usd. An estimate with its "
                  "inputs declared, not a guaranteed saving."),
    }

    return {
        "name": "Business Impact",
        "measured": measured,
        "capital": capital,
        "estimated_value": estimated,
        "headline": (
            f"{measured['decisions_on_record']} decisions on record · "
            f"{_pct(measured['assumption_coverage'])} carry tracked assumptions · "
            f"{_pct(measured['forecast_verification_rate'])} verified against reality"),
    }


def _pct(x: float | None) -> str:
    return f"{round(100 * x)}%" if isinstance(x, (int, float)) else "n/a"
