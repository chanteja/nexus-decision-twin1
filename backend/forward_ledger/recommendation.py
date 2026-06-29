# backend/forward_ledger/recommendation.py
"""Recommendation Engine — every recommendation explains why, evidence, business impact,
confidence, alternatives, and the recommended action, grounded in the simulation."""
from __future__ import annotations


def recommend(decision: str, sim: dict, assumptions: list[str], domain: str = "general") -> dict:
    exp = float(sim.get("expected_survival", 0.0))
    dist = sim.get("distribution", {})
    p10 = float(dist.get("p10_worst", exp))
    drivers = sim.get("drivers", []) or []
    top = drivers[0] if drivers else None

    if exp < 0.40:
        action = f"Hold and re-underwrite “{decision}” before committing capital."
        stance = "hold"
    elif exp < 0.60:
        action = (f"Stage “{decision}” behind a gate that releases only once the "
                  "load-bearing belief re-clears.")
        stance = "gate"
    else:
        action = f"Proceed with “{decision}”, monitoring the load-bearing belief."
        stance = "proceed"

    why = (f"Expected survival is {round(exp * 100)}% (worst-case {round(p10 * 100)}%); "
           + (f"the outcome is dominated by “{top['assumption']}” "
              f"({round(top['variance_share'] * 100)}% of the variance)."
              if top else "no single assumption dominates the outcome."))

    evidence = [f"“{d['assumption']}” — P(holds) {d['prob_holds']}, drives "
                f"{round(d['variance_share'] * 100)}% of outcome variance" for d in drivers[:3]]
    evidence.append("Probabilities are learned from the verified record (1 − falsification rate).")

    business_impact = {
        "expected_survival": round(exp, 4),
        "downside_p10": round(p10, 4),
        "failure_pressure": round(1 - exp, 4),
        "interpretation": (f"~{round((1 - exp) * 100)}% expected failure pressure; the "
                           f"downside scenario still survives at {round(p10 * 100)}%."),
        "estimate": True,
        "note": ("risk framing from the simulation. Commit the decision with a "
                 "capital_at_risk to get a dollar exposure via the cascade (propagate)."),
    }

    confidence = {
        "expected_survival": round(exp, 4),
        "stdev": sim.get("stdev"),
        "basis": "Monte-Carlo over learned assumption probabilities",
    }

    alt = []
    if top:
        alt.append(f"Decorrelate: redeploy to an initiative that does not depend on "
                   f"“{top['assumption']}”.")
    alt.append("Run a capped pilot that auto-expands only once the pivotal belief re-clears.")
    alt.append("Tighten the weakest assumption (buy data / hedge) before committing.")

    return {
        "recommended_action": action,
        "stance": stance,
        "why": why,
        "evidence": evidence,
        "business_impact": business_impact,
        "confidence": confidence,
        "alternatives": alt,
    }
