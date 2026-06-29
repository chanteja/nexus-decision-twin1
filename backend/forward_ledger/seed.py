# backend/forward_ledger/seed.py
"""
Seeds three honestly-distinct things:

  1. FORWARD / long-horizon — genuinely open questions sealed NOW, resolving in the
     future. They stay PENDING. This is the real forward record; verify the seal,
     come back when reality settles it.
  2. FORWARD / demo-horizon — same mechanism, tiny resolve offset, so a judge can
     fast-forward the demo clock and watch sealed-then-resolved happen live. The
     seal still precedes resolution; nothing is faked.
  3. BACKTEST — historical decisions, labeled hindsight, for context only. Never
     mixed into the forward headline.

The SeedOracle answer key is what settles (1-demo) and (3). The ledger never sees
it at seal time, so the predictor does not grade itself.
"""
from __future__ import annotations

import time

from .ensemble import decide
from .ledger import Kind, Ledger, Prediction
from .oracles import SeedOracle

# ── (3) historical backtest set — labeled hindsight, context only ────────────
# (decision, domain, survived, predicted_survival_prob, oracle_ref)
_BACKTEST = [
    ("Microsoft acquires GitHub ($7.5B, 2018)",            "m&a",      True,  0.82, "bt:msft_github"),
    ("Google launches Google+ to rival Facebook (2011)",   "product",  False, 0.34, "bt:googleplus"),
    ("Apple removes the headphone jack (2016)",            "product",  True,  0.71, "bt:hpjack"),
    ("Amazon ships the Fire Phone (2014)",                 "product",  False, 0.38, "bt:firephone"),
    ("Disney goes direct-to-consumer with Disney+ (2019)", "strategy", True,  0.80, "bt:disneyplus"),
    ("Quibi launches short-form mobile streaming (2020)",  "product",  False, 0.29, "bt:quibi"),
    ("Facebook acquires Instagram ($1B, 2012)",            "m&a",      True,  0.86, "bt:fb_insta"),
    ("Meta bets the company on the metaverse (2021)",      "strategy", False, 0.44, "bt:meta_mv"),
    ("Slack sells to Salesforce ($27.7B, 2021)",           "m&a",      True,  0.74, "bt:slack_sfdc"),
    ("Netflix spins DVDs into 'Qwikster' (2011)",          "strategy", False, 0.33, "bt:qwikster"),
    ("Yahoo passes on buying Google (2002)",               "m&a",      False, 0.21, "bt:yahoo_google"),
    ("Snap rejects Facebook's $3B offer (2013)",           "strategy", True,  0.55, "bt:snap_reject"),
]

# ── (2) demo-horizon forward questions — settle on the demo clock ────────────
# (decision, domain, survived_truth, predicted_survival, oracle_ref)
# Obvious directional calls; their only job is to animate the seal→resolve→score
# loop on stage. Flagged illustrative in the headline — they do not stand in for
# the genuine long-horizon forward record.
_DEMO_FWD = [
    ("Close the Q3 enterprise pricing change before renewal season", "pricing", True, 0.78, "demo:pricing_change",
     ["the team holds scope", "no competitor undercuts first"]),
    ("Consolidate the two LATAM warehouses this quarter",  "supply-chain", True,  0.70, "demo:warehouse_consolidation",
     ["the lease break clears legal", "the demand forecast holds"]),
    ("Launch the new tier on a single unproven channel",   "go-to-market", False, 0.31, "demo:single_channel",
     ["the channel converts as modeled", "the launch window holds"]),
]

# ── (1) long-horizon forward questions — stay PENDING, the real test ─────────
# (decision, domain, days_out, oracle_ref, assumptions) — settled later by HttpOracle
_FWD = [
    ("Enterprise net revenue retention stays above 110% through 2027", "strategy", 540, "polymarket:nrr_110:yes",
     ["downgrades stay below plan", "the expansion motion keeps working"]),
    ("LATAM becomes a top-3 revenue region by 2027", "expansion", 540, "polymarket:latam_top3:yes",
     ["the market-entry thesis holds", "FX stays within the planning band"]),
    ("The strategy team cuts decision-to-commit time below 30 days", "execution", 180, "polymarket:ttc_30:yes",
     ["the twin is adopted org-wide", "reviews move onto the timeline"]),
]


def demo_oracle() -> SeedOracle:
    answers: dict[str, tuple[bool, str]] = {}
    # backtest answers
    for (d, dom, surv, p, ref) in _BACKTEST:
        answers[ref] = (surv, f"public-record:{ref}")
    # demo forward answers
    for (d, dom, surv, p, ref, asm) in _DEMO_FWD:
        answers[ref] = (surv, f"demo-oracle:{ref}")
    return SeedOracle(answers)


def seed(ledger: Ledger, demo: bool = True, demo_horizon_s: float = 8.0) -> None:
    """Populate a fresh ledger. Idempotent-ish: only seeds when empty."""
    if ledger.all():
        return
    now = time.time()

    # (3) backtest — sealed with past created_at, resolves in the past (settles immediately)
    for (d, dom, surv, p, ref) in _BACKTEST:
        v = decide(d)
        # honour the historical authored survival prob on the survivor slot
        w = list(v.weights)
        w[v.survivor] = p
        pred = Prediction(
            decision=d, branches=v.branches, weights=[round(x, 4) for x in w], survivor=v.survivor,
            confidence=p, why=v.why, watch=v.watch, author="nexus-house", domain=dom,
            model=v.model, kind=Kind.BACKTEST, resolves_at=now - 1, oracle="seed", oracle_ref=ref,
        )
        ledger.append(pred, created_at=now - 86400 * 30)  # clearly historical

    if demo:
        # (2) demo-horizon forward — sealed NOW, resolves on the demo clock
        for (d, dom, surv, p, ref, asm) in _DEMO_FWD:
            v = decide(d)
            w = list(v.weights)
            w[v.survivor] = p
            pred = Prediction(
                decision=d, branches=v.branches, weights=[round(x, 4) for x in w], survivor=v.survivor,
                confidence=p, why=v.why, watch=v.watch, author="nexus-house", domain=dom,
                model=v.model, kind=Kind.FORWARD, resolves_at=now + demo_horizon_s,
                oracle="seed", oracle_ref=ref, assumptions=asm,
            )
            ledger.append(pred, created_at=now)

    # (1) long-horizon forward — the genuine open record, stays PENDING
    for (d, dom, days, ref, asm) in _FWD:
        v = decide(d)
        pred = Prediction(
            decision=d, branches=v.branches, weights=v.weights, survivor=v.survivor,
            confidence=v.confidence, why=v.why, watch=v.watch, author="nexus-house", domain=dom,
            model=v.model, kind=Kind.FORWARD, resolves_at=now + 86400 * days,
            oracle="http", oracle_ref=ref, assumptions=asm,
        )
        ledger.append(pred, created_at=now)
