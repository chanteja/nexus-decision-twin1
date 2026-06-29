# backend/forward_ledger/simulation.py
"""
The simulation engine behind Future Explorer — a real probabilistic model of how a
decision survives, not a cosmetic score.

A decision rests on named assumptions. Each assumption i has:
  * prob_i  — probability it HOLDS (sourced from the learned falsification-rate corpus
              when available: prob = 1 - falsification_rate; this is the flywheel —
              every resolved outcome sharpens future simulations);
  * load_i  — how load-bearing it is for THIS decision, in [0, 1].

Model.  Treat each assumption as an independent factor on survival:

    factor_i = 1            if the assumption holds      (prob_i)
             = 1 - load_i   if it is falsified           (1 - prob_i)

    survival = base_survival * Π_i factor_i

Because the factors are independent, the mean and variance have CLOSED FORMS (exact,
no sampling error), while the full outcome DISTRIBUTION (p10/p50/p90) is estimated by
Monte Carlo — which scales linearly with sample count, so "more compute → sharper
tails" is real here.

Sensitivity (the assumptions that matter most) is reported two honest ways:
  * swing_i      — tornado analysis: how far expected survival moves if assumption i
                   flips from certainly-true to certainly-false (others at their mean);
  * variance_share_i — first-order Sobol index: the fraction of total outcome variance
                   attributable to assumption i alone. Closed-form under independence.

Everything is deterministic given a seed, so a result is reproducible and auditable.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Assumption:
    name: str
    prob: float = 0.7      # P(holds)
    load: float = 0.6      # how load-bearing for this decision, [0,1]

    def clamped(self) -> Assumption:
        return Assumption(self.name,
                          min(0.999, max(0.001, float(self.prob))),
                          min(1.0, max(0.0, float(self.load))))


def _factor_moments(a: Assumption) -> tuple[float, float]:
    """E[factor] and E[factor^2] for one assumption's survival factor."""
    p, lo = a.prob, a.load
    lost = 1.0 - lo
    mean = p * 1.0 + (1.0 - p) * lost
    m2 = p * 1.0 + (1.0 - p) * lost * lost
    return mean, m2


def simulate_decision(base_survival: float, assumptions: list[Assumption],
                      n: int = 4000, seed: int = 0) -> dict:
    base = min(1.0, max(0.0, float(base_survival)))
    asms = [a.clamped() for a in assumptions]

    means = [m for (m, _) in (_factor_moments(a) for a in asms)]
    m2s = [m2 for (_, m2) in (_factor_moments(a) for a in asms)]

    prod_mean = 1.0
    for m in means:
        prod_mean *= m
    expected = base * prod_mean

    # exact variance: Var = b^2 (Π E[f^2] - Π E[f]^2)
    prod_m2 = 1.0
    for v in m2s:
        prod_m2 *= v
    variance = base * base * (prod_m2 - prod_mean * prod_mean)
    variance = max(0.0, variance)

    # per-assumption sensitivity (closed form, exact)
    rows = []
    for i, a in enumerate(asms):
        others_mean = prod_mean / means[i] if means[i] else 0.0
        swing = base * a.load * others_mean            # tornado swing
        # first-order Sobol: freeze i to its mean -> its E[f^2] becomes mean^2
        if m2s[i] > 0 and variance > 0:
            prod_m2_wo_i = prod_m2 * (means[i] * means[i]) / m2s[i]
            var_wo_i = base * base * (prod_m2_wo_i - prod_mean * prod_mean)
            share = max(0.0, (variance - var_wo_i) / variance)
        else:
            share = 0.0
        rows.append({"assumption": a.name, "prob_holds": round(a.prob, 4),
                     "load": round(a.load, 4), "swing": round(swing, 4),
                     "variance_share": round(share, 4)})
    rows.sort(key=lambda r: (r["variance_share"], r["swing"]), reverse=True)

    # Monte Carlo for the outcome distribution (tails need sampling)
    rng = random.Random(seed)
    samples = []
    for _ in range(max(1, n)):
        s = base
        for a in asms:
            if rng.random() >= a.prob:      # assumption falsified this draw
                s *= (1.0 - a.load)
        samples.append(s)
    samples.sort()

    def pct(q: float) -> float:
        if not samples:
            return expected
        k = min(len(samples) - 1, max(0, int(q * (len(samples) - 1))))
        return round(samples[k], 4)

    return {
        "expected_survival": round(expected, 4),
        "stdev": round(variance ** 0.5, 4),
        "distribution": {"p10_worst": pct(0.10), "p50_expected": pct(0.50),
                         "p90_best": pct(0.90)},
        "drivers": rows,                       # assumptions ranked by what they move
        "samples": len(samples),
        "model": ("survival = base · Π(assumption factors); factor = 1 if the belief "
                  "holds else 1−load. Independent factors → exact mean/variance, "
                  "sampled tails. Probabilities are learned from resolved outcomes."),
    }


def explore_decision(ledger, decision: str, assumptions: list,
                     base_survival: float | None = None, n: int = 4000,
                     seed: int = 0) -> dict:
    """High-level Future Explorer entry: simulate a decision and its assumptions over
    the twin's LEARNED beliefs. Each assumption's P(holds) defaults to 1 − its
    falsification rate in the record (so the twin's experience shapes the forecast);
    callers may override prob/load per assumption with a dict."""
    from .assumptions import assumptions_corpus
    from .ensemble import decide

    if base_survival is None:
        base_survival = decide(decision).confidence

    corpus = {row["assumption"]: row for row in assumptions_corpus(ledger)["assumptions"]}

    asms: list[Assumption] = []
    n_asm = max(1, len(assumptions))
    for item in assumptions:
        if isinstance(item, dict):
            name = item.get("name", "")
            prob = item.get("prob")
            load = item.get("load")
        else:
            name, prob, load = str(item), None, None
        if prob is None:
            row = corpus.get(name)
            # learned: P(holds) = 1 - falsification_rate; unseen beliefs default to 0.7
            prob = (1.0 - row["falsification_rate"]) if row else 0.7
        if load is None:
            load = round(1.0 / n_asm + 0.3, 4)     # even share, nudged toward load-bearing
        asms.append(Assumption(name=name, prob=float(prob), load=float(load)))

    sim = simulate_decision(base_survival, asms, n=n, seed=seed)
    sim["decision"] = decision
    sim["base_survival"] = round(float(base_survival), 4)
    sim["learning"] = ("Assumption probabilities are drawn from the verified record — "
                       "every resolved outcome makes the next simulation sharper.")
    return sim
