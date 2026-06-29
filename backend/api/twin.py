# backend/api/twin.py
"""
NEXUS · The Decision Twin — the product surface.

This module is the ONLY thing a user (or a judge) is meant to understand. It
exposes the platform as exactly five pillars and nothing else:

    1. Decision Twin        /twin                  — the living state of how an
                                                      organization decides + one
                                                      unified Decision Confidence.
    2. Decision Graph       /twin/graph            — the single canonical model of
                                                      decisions, assumptions, evidence,
                                                      outcomes and the edges between them.
    3. Future Explorer      /twin/futures          — reason over a decision: forecasts,
                                                      simulations, alternative futures,
                                                      counterfactuals.
    4. Reality Verification /twin/verification     — evidence → verification →
                                                      confidence → certificate → learning.
                                                      The phone-verifiable proof.
    5. Decision Timeline    /twin/timeline         — one time axis: past (resolved),
                                                      present (sealed/pending), future
                                                      (next resolutions).

Every pillar delegates to the existing forward-ledger implementation. The words
"engine", "ledger", "GraphRAG", "calibration", "Brier", "trust graph" never appear
in a response body. Those are internal modules, not product concepts.

Mounted ALONGSIDE the original /v1/* contract — the landing and the demo pages keep
working unchanged. Nothing here removes a working endpoint; it reframes the surface.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from forward_ledger import (
    TRIGGER_ASSUMPTION,
    Kind,
    Ledger,
    apply_learning,
    assumptions_corpus,
    build_graph,
    calibration,
    consensus_forecast,
    counterfactuals,
    enterprise_scenario,
    explore_decision,
    graphs_summary,
    movers,
    propagate,
    reality_score,
    reliability_band,
    run_pipeline,
    value_summary,
)
from forward_ledger import (
    decide as run_ensemble,
)

router = APIRouter(prefix="/twin", tags=["Decision Twin"])


def _dep():
    """The real auth+tenant dependency, indirected through app to avoid an import cycle."""
    from .app import tenant_ledger
    return tenant_ledger

# The five pillars, and the internal modules each one hides. This is the single
# source of truth for "what is visible vs. what is implementation."
PILLARS: dict[str, list[str]] = {
    "Decision Twin": ["ensemble", "recalibrate", "calibration", "trust", "reality_score"],
    "Decision Graph": ["graph", "graphrag-retrieval", "questions"],
    "Future Explorer": ["ensemble", "counterfactual", "markets", "consensus"],
    "Reality Verification": ["ledger", "anchor", "resolver", "oracles", "assumptions"],
    "Decision Timeline": ["ledger"],
}


def _round(x, n=4):
    return round(x, n) if isinstance(x, (int, float)) else x


# ── Decision Confidence ──────────────────────────────────────────────────────
# The merge the review demanded: Reality Score + Trust Score + Confidence +
# Calibration collapse into ONE legible object with four honest sub-signals.
def decision_confidence(ledger: Ledger) -> dict:
    cal = calibration(ledger)
    band = reliability_band(ledger)
    cfs = assumptions_corpus(ledger)

    fwd = cal["forward"]
    accuracy = fwd.get("accuracy")                  # resolved-only forward accuracy
    n_resolved = fwd.get("n", 0)
    calibrated = bool(band.get("significant"))      # has the curve earned its shape?

    # evidence quality: share of resolved forward calls that carry a hashed
    # resolution evidence record (the "don't trust us" guarantee).
    resolved = ledger.resolved(Kind.FORWARD)
    with_evidence = sum(1 for e in resolved if getattr(e, "resolution_evidence_hash", None))
    evidence_quality = (with_evidence / len(resolved)) if resolved else None

    # assumption stability: 1 − falsification rate of the beliefs the sealed bets
    # leaned on. Higher = the twin's premises have held up against reality.
    rows = cfs.get("assumptions", [])
    if rows:
        fail = sum(r.get("failed_with", 0) for r in rows)
        tested = sum(r.get("seen", 0) for r in rows)
        assumption_stability = max(0.0, 1.0 - (fail / tested)) if tested else None
    else:
        assumption_stability = None

    # one number, only when there is a real track record to earn it.
    parts = [p for p in (accuracy,
                         (1.0 if calibrated else None) if calibrated is not None else None,
                         evidence_quality,
                         assumption_stability) if isinstance(p, (int, float))]
    score = round(sum(parts) / len(parts), 4) if parts and n_resolved else None

    return {
        "score": score,
        "earned": bool(n_resolved),
        "components": {
            "forecast_accuracy": _round(accuracy),
            "historical_calibration": {
                "significant": calibrated,
                "resolved_forward": n_resolved,
                "needed": band.get("needed"),
            },
            "evidence_quality": _round(evidence_quality),
            "assumption_stability": _round(assumption_stability),
        },
        "honesty": (
            "Decision Confidence is unscored until sealed forward calls actually "
            "resolve against reality. A fresh twin says so rather than inventing a number."
        ),
    }


# ── Pillar 1 · Decision Twin ─────────────────────────────────────────────────
@router.get("")
@router.get("/")
def twin(lg: Ledger = Depends(_dep())):
    d = lg.digest()
    board = reality_score(lg)["leaderboard"]
    self_row = next((r for r in board if r["forecaster"] == "nexus-ensemble"), None)
    return {
        "name": "Decision Twin",
        "statement": (
            "A living model of how this organization decides — what it believes, "
            "why, what it expects to happen, and how often reality has agreed."
        ),
        "decisions_on_record": d["entries"],
        "integrity": {"intact": d["chain_valid"], "fingerprint": d["merkle_root"]},
        "confidence": decision_confidence(lg),
        "self": self_row,
        "pillars": list(PILLARS.keys()),
    }


# ── Pillar 2 · Decision Graph ────────────────────────────────────────────────
@router.get("/graph")
def graph(limit: int = 400, lg: Ledger = Depends(_dep())):
    g = build_graph(lg, limit=limit)
    g["influencers"] = movers(lg, top=10)["reality_movers"]
    g["meaning"] = (
        "One graph for the whole organization: decisions, the assumptions they rest "
        "on, the evidence that supports them, and the outcomes that settled them."
    )
    return g


# ── Pillar 2 (live) · the graph reacts — the aha moment ──────────────────────
@router.get("/graph/propagate")
def graph_propagate(assumption: str = TRIGGER_ASSUMPTION, evidence: str = "",
                    lg: Ledger = Depends(_dep())):
    """The living Decision Graph. Give it a belief reality just disproved and it
    walks every connected decision, drops the confidence of the ones that leaned on
    that belief, ranks the revisions they now need by business impact, and records
    what the twin learned. This is the unforgettable beat: one falsified assumption
    re-scores the whole strategy in real time."""
    return propagate(lg, assumption=assumption, evidence=evidence)


@router.get("/pipeline")
def pipeline(decision: str, constraint: str = "", assumptions: str = "",
             samples: int = 4000, lg: Ledger = Depends(_dep())):
    """The full Decision pipeline in one call: Intent → Knowledge Extraction → Decision
    Memory → Graph → Future Explorer → Recommendation → (next) Reality Verification →
    Learning. Exploration only — sealing is a separate, deliberate step."""
    named = [a.strip() for a in assumptions.split(",") if a.strip()]
    return run_pipeline(lg, decision, constraint=constraint,
                        assumptions=named or None, n=max(200, min(50000, samples)))


@router.get("/graphs")
def graphs(lg: Ledger = Depends(_dep())):
    """Decision Memory: every Decision Graph (initiative) in this organisation's record,
    with its size and the beliefs it rests on. Related decisions share a graph so a
    falsified belief cascades across the whole connected strategy."""
    return graphs_summary(lg)


@router.get("/graph/scenario")
def graph_scenario():
    """The canonical enterprise scenario the demo drives (so the UI never guesses)."""
    return enterprise_scenario()


# ── Pillar 3 · Future Explorer ───────────────────────────────────────────────
@router.get("/futures")
def futures(decision: str, constraint: str = "", branches: int = 7,
            oracle_ref: str = "", domain: str | None = None,
            assumptions: str = "", samples: int = 4000,
            lg: Ledger = Depends(_dep())):
    """Explore a decision without committing it: the ensemble reasons it out, the
    twin recalibrates the call against its own resolved track record, and (if a
    crowd exists on this question) the calibration-weighted consensus is shown as a
    competing future. Pure exploration — call /twin/verification to put it on record."""
    branches = max(2, min(int(branches), 7))      # bound: never an empty/oversized fan-out
    v = run_ensemble(decision, constraint, branches)
    v = apply_learning(v, lg, decision, oracle_ref)
    cf_rows = counterfactuals(lg, domain=domain, limit=12)["rows"]
    alt_futures = [
        {
            "future": r.get("branch"),
            "considered_weight": r.get("branch_prob"),
            "regret": r.get("regret"),
            "domain": r.get("domain"),
        }
        for r in cf_rows
    ]
    out = {
        "decision": decision,
        "recommended_future": v.branches[v.survivor] if v.branches else None,
        "survival": v.confidence,
        "futures": [{"future": b, "weight": w} for b, w in zip(v.branches, v.weights)],
        "why": v.why,
        "watch": v.watch,
        "alternative_futures": alt_futures,
    }
    # Real probabilistic simulation when the caller names the assumptions the decision
    # rests on: a sampled outcome distribution + which assumptions actually drive it.
    named = [a.strip() for a in assumptions.split(",") if a.strip()]
    if named:
        out["simulation"] = explore_decision(lg, decision, named,
                                              base_survival=v.confidence,
                                              n=max(200, min(50000, samples)))
    if oracle_ref:
        cf = consensus_forecast(lg, decision, oracle_ref)
        if cf:
            out["consensus_future"] = {"survival": cf["survival"], "peers": cf["n_peers"]}
    return out


# ── Pillar 4 · Reality Verification ──────────────────────────────────────────
@router.get("/verification")
def verification(lg: Ledger = Depends(_dep())):
    """The state of the proof: how many decisions are sealed-and-waiting, how many
    reality has already settled, the unified Decision Confidence, and the beliefs
    most often falsified by reality. The phone-verify proof lives at /v1/verify/{id}."""
    cal = calibration(lg)
    d = lg.digest()
    return {
        "name": "Reality Verification",
        "flow": ["evidence", "verification", "decision confidence", "certificate", "learning"],
        "sealed_pending": cal["forward"].get("sealed_pending"),
        "resolved": cal["forward"].get("n"),
        "next_resolution_at": cal["forward"].get("next_resolution_at"),
        "confidence": decision_confidence(lg),
        "fragile_assumptions": assumptions_corpus(lg, limit=8)["assumptions"],
        "integrity": {"intact": d["chain_valid"], "fingerprint": d["merkle_root"]},
        "proof": {
            "claim": "Every sealed decision is fingerprinted before its outcome exists "
                     "and the chain's root is timestamped by an authority we do not "
                     "control. A stranger verifies it without trusting us.",
            "verify_one": "/v1/verify/{id}",
            "verify_on_phone": "/v1/verify/{id}/qr",
        },
    }


# ── Pillar 5 · Decision Timeline ─────────────────────────────────────────────
@router.get("/value")
def value(analyst_hourly_usd: float = 150.0, hours_per_review: float = 40.0,
          reviews_per_year: int = 12, automation_fraction: float = 0.7,
          lg: Ledger = Depends(_dep())):
    """Business impact, measured from the record (coverage, audit readiness, verification
    rate, capital at risk) plus a parameterised ROI estimate with its inputs declared."""
    return value_summary(lg, analyst_hourly_usd=analyst_hourly_usd,
                         hours_per_review=hours_per_review, reviews_per_year=reviews_per_year,
                         automation_fraction=automation_fraction)


@router.get("/timeline")
def timeline(limit: int = 120, lg: Ledger = Depends(_dep())):
    """One time axis. Past = decisions reality has settled. Present = sealed and
    waiting. Future = the next outcomes due. The merge of replay + history + the
    'decision time machine' into a single ordered stream."""
    now = time.time()
    past, present, future = [], [], []
    for e in lg.all()[-limit:]:
        p = e.prediction
        row = {
            "id": e.id,
            "decision": p.get("decision"),
            "author": p.get("author"),
            "sealed_at": e.created_at,
            "survival": p["weights"][p["survivor"]] if p.get("weights") else p.get("confidence"),
        }
        if e.status == "resolved" or e.resolved_at:
            row["resolved_at"] = e.resolved_at
            row["survived"] = e.survived
            past.append(row)
        else:
            row["resolves_at"] = p.get("resolves_at")
            present.append(row)
            if p.get("resolves_at"):
                future.append({"id": e.id, "decision": p.get("decision"),
                               "resolves_at": p.get("resolves_at"),
                               "in_s": round(float(p["resolves_at"]) - now, 1)})
    future.sort(key=lambda r: (r["resolves_at"] is None, r["resolves_at"]))

    # "What's changed today?" — the reason an executive opens NEXUS every morning.
    day = 86400.0
    settled_recently = [r for r in past if r.get("resolved_at") and (now - r["resolved_at"]) <= day]
    resolving_soon = [r for r in future if r.get("resolves_at") and (float(r["resolves_at"]) - now) <= 7 * day]
    surprises = [r for r in settled_recently if r.get("survived") is False]
    changes_today = {
        "headline": (
            f"{len(settled_recently)} decision(s) settled, "
            f"{len(surprises)} against expectation, "
            f"{len(resolving_soon)} resolving within 7 days."
        ),
        "newly_settled": settled_recently,
        "against_expectation": surprises,
        "resolving_this_week": resolving_soon,
        "prompt": "Ask Future Explorer what to change, or open the Decision Graph to see "
                  "what a settled outcome just propagated to.",
    }

    return {
        "name": "Decision Timeline",
        "question": "What's changed today?",
        "changes_today": changes_today,
        "past": past,
        "present": present,
        "future": future[:20],
        "now": now,
    }
