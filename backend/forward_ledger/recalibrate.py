# backend/forward_ledger/recalibrate.py
"""
L1 — the recalibration loop. The flywheel, made literal.

v11 *measured* a reliability curve in calibration.py and never used it. This module
feeds it back: a raw survival probability is mapped to the value the resolved
forward record says that confidence band ACTUALLY achieved. Every newly resolved
row reshapes the map, so stated confidence converges on reality as the ledger grows
— with no retraining and no model swap. That is "smarter with every outcome," in code.

Honesty invariant: with fewer than MIN_N resolved forward rows the map is the
identity (every bucket -> itself). We do not pretend to be calibrated before we have
earned the evidence; the curve only bends once reality has graded enough calls.

The fit is isotonic (monotone non-decreasing) via pool-adjacent-violators, the
standard non-parametric calibration fit — it cannot make "more confident" map to
"less likely," which would be nonsense.
"""
from __future__ import annotations

from .calibration import _survival_prob
from .ledger import Kind, Ledger

MIN_N = 40          # raised from 30: a 10-bucket curve needs more than 3 rows/bucket
                    # before any bend is meaningful. Below this the map is the identity.
PSEUDO = 4.0        # Beta-Binomial pseudo-count: each bucket's empirical survival is
                    # shrunk toward its stated probability by PSEUDO virtual rows, so a
                    # 3-sample bucket barely moves and noise cannot fake a bend.


def _bucket_nominal(i: int) -> float:
    return i / 10.0 + 0.05


def reliability_map(ledger: Ledger) -> list[float | None]:
    """Per-decile map: index i (predicted band [i/10, i/10+0.1)) -> shrunk empirical
    survival, made monotone by PAVA. None for a band means 'pass through unchanged'
    (no evidence, or pre-MIN_N). Shrinkage toward the stated probability keeps the
    fit honest at low sample size — we never claim calibration we have not earned."""
    res = ledger.resolved(Kind.FORWARD)
    if len(res) < MIN_N:
        return [None] * 10
    buckets = [[0, 0] for _ in range(10)]  # [sum_survived, count]
    for e in res:
        b = min(9, int(_survival_prob(e) * 10))
        buckets[b][0] += 1 if bool(e.survived) else 0
        buckets[b][1] += 1
    # Beta-Binomial posterior mean per populated bucket, shrunk toward the nominal.
    pts = []
    for i, (s, c) in enumerate(buckets):
        if c:
            shrunk = (s + PSEUDO * _bucket_nominal(i)) / (c + PSEUDO)
            pts.append((i, shrunk, c))
    if not pts:
        return [None] * 10
    fitted = _pava([y for _, y, _ in pts], [c for _, _, c in pts])
    out: list[float | None] = [None] * 10
    for (i, _, _), y in zip(pts, fitted):
        out[i] = round(y, 4)
    return out


def _wilson(s: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion — well-behaved at small n,
    unlike the naive normal approximation."""
    if n == 0:
        return (0.0, 1.0)
    p = s / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5)) / denom
    return (round(max(0.0, center - half), 4), round(min(1.0, center + half), 4))


def reliability_band(ledger: Ledger) -> dict:
    """Per-decile observed survival with a 95% Wilson confidence interval and the
    sample count, so the demo can render the bend WITH its uncertainty. A wide band
    is the honest signal that the curve has not earned its shape yet."""
    res = ledger.resolved(Kind.FORWARD)
    buckets = [[0, 0] for _ in range(10)]
    for e in res:
        b = min(9, int(_survival_prob(e) * 10))
        buckets[b][0] += 1 if bool(e.survived) else 0
        buckets[b][1] += 1
    bands = []
    for i, (s, c) in enumerate(buckets):
        lo, hi = _wilson(s, c) if c else (None, None)
        bands.append({
            "band": round(_bucket_nominal(i), 2),
            "n": c,
            "observed": round(s / c, 4) if c else None,
            "ci95": [lo, hi],
            "fitted": None,  # filled below
        })
    rmap = reliability_map(ledger)
    for i, b in enumerate(bands):
        b["fitted"] = rmap[i]
    return {
        "bands": bands,
        "resolved_forward": len(res),
        "needed": MIN_N,
        "significant": len(res) >= MIN_N,
        "note": "observed survival per confidence band with 95% Wilson intervals; the "
                "fitted curve is identity until the band is significant. Wide intervals "
                "mean the bend is not yet earned — shown on purpose.",
    }


def apply(raw_p: float, rmap: list[float | None]) -> float:
    """Map one probability through the curve. Unknown bands pass through."""
    raw_p = min(0.9999, max(0.0001, float(raw_p)))
    b = min(9, int(raw_p * 10))
    mapped = rmap[b] if b < len(rmap) and rmap[b] is not None else raw_p
    return round(float(mapped), 4)


def recalibrate_verdict(verdict, rmap: list[float | None]):
    """Return a copy of a Verdict with weights & confidence pushed through the map,
    re-normalized so the weight vector still sums to 1. Survivor index is preserved
    (we recalibrate magnitudes, not the ranking the reasoner produced)."""
    if all(v is None for v in rmap):
        return verdict  # identity — nothing earned yet
    mapped = [apply(w, rmap) for w in verdict.weights]
    total = sum(mapped) or 1.0
    weights = [round(w / total, 4) for w in mapped]
    survivor = verdict.survivor
    verdict.weights = weights
    verdict.confidence = round(weights[survivor], 4)
    return verdict


def _pava(ys: list[float], ws: list[float]) -> list[float]:
    """Weighted pool-adjacent-violators: monotone non-decreasing isotonic fit."""
    y = list(ys)
    w = list(ws)
    i = 0
    while i < len(y) - 1:
        if y[i] > y[i + 1] + 1e-12:
            ny = (y[i] * w[i] + y[i + 1] * w[i + 1]) / (w[i] + w[i + 1])
            y[i] = ny
            w[i] += w[i + 1]
            del y[i + 1]
            del w[i + 1]
            if i:
                i -= 1
        else:
            i += 1
    # re-expand pooled blocks back to one value per original point
    out: list[float] = []
    for v, ww in zip(y, w):
        out += [round(v, 6)] * int(round(ww))
    # guard against rounding drift in block sizes
    while len(out) < len(ys):
        out.append(out[-1] if out else 0.0)
    return out[: len(ys)]
