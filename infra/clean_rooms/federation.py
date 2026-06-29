# infra/clean_rooms/federation.py
"""
AWS Clean Rooms federation — the enterprise network effect, made privacy-safe.

The problem: organizations will never upload raw strategic decisions to a shared
service. The unlock: AWS Clean Rooms lets two parties run an agreed analysis over
each other's data WITHOUT either side seeing the other's rows. NEXUS uses it to
compute JOINT calibration across tenants — every org that joins sharpens the shared
forecast-accuracy model, and none exposes a single decision. Switching cost rises
with every contributing org; that is a moat a single-LLM vendor cannot build.

This module models the collaboration analysis rule (the SQL that both parties
approve) and a local simulation of the join so the mechanism is demonstrable
offline. In production the same query runs inside a Clean Rooms collaboration.
"""
from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass


def _laplace(scale: float, rng: random.Random) -> float:
    """Inverse-CDF Laplace sample with the given scale (b)."""
    if scale <= 0:
        return 0.0
    u = rng.random() - 0.5
    return -scale * math.copysign(1.0, u) * math.log(1.0 - 2.0 * abs(u))


def _rng(rng: random.Random | None) -> random.Random:
    return rng if rng is not None else random.Random(int.from_bytes(os.urandom(8), "big"))


def dp_mean(total: float, n: int, epsilon: float, sensitivity: float,
            rng: random.Random) -> float:
    """ε-differentially-private mean of per-record values bounded in [0, sensitivity].
    The mean's sensitivity to one record is sensitivity/n, so Laplace scale =
    (sensitivity / n) / ε. Result is clamped to [0, 1]. Min-cell suppression bounds n
    away from 0, keeping the noise finite and the released value useful."""
    noisy = (total / n) + _laplace((sensitivity / n) / epsilon, rng)
    return min(1.0, max(0.0, noisy))

# The analysis rule both tenants approve. Aggregate-only: no raw decision text or
# author leaves either account; only bucketed, count-thresholded calibration does.
ANALYSIS_RULE = """
SELECT  predicted_bucket,
        COUNT(*)                AS n,
        AVG(CAST(survived AS DOUBLE)) AS actual_survival
FROM    forward_ledger_resolved
WHERE   kind = 'forward'
GROUP BY predicted_bucket
HAVING  COUNT(*) >= 5          -- aggregation constraint: no small-cell re-identification
"""


@dataclass
class TenantContribution:
    tenant: str
    # predicted_bucket (0..9) -> (n, sum_survived); raw rows never leave the tenant
    buckets: dict[int, tuple[int, int]]


def joint_calibration(contributions: list[TenantContribution], min_cell: int = 5,
                      epsilon: float = 1.0, rng: random.Random | None = None) -> dict:
    """The output Clean Rooms returns to both parties: a joint reliability curve, made
    ε-differentially private. Each tenant sees the shared curve, never the other's rows;
    DP noise additionally bounds what a differencing attack can infer about any one row."""
    R = _rng(rng)
    merged: dict[int, list[int]] = {}
    for c in contributions:
        for b, (n, s) in c.buckets.items():
            agg = merged.setdefault(b, [0, 0])
            agg[0] += n
            agg[1] += s
    curve = []
    for b in range(10):
        n, s = merged.get(b, [0, 0])
        if n >= min_cell:                      # k-anonymity: suppress small cells
            curve.append({"bucket": round(b / 10 + 0.05, 2), "n": n,
                          "actual_survival": round(dp_mean(s, n, epsilon, 1.0, R), 3)})
    return {
        "tenants": [c.tenant for c in contributions],
        "joint_reliability": curve,
        "privacy": (f"ε-DP (Laplace) · ε={epsilon}/cell · min cell {min_cell} · "
                    "aggregate-only · no raw decision left any account"),
        "dp": {"mechanism": "laplace", "epsilon_per_cell": epsilon,
               "epsilon_total": round(epsilon * len(curve), 4), "released_cells": len(curve)},
        "effect": "every joining org sharpens the shared model; none exposes a decision",
    }


# ── second analysis rule: federate the UN-copyable assets, not just buckets ───
# v11 federated only the reliability curve — a thing any vendor can approximate. The
# real enterprise moat is the joint COUNTERFACTUAL regret (which strategic patterns
# fail across the industry) and joint QUESTION CONSENSUS (where good forecasters
# collectively land before outcomes exist). Pooling these — count-thresholded, raw
# rows never leaving any account — is the switching cost a single-LLM vendor cannot
# build, and it is AWS Clean Rooms-exclusive.
ANALYSIS_RULE_COUNTERFACTUAL = """
SELECT  domain,
        COUNT(*)                       AS n_branches,
        AVG(regret)                    AS mean_regret
FROM    counterfactual_corpus
WHERE   was_taken = false
GROUP BY domain
HAVING  COUNT(*) >= 8          -- no small-cell re-identification of any decision
"""

ANALYSIS_RULE_CONSENSUS = """
SELECT  question_id,
        COUNT(*)                       AS n_forecasts,
        AVG(survival_prob)             AS consensus
FROM    forward_ledger_pending
WHERE   kind = 'forward'
GROUP BY question_id
HAVING  COUNT(*) >= 5
"""


@dataclass
class TenantCounterfactuals:
    tenant: str
    # domain -> (n_untaken_branches, sum_regret); raw branch rows never leave the tenant
    domains: dict[str, tuple[int, float]]


def joint_counterfactual_regret(contributions: list["TenantCounterfactuals"],
                                min_cell: int = 8, epsilon: float = 1.0,
                                rng: random.Random | None = None) -> dict:
    """The industry's shared map of which strategic patterns fail — pooled across
    tenants, ε-DP, exposing no single decision. The output both parties receive."""
    R = _rng(rng)
    merged: dict[str, list[float]] = {}
    for c in contributions:
        for dom, (n, sreg) in c.domains.items():
            agg = merged.setdefault(dom, [0.0, 0.0])
            agg[0] += n
            agg[1] += sreg
    out = []
    for dom, (n, sreg) in merged.items():
        if n >= min_cell:                      # k-anonymity: suppress small cells
            out.append({"domain": dom, "n_branches": int(n),
                        "mean_regret": round(dp_mean(sreg, int(n), epsilon, 1.0, R), 4)})
    out.sort(key=lambda x: x["mean_regret"], reverse=True)
    return {
        "tenants": [c.tenant for c in contributions],
        "joint_regret_by_domain": out,
        "privacy": (f"ε-DP (Laplace) · ε={epsilon}/cell · min cell {min_cell} · "
                    "aggregate-only · no branch row left any account"),
        "dp": {"mechanism": "laplace", "epsilon_per_cell": epsilon,
               "epsilon_total": round(epsilon * len(out), 4), "released_cells": len(out)},
        "effect": "every joining org sharpens the shared failure model; switching cost "
                  "rises with each participant — a moat a single-LLM vendor cannot build",
    }


ANALYSIS_RULE_REPUTATION = """
SELECT  question_type,
        COUNT(*)                       AS n_resolved,
        AVG(brier)                     AS mean_brier
FROM    forward_ledger_resolved
WHERE   kind = 'forward'
GROUP BY question_type
HAVING  COUNT(*) >= 5          -- no small-cell re-identification of any forecaster
"""


@dataclass
class TenantReputation:
    tenant: str
    # question_type/domain -> (n_resolved, sum_brier); raw forecaster rows never leave
    types: dict[str, tuple[int, float]]


def joint_reputation_by_type(contributions: list["TenantReputation"],
                             min_cell: int = 5, epsilon: float = 1.0,
                             rng: random.Random | None = None) -> dict:
    """The strongest enterprise asset to federate: the cohort's joint calibration by
    QUESTION TYPE — i.e. which kinds of bets this industry systematically misjudges.
    Far more valuable than a shared reliability curve, still aggregate-only: no
    forecaster and no decision leaves any account, only bucketed, count-thresholded
    Brier per type. Each org that joins sharpens the shared 'what we collectively get
    wrong' map and cannot extract its own contribution back out — the switching cost."""
    R = _rng(rng)
    merged: dict[str, list[float]] = {}
    for c in contributions:
        for qt, (n, sb) in c.types.items():
            agg = merged.setdefault(qt, [0.0, 0.0])
            agg[0] += n
            agg[1] += sb
    out = []
    for qt, (n, sb) in merged.items():
        if n >= min_cell:
            mb = round(dp_mean(sb, int(n), epsilon, 1.0, R), 4)
            out.append({"question_type": qt, "n_resolved": int(n),
                        "mean_brier": mb, "systematically_misjudged": mb > 0.25})
    out.sort(key=lambda x: x["mean_brier"], reverse=True)
    return {
        "tenants": [c.tenant for c in contributions],
        "joint_reputation_by_type": out,
        "dp": {"mechanism": "laplace", "epsilon_per_cell": epsilon,
               "epsilon_total": round(epsilon * len(out), 4), "released_cells": len(out)},
        "privacy": (f"ε-DP (Laplace) · ε={epsilon}/cell · min cell {min_cell} · "
                    "aggregate-only · no forecaster row left any account"),
        "effect": "the cohort learns which question types it collectively misjudges; "
                  "each org sharpens it and cannot extract its share back — the switching cost",
    }


if __name__ == "__main__":
    # offline demonstration of the mechanism
    t1 = TenantContribution("acme_corp", {7: (12, 9), 8: (8, 7), 3: (10, 3)})
    t2 = TenantContribution("globex",    {7: (9, 7), 8: (11, 10), 2: (6, 1)})
    import json
    print(json.dumps(joint_calibration([t1, t2]), indent=2))
    r1 = TenantReputation("acme_corp", {"m&a": (14, 1.9), "product": (9, 2.4)})
    r2 = TenantReputation("globex",    {"m&a": (11, 1.4), "strategy": (7, 1.1)})
    print(json.dumps(joint_reputation_by_type([r1, r2]), indent=2))
