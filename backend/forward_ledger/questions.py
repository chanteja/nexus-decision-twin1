# backend/forward_ledger/questions.py
"""
Canonical question identity — the accretion point of the network effect.

v11 keyed markets by `oracle_ref or decision[string]` and trust by raw strings, so
two phrasings of the same real question split the consensus and a domain typo split
the standing. Network effects require a STABLE entity that forecasts accrete onto.

`canonical_id` derives a deterministic id for the question a prediction is about:
  * if an oracle_ref is present, that IS the question's external identity — every
    forecast pointing at the same settleable market is the same question, regardless
    of wording;
  * otherwise we fold the decision text to a normalized form (lowercased, stripped
    of punctuation and filler) and hash it, so near-identical phrasings collapse.

This is intentionally simple and deterministic — no model call, no network. The
goal is that the SAME real-world question always produces the SAME id, so its
sealed forecasts pool into one consensus node that sharpens as good forecasters join.
"""
from __future__ import annotations

import hashlib
import re

_FILLER = {
    "the", "a", "an", "to", "of", "for", "in", "on", "by", "will", "is", "are",
    "be", "do", "does", "should", "we", "our", "this", "that", "with", "at", "as",
}
_PUNCT = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Fold a decision string to a stable comparison key."""
    t = _PUNCT.sub(" ", (text or "").lower())
    toks = [w for w in _WS.sub(" ", t).strip().split(" ") if w and w not in _FILLER]
    return " ".join(toks)


def is_bound(oracle_ref: str) -> bool:
    """A question is BOUND when it points at a settleable external identity (a real
    market/series an oracle can resolve). Unbound free-text questions are provisional:
    they can be reasoned about, but they never enter markets, trust, or consensus,
    because nothing external can ever grade them. This is what keeps the network
    effect and the settlement honest — you accrete standing only on real questions."""
    return bool((oracle_ref or "").strip())


def canonical_id(decision: str, oracle_ref: str = "") -> str:
    """Stable id for the question a prediction addresses.

    An oracle_ref is an external identity (a real settleable market), so it wins:
    every forecast on the same market is the same question -> `q:<hash>`. Without one
    the question is PROVISIONAL: we still fold the text so phrasings collapse, but the
    `q:prov:` prefix marks it as unsettleable, and markets/trust/consensus skip it.
    """
    ref = (oracle_ref or "").strip()
    if ref:
        return "q:" + hashlib.sha256(("ref:" + ref).encode("utf-8")).hexdigest()[:16]
    return "q:prov:" + hashlib.sha256(("txt:" + normalize(decision)).encode("utf-8")).hexdigest()[:16]
