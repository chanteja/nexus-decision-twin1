# backend/forward_ledger/arena_seed.py
"""
The Reality Arena cohort — an AGED, multi-forecaster demo population so the
Human-vs-AI leaderboard and the seal -> resolve -> score beat are ALIVE on stage.

────────────────────────────────────────────────────────────────────────────
HONESTY NOTE — read this, it is the whole point of the project.

These rows are SEEDED for the demo. Their seal times are backdated ~30 days and
they settle from a fixed SeedOracle answer key the cohort never saw at seal time —
so the sealed-BEFORE-resolved ordering is real and `Ledger.verify()` still passes.
But a backdated `created_at` is NOT the same thing as a cryptographically anchored
30-day-old seal. So:

  * The ARENA is the SPECTACLE — a populated Human-vs-AI board that moves on stage.
    Every arena row carries an "arena:" oracle_ref and is reported `cohort: "demo"`;
    the leaderboard and the calibration headline both say so. We never pass it off
    as the externally-anchored forward record.
  * The PROOF is `seal_live.py` — ONE genuine bound call, anchored to OpenTimestamps
    days before finals, that a judge verifies on their own phone. That beat is real.

Two horizons (same pattern as seed.py):
  * already-due  -> resolvable the instant you POST /v1/prove (the board populates)
  * live-horizon -> resolves a few seconds into the demo, so a judge WATCHES a score move
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import hashlib
import time

from .ledger import Kind, Ledger, Prediction
from .oracles import SeedOracle

ARENA_PREFIX = "arena:"
_AGE_S = 30 * 86400          # seals are ~30 days old
_DUE_BACK_S = 120            # already-due rows resolve the moment /v1/prove runs
_HELD_S = 10 * 365 * 86400   # "live" rows are held far out, released on operator command

# the two questions held back for the on-stage "release reality" beat
LIVE_REFS = ["arena:apple_ai", "arena:mars_crew"]

# Five forecasters competing on the same canonical questions. Probabilities chosen
# so the board is a CLOSE race, not a blowout: a sharp human expert edges the best
# model, the models beat the crowd, the crowd hovers near a coin flip.
FORECASTERS = ["human-expert", "claude", "gpt", "gemini", "student-team"]

# (ref, headline, domain, truth, {forecaster: survival_prob}, live?)
# truth = did the "happens" branch (survivor=0) actually occur.
_Q = [
    ("arena:gpu_demand", "Data-center GPU demand keeps rising through the period", "tech", True,
     {"human-expert": .85, "claude": .82, "gpt": .78, "gemini": .69, "student-team": .55}, False),
    ("arena:rate_cut", "The central bank cuts rates at the next meeting", "macro", False,
     {"human-expert": .28, "claude": .30, "gpt": .44, "gemini": .58, "student-team": .62}, False),
    ("arena:orbital_test", "The flagship rocket completes its orbital test", "space", True,
     {"human-expert": .74, "claude": .66, "gpt": .71, "gemini": .60, "student-team": .50}, False),
    ("arena:ai_regulation", "Major AI regulation takes force in the region this year", "policy", True,
     {"human-expert": .80, "claude": .77, "gpt": .64, "gemini": .72, "student-team": .58}, False),
    ("arena:open_model_top", "An open model tops the closed leaderboard this quarter", "ai", False,
     {"human-expert": .33, "claude": .35, "gpt": .52, "gemini": .61, "student-team": .57}, False),
    ("arena:btc_ath", "The benchmark asset prints a new all-time high", "markets", True,
     {"human-expert": .62, "claude": .59, "gpt": .55, "gemini": .66, "student-team": .49}, False),
    ("arena:layoffs", "A new wave of big-tech layoffs lands in the quarter", "tech", True,
     {"human-expert": .76, "claude": .71, "gpt": .60, "gemini": .57, "student-team": .52}, False),
    ("arena:fusion_net", "A fusion reactor reaches sustained net energy gain", "science", False,
     {"human-expert": .19, "claude": .22, "gpt": .38, "gemini": .49, "student-team": .55}, False),
    ("arena:apple_ai", "The major consumer firm ships its on-device AI feature", "tech", True,
     {"human-expert": .70, "claude": .68, "gpt": .73, "gemini": .58, "student-team": .53}, True),
    ("arena:mars_crew", "A crewed mission to Mars is announced for before 2030", "space", False,
     {"human-expert": .21, "claude": .24, "gpt": .41, "gemini": .52, "student-team": .60}, True),
]


def arena_answers() -> dict[str, tuple[bool, str]]:
    """The SeedOracle key for the arena. The cohort never sees this at seal time."""
    return {ref: (truth, f"arena-oracle:{ref}") for (ref, _h, _d, truth, _p, _live) in _Q}


def arena_oracle(base: SeedOracle | None = None) -> SeedOracle:
    """A SeedOracle that can settle the arena (merged with any base demo answers)."""
    if isinstance(base, SeedOracle):
        base.extend(arena_answers())
        return base
    return SeedOracle(arena_answers())


def has_arena(ledger: Ledger) -> bool:
    return any(e.prediction.get("oracle_ref", "").startswith(ARENA_PREFIX) for e in ledger.all())


def _seal_offset(author: str, ref: str) -> float:
    """Deterministic per-(author,question) jitter inside the ~30-day-ago window, so
    different forecasters seal at different times and 'first-to-be-right' is real."""
    h = int(hashlib.sha256((author + "|" + ref).encode("utf-8")).hexdigest()[:6], 16)
    return (h % 4000) + 60.0      # 60s .. ~67min spread


def seed_arena(ledger: Ledger, live_horizon_s: float = 6.0) -> int:
    """Populate the Human-vs-AI arena. Idempotent: no-op if arena rows already exist.
    Returns the number of rows sealed. `live_horizon_s` is kept for API compatibility
    but the live questions are HELD (released via resolve_live) so the on-stage beat
    does not depend on how long the server has been running."""
    if has_arena(ledger):
        return 0
    now = time.time()
    base_seal = now - _AGE_S
    sealed = 0
    for (ref, headline, domain, truth, probs, live) in _Q:
        resolves_at = (now + _HELD_S) if live else (now - _DUE_BACK_S)
        for author in FORECASTERS:
            p = float(probs[author])
            pred = Prediction(
                decision=headline,
                branches=[headline + " — happens", headline + " — does not"],
                weights=[round(p, 4), round(1 - p, 4)],
                survivor=0,
                confidence=round(p, 4),
                why="sealed before the outcome; settled by an oracle the cohort does not control",
                watch="the other branch wins if the catalyst slips",
                author=author, domain=domain, model=("manual" if kind_is_human(author) else author),
                kind=Kind.FORWARD, resolves_at=resolves_at,
                oracle="seed", oracle_ref=ref,
            )
            created = base_seal + _seal_offset(author, ref)
            ledger.append(pred, created_at=created)
            sealed += 1
    return sealed


def resolve_live(ledger: Ledger, oracle, now: float | None = None) -> list[dict]:
    """Release the HELD live questions on operator command — the on-stage 'reality
    arrives' beat. Settles every pending arena row on a LIVE_REF using the oracle
    (the predictor still never grades itself), at wall-clock now. Seal < resolution
    holds because the seals are ~30 days old."""
    now = now if now is not None else time.time()
    settled = []
    for e in ledger.pending():
        p = e.prediction
        ref = p.get("oracle_ref", "")
        if ref in LIVE_REFS:
            ans = oracle.settle(ref)
            if ans is None:
                continue
            survived, evidence = ans
            ledger.resolve(e.id, survived, evidence, at=now)
            settled.append({"id": e.id, "author": p.get("author"),
                            "survived": survived, "evidence": evidence})
    return settled


def kind_is_human(author: str) -> bool:
    return author in ("human-expert", "student-team")
