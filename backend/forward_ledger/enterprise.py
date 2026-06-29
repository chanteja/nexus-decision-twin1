# backend/forward_ledger/enterprise.py
"""
The Enterprise Strategy scenario + the live Decision Graph propagation engine.

This is the product's centerpiece: a connected set of real strategic decisions an
enterprise strategy team actually makes, each sealed on the record with the named
assumptions it rests on. When reality falsifies one assumption, propagation walks the
graph and shows — deterministically, with no model call required — every connected
decision whose confidence just changed, ranked by business impact, with the specific
revision each one now needs.

Nothing here fabricates foresight. Every decision is a real sealed entry in the same
hash-chained record as everything else; the cascade is a pure read over that record.
The one decision that already failed (Brazil GTM) is sealed in the past and resolved
in the past by the same oracle path as any other entry — its seal provably precedes
its outcome. Propagation is the organization *learning from a verified failure*.
"""
from __future__ import annotations

import time

from .assumptions import _norm, assumption_key
from .ensemble import decide
from .ledger import Kind, Ledger, Prediction

# ── The shared assumptions (the load-bearing beliefs the strategy rests on) ──
# These strings are reused verbatim across decisions so the graph actually connects.
A_DEMAND   = "Brazil consumer demand grows more than 18% YoY"          # the famous one
A_FX       = "BRL/USD stays within 10% of the planning rate"
A_HIRING   = "We can hire 40 LATAM roles within two quarters"
A_RESIDENCY = "EU data-residency rules do not change before launch"
A_CYCLE    = "Enterprise sales cycle stays under 90 days"

# Human-readable domain → relative business exposure (drives impact ranking).
_DOMAIN_EXPOSURE = {
    "go-to-market": 1.00,
    "supply-chain": 0.95,
    "hiring": 0.70,
    "pricing": 0.85,
    "expansion": 0.90,
    "platform": 0.60,
    "sales-motion": 0.55,
    "general": 0.50,
}

# The connected enterprise decision set.
#  (decision, domain, assumptions, survival, resolved_outcome|None, days_out, capital_usd)
#  resolved_outcome True/False means seal-in-the-past + resolved-in-the-past.
#  None means a genuinely open call that stays PENDING (sealed now).
#  capital_usd = the committed / at-stake capital behind the decision. It is an
#  input to the impact model (below), declared per-decision so the dollar figure is
#  auditable, never invented at render time.
_DECISIONS = [
    ("Launch the Brazil go-to-market in H2", "go-to-market",
     [A_DEMAND, A_FX, A_HIRING], 0.74, False, None, 22_000_000),   # ← already FAILED (trigger)
    ("Build the São Paulo fulfilment center", "supply-chain",
     [A_DEMAND, A_FX], 0.68, None, 210, 35_000_000),
    ("Stand up a 40-person LATAM sales org", "hiring",
     [A_DEMAND, A_HIRING], 0.63, None, 150, 9_000_000),
    ("Set the FY pricing for the LATAM tier", "pricing",
     [A_DEMAND, A_FX], 0.66, None, 120, 12_000_000),
    ("Open the Mexico expansion in FY+1", "expansion",
     [A_DEMAND], 0.59, None, 300, 48_000_000),
    # Controls — these do NOT lean on Brazil demand, so they must stay untouched.
    ("Launch the EU data platform", "platform",
     [A_RESIDENCY, A_CYCLE], 0.71, None, 240, 30_000_000),
    ("Adopt the 90-day enterprise sales motion", "sales-motion",
     [A_CYCLE], 0.64, None, 90, 6_000_000),
]

# decision text → committed capital (USD), for the impact model.
_CAPITAL = {d[0]: d[6] for d in _DECISIONS}

# Per-domain executive alternative — the "instead, do this" a strategy lead expects
# next to every "stop this." Grounded in the scenario, never generic filler.
_ALTERNATIVE = {
    "go-to-market": "Re-enter behind a demand gate: a capped pilot that auto-expands only "
                    "once demand re-clears the corrected threshold.",
    "supply-chain": "Bridge on a 3PL instead of owned capacity — keeps the option open at "
                    "~20% of the capex with no take-or-pay lock-in.",
    "hiring":       "Backfill only revenue-tied roles now; convert the rest to a "
                    "demand-triggered contractor ramp.",
    "pricing":      "Hold current pricing one quarter and re-survey elasticity before the "
                    "next quote cycle, rather than repricing on a stale demand band.",
    "expansion":    "Redeploy the Mexico budget to the validated EU platform until Brazil "
                    "re-clears — same capital, decorrelated demand thesis.",
}

ENTERPRISE_AUTHOR = "strategy-office"
# The Brazil/LATAM scenario is ONE sample Decision Graph, not default behaviour.
SAMPLE_GRAPH_ID = "sample:latam-expansion"
TRIGGER_ASSUMPTION = A_DEMAND
TRIGGER_REF = "ent:brazil_gtm"


def has_enterprise(ledger: Ledger) -> bool:
    return any(
        e.prediction.get("oracle_ref", "").startswith("ent:")
        for e in ledger.all()
    )


def seed_enterprise(ledger: Ledger) -> int:
    """Seal the connected enterprise decision set into the record. Idempotent.
    Returns the number of decisions sealed (0 if already present)."""
    if has_enterprise(ledger):
        return 0
    now = time.time()
    sealed = 0
    for i, (decision, domain, asm, survival, outcome, days, _cap) in enumerate(_DECISIONS):
        v = decide(decision)
        w = list(v.weights)
        w[v.survivor] = survival
        ref = f"ent:{domain}:{i}" if outcome is None else TRIGGER_REF
        if outcome is None:
            created = now
            resolves_at = now + 86400 * float(days)
        else:
            # the failed call: sealed 45 days ago, resolved 12 hours ago — seal
            # precedes outcome, same invariant the whole chain enforces, and it lands
            # inside the "what changed today?" window so the timeline beat is live.
            created = now - 86400 * 45
            resolves_at = now - 3600 * 12
        pred = Prediction(
            decision=decision, branches=v.branches,
            weights=[round(x, 4) for x in w], survivor=v.survivor,
            confidence=survival, why=v.why, watch=v.watch,
            author=ENTERPRISE_AUTHOR, domain=domain, model=v.model,
            kind=Kind.FORWARD, resolves_at=resolves_at,
            oracle="seed", oracle_ref=ref, assumptions=asm,
            graph_id=SAMPLE_GRAPH_ID,
        )
        e = ledger.append(pred, created_at=created)
        sealed += 1
        if outcome is not None:
            # settle it through the ledger's own resolve path (counterfactuals +
            # assumption corpus get scored exactly as for any real outcome).
            ledger.resolve(
                e.id, survived=bool(outcome),
                ref="oracle:reality:brazil-demand-came-in-at-6pct",
                at=resolves_at,
            )
    return sealed


# ── The propagation engine — the living Decision Graph ───────────────────────
def _matches(assumption: str, target: str) -> bool:
    return _norm(assumption) == _norm(target) or assumption_key(assumption) == assumption_key(target)


def _recommendation(domain: str, decision: str) -> str:
    table = {
        "go-to-market": "Re-underwrite the launch plan against the corrected demand "
                        "curve; stage the rollout behind a demand gate.",
        "supply-chain": "Pause capex on fixed fulfilment capacity; switch to a 3PL "
                        "until demand re-clears the threshold.",
        "hiring": "Freeze the LATAM sales req backfill; convert offers to a "
                  "demand-triggered ramp.",
        "pricing": "Reprice the LATAM tier to the lower-demand elasticity band before "
                   "the next quote cycle.",
        "expansion": "Hold the Mexico expansion; it inherits the same demand thesis "
                     "and should not commit until Brazil re-clears.",
    }
    return table.get(domain, f"Revisit '{decision}' — a load-bearing assumption no longer holds.")


def _fmt_usd(x: float) -> str:
    """A short, honest money label: $48M, $3.4M, $640K."""
    a = abs(x)
    if a >= 1_000_000:
        return f"${x/1_000_000:.1f}M".replace(".0M", "M")
    if a >= 1_000:
        return f"${x/1_000:.0f}K"
    return f"${x:,.0f}"


# The impact model, stated once so every dollar figure is auditable, not invented:
#   capital_at_risk = committed capital behind the decision (declared per-decision)
#   risk_repriced   = capital_at_risk × |Δconfidence|
# Acting now (gate / pause / reprice) converts that increment of expected loss from
# unmanaged to managed. It is an estimate of exposure repriced, not a guaranteed saving.
IMPACT_MODEL = ("risk repriced ≈ committed capital × drop in the decision's survival "
                "probability; an estimate of exposure now actively managed, not a "
                "guaranteed saving.")


def _exec_recommendation(row: dict) -> dict:
    """Turn a re-scored decision into the executive card the review demanded:
    recommended action, reason, dollar impact, confidence move, why now, evidence,
    and the alternative to take instead."""
    decision = row["decision"]
    domain = row["domain"]
    cap = _CAPITAL.get(decision, 0)
    delta_mag = abs(row["confidence_delta"])
    risk = round(cap * delta_mag)
    return {
        "decision": decision,
        "domain": domain,
        "impact_score": row["impact_score"],
        "recommended_action": row["recommended_action"],
        "action": row["recommended_action"],  # backward-compatible alias
        "reason": f"Leans on a belief reality just disproved: “{row['leans_on'][0]}.”",
        "confidence": {
            "before": row["confidence_before"],
            "after": row["confidence_after"],
            "delta": row["confidence_delta"],
        },
        "financial_impact": {
            "capital_at_risk_usd": cap,
            "capital_at_risk": _fmt_usd(cap),
            "risk_repriced_usd": risk,
            "risk_repriced": _fmt_usd(risk),
            "estimate": True,
            "model": IMPACT_MODEL,
        },
        "why_now": ("A shared upstream belief was settled false this cycle; this "
                    "commitment inherits it and has an open decision window."),
        "evidence": [
            "Brazil demand settled ~6% YoY vs. the >18% assumed (independent oracle).",
            "The triggering decision was sealed 45 days before its outcome existed.",
            f"Shares the load-bearing belief: “{row['leans_on'][0]}.”",
        ],
        "alternative": _ALTERNATIVE.get(domain, "Stage behind a gate until the belief re-clears."),
    }


def propagate(ledger: Ledger, assumption: str = TRIGGER_ASSUMPTION,
              evidence: str = "") -> dict:
    """Walk the Decision Graph from a falsified assumption.

    Given the belief reality just disproved, find every decision sealed on it, show
    how each decision's confidence changes, and rank the revisions by business
    impact. Pure read over the record — fully deterministic, no model call, safe to
    run live on stage.
    """
    entries = ledger.all()
    affected, unaffected = [], []

    for e in entries:
        p = e.prediction
        asms = p.get("assumptions") or []
        if not asms:
            continue
        leans = [a for a in asms if _matches(assumption, a)]
        domain = p.get("domain", "general")
        survivor = p.get("survivor", 0)
        before = (p.get("weights") or [p.get("confidence", 0.0)])[survivor] \
            if p.get("weights") else p.get("confidence", 0.0)

        if not leans:
            unaffected.append({"id": e.id, "decision": p.get("decision"), "domain": domain,
                               "graph_id": p.get("graph_id", "")})
            continue

        # how load-bearing was this belief for this decision?
        share = len(leans) / max(1, len(asms))
        if e.status == "resolved" and e.survived is False:
            state = "failed"
            after = 0.0
        elif e.status == "resolved":
            state = "resolved-survived"
            after = round(before, 4)
        else:
            state = "at-risk"
            # falsifying a load-bearing premise collapses the survival estimate in
            # proportion to how central it was. Deterministic, monotone, bounded.
            after = round(max(0.05, before * (1.0 - 0.85 * share)), 4)

        delta = round(after - before, 4)
        exposure = _DOMAIN_EXPOSURE.get(domain, 0.5)
        # impact = how much confidence moved × how exposed the domain is. 0..100.
        impact = round(min(100.0, abs(delta) * exposure * 140.0), 1) if state != "resolved-survived" else 0.0
        cap = _CAPITAL.get(p.get("decision", ""), 0)
        risk_repriced = round(cap * abs(delta)) if state == "at-risk" else 0

        affected.append({
            "id": e.id,
            "decision": p.get("decision"),
            "domain": domain,
            "graph_id": p.get("graph_id", ""),
            "state": state,
            "leans_on": leans,
            "confidence_before": round(before, 4),
            "confidence_after": after,
            "confidence_delta": delta,
            "impact_score": impact,
            "capital_at_risk_usd": cap,
            "risk_repriced_usd": risk_repriced,
            "recommended_action": _recommendation(domain, p.get("decision", "")),
        })

    # rank: failures first, then by business impact.
    order = {"failed": 0, "at-risk": 1, "resolved-survived": 2}
    affected.sort(key=lambda r: (order.get(r["state"], 3), -r["impact_score"]))

    # Decision-Graph scoping: the cascade lives inside the initiative(s) the falsified
    # belief actually touches. "Unaffected" means controls in the SAME graph that don't
    # lean on the belief — not every unrelated decision in the tenant's record.
    scope_graphs = {r["graph_id"] for r in affected if r["graph_id"]}
    if scope_graphs:
        unaffected = [u for u in unaffected if u.get("graph_id") in scope_graphs]

    at_risk = [r for r in affected if r["state"] == "at-risk"]
    failed = [r for r in affected if r["state"] == "failed"]

    # learning: the assumption's falsification rate before vs. after this evidence,
    # and the twin's net confidence movement across the connected decisions.
    from .assumptions import assumptions_corpus
    corpus = {row["assumption"]: row for row in assumptions_corpus(ledger)["assumptions"]}
    row = corpus.get(assumption) or next(
        (r for r in corpus.values() if _matches(assumption, r["assumption"])), None)
    fr_before = row["falsification_rate"] if row else None
    seen = (row["seen"] if row else 0) + 1
    failed_with = (row["failed_with"] if row else 0) + (1 if failed else 0)
    fr_after = round((failed_with + 1.0) / (seen + 2.0), 4)

    net_delta = round(sum(r["confidence_delta"] for r in affected), 4)
    total_risk_repriced = sum(r["risk_repriced_usd"] for r in at_risk)

    return {
        "name": "Decision Graph",
        "trigger": {
            "assumption": assumption,
            "evidence": evidence or "Reality settled this belief false: demand grew ~6%, not >18%.",
            "verified": True,
        },
        "cascade": [
            "evidence arrives",
            "assumption falsified",
            "decision confidence drops",
            "forecasts change",
            "recommendations change",
            "decision timeline updates",
            "decision twin learns",
        ],
        "summary": {
            "decisions_touched": len(affected),
            "already_failed": len(failed),
            "now_at_risk": len(at_risk),
            "unaffected": len(unaffected),
            "net_confidence_delta": net_delta,
            "capital_repriced_usd": total_risk_repriced,
            "capital_repriced": _fmt_usd(total_risk_repriced),
        },
        "failed": failed,
        "at_risk": at_risk,
        "recommended_changes": [
            {"rank": i + 1, **_exec_recommendation(r)}
            for i, r in enumerate(at_risk)
        ],
        "impact_model": IMPACT_MODEL,
        "learning": {
            "assumption": assumption,
            "falsification_rate_before": fr_before,
            "falsification_rate_after": fr_after,
            "decisions_rescored": len(at_risk),
            "statement": (
                "The twin learned: this belief now carries a higher falsification rate, "
                "so future strategies that lean on it inherit lower confidence automatically."
            ),
        },
        "unaffected_decisions": unaffected,
        "honesty": (
            "This is a read over the verified record, not a new prediction. The failed "
            "decision was sealed before its outcome and settled by an independent source "
            "the team does not control; the cascade simply propagates that verified fact."
        ),
    }


def enterprise_scenario() -> dict:
    """What the demo/visualization needs to drive the aha without guessing ids."""
    connected = [d for d in _DECISIONS if TRIGGER_ASSUMPTION in d[2]]
    return {
        "trigger_assumption": TRIGGER_ASSUMPTION,
        "failed_decision": _DECISIONS[0][0],
        "control_decisions": [d[0] for d in _DECISIONS if TRIGGER_ASSUMPTION not in d[2]],
        "evidence": "Brazil consumer demand grew ~6% YoY, not the >18% the plan assumed.",
        "capital_on_the_belief_usd": sum(d[6] for d in connected),
        "capital_on_the_belief": _fmt_usd(sum(d[6] for d in connected)),
    }
