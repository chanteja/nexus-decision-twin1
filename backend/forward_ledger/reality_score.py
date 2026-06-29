# backend/forward_ledger/reality_score.py
"""
The Reality Score — ONE legible number per forecaster.

The Trust Graph already computes the right statistic (difficulty-weighted,
calibration-shrunk Brier, plus first-to-be-right). But a judge cannot read a Brier
score in fifteen seconds. The Reality Score collapses that statistic into a single
ELO-style integer that rises ONLY when a forecaster makes a SEALED forward call an
external oracle later confirms — and rises MORE when the call was on a hard,
crowd-split question and when the forecaster was provably RIGHT FIRST.

    reality_score = 1000
                  + 800 * difficulty_weighted_calibration   (0..1)
                  +  12 * first_to_be_right                  (capped at 120)

A forecaster with zero resolved forward calls is UNSCORED (provisional) and sits at
the 1000 baseline — we never invent a score for a track record that does not exist
yet. Same honesty invariant the calibration layer enforces.

Uncopyable for the same reason the Trust Graph is: a pure function of
sealed-before-outcome calls a latecomer cannot backfill. The number only goes up by
living through time on the record.
"""
from __future__ import annotations

from collections import defaultdict

from .ledger import Kind, Ledger
from .trust import trust_graph

BASE = 1000
SKILL_SPAN = 800          # difficulty-weighted calibration 0..1  ->  +0..800
FIRST_BONUS = 12          # points per first-to-be-right credit
FIRST_CAP = 120           # ceiling on the first-mover bonus

# how a forecaster is labelled on the Human-vs-AI board
_AI_PREFIXES = ("claude", "gpt", "gemini", "llama", "mistral", "grok",
                "deepseek", "qwen", "o1", "o3", "bedrock")
_ENSEMBLE = {"nexus-consensus", "nexus-house", "nexus-local-ensemble"}


def kind_of(author: str) -> str:
    a = (author or "").lower()
    if a in _ENSEMBLE:
        return "ensemble"
    if any(a.startswith(p) for p in _AI_PREFIXES):
        return "ai"
    return "human"


def _score(effective_trust: float, first_right: int) -> int:
    skill = SKILL_SPAN * max(0.0, min(1.0, float(effective_trust)))
    first = min(FIRST_CAP, FIRST_BONUS * int(first_right))
    return int(round(BASE + skill + first))


def reality_score(ledger: Ledger) -> dict:
    """Project the resolved forward record onto one number per forecaster and rank.
    Forecasters with only PENDING forward calls appear as provisional rows (so the
    arena board is populated before reality has resolved anything)."""
    tg = trust_graph(ledger)
    board = []
    seen = set()
    for a in tg["authors"]:
        scored = a["resolved"] > 0
        seen.add(a["author"])
        board.append({
            "forecaster": a["author"],
            "kind": kind_of(a["author"]),
            "reality_score": _score(a["effective_trust"], a["first_right"]) if scored else BASE,
            "scored": scored,
            "resolved": a["resolved"],
            "pending": a["pending"],
            "accuracy": a["accuracy"],
            "brier": a["brier"],
            "first_right": a["first_right"],
            "effective_trust": a["effective_trust"],
            "domains": a["domains"],
            "status": "ranked" if scored else "provisional · no resolved calls yet",
        })

    # forecasters who have ONLY sealed-and-pending forward calls (no resolved row
    # yet) never reach the trust graph — but the arena should still show them sealed
    # in and waiting on reality. Add them as provisional rows.
    pending_only: dict[str, int] = defaultdict(int)
    for e in ledger.pending():
        p = e.prediction
        if p.get("kind") == Kind.FORWARD.value:
            au = p.get("author", "anon")
            if au not in seen:
                pending_only[au] += 1
    for au, cnt in pending_only.items():
        board.append({
            "forecaster": au, "kind": kind_of(au), "reality_score": BASE, "scored": False,
            "resolved": 0, "pending": cnt, "accuracy": None, "brier": None,
            "first_right": 0, "effective_trust": 0.0, "domains": {},
            "status": "provisional · sealed and awaiting reality",
        })

    # ranked first (by score, then first-mover); provisional forecasters last
    board.sort(key=lambda x: (x["scored"], x["reality_score"], x["first_right"]), reverse=True)
    for i, row in enumerate(board):
        row["rank"] = i + 1 if row["scored"] else None
    return {
        "leaderboard": board,
        "scored_on": tg["scored_on"],
        "baseline": BASE,
        "formula": "1000 + 800·difficulty-weighted-calibration + 12·first-to-be-right (cap 120)",
        "note": ("One number. Rises only on sealed forward calls an external oracle later "
                 "confirms; harder questions and earlier-correct seals count more. "
                 "Unscored until a real track record exists."),
    }
