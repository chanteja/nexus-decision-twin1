# backend/forward_ledger/knowledge.py
"""Knowledge Extraction — turn a decision into the named assumptions it rests on.

When the caller supplies assumptions, those are the truth (source='provided'). Otherwise a
model provider can extract them (production); offline we fall back to a clearly-labelled
heuristic so the pipeline always runs without fabricating certainty.
"""
from __future__ import annotations


def extract_assumptions(decision: str, provided: list[str] | None = None) -> tuple[list[str], str]:
    if provided:
        return [a for a in provided if a and a.strip()], "provided"
    d = (decision or "this decision").strip().rstrip("?.")
    return ([f"demand and market conditions for “{d}” hold as planned",
             "execution stays on plan (cost, timeline, hiring)",
             "no decorrelated external shock lands in the decision window"], "heuristic")
