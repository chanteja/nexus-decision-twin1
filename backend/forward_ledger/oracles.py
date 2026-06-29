# backend/forward_ledger/oracles.py
"""
Oracles settle predictions against ground truth NEXUS does not control. That
independence is what makes a resolved entry evidence rather than self-grading.

  * HttpOracle  — live deployments: Polymarket / financial / RSS endpoints settle
                  forward questions at their resolve date. (Network-gated; real.)
  * SeedOracle  — local + demo: a fixed, dated answer key the *ledger has never
                  seen at seal time*. The seal still precedes resolution, so the
                  honesty invariant (sealed-before-outcome) holds even offline.

The resolver only ever asks the oracle; it cannot author outcomes itself.
"""
from __future__ import annotations

from typing import Protocol


class Oracle(Protocol):
    name: str
    def settle(self, oracle_ref: str) -> tuple[bool, str] | None:
        """Return (survived, evidence_ref) or None if not yet settleable."""
        ...


class SeedOracle:
    """Offline answer key keyed by oracle_ref. Used for the demo and for tests.
    The outcomes are real public facts; the point of the demo is the *mechanism*
    (seal → wait → settle by a party other than the predictor), not the scale."""
    name = "seed"

    def __init__(self, answers: dict[str, tuple[bool, str]]):
        self._answers = dict(answers)

    def extend(self, answers: dict[str, tuple[bool, str]]) -> SeedOracle:
        """Merge more answers in (e.g. the arena cohort key). Returns self."""
        self._answers.update(answers)
        return self

    def settle(self, oracle_ref: str):
        return self._answers.get(oracle_ref)


class HttpOracle:
    """Live settlement. Pluggable per source. Real code; runs when deployed with
    network egress to the oracle APIs."""
    name = "http"

    def __init__(self, resolvers: dict[str, callable]):
        # map oracle_ref prefix -> fn(ref) -> Optional[(bool, evidence)]
        self._resolvers = resolvers

    def settle(self, oracle_ref: str):
        for prefix, fn in self._resolvers.items():
            if oracle_ref.startswith(prefix):
                return fn(oracle_ref)
        return None


def polymarket_resolver(ref: str):
    """ref form: 'polymarket:<condition_id>:<yes|no>'. Settles when the market
    is closed and resolved. Network-gated — returns None on any failure so the
    entry simply stays PENDING (never fabricates an outcome)."""
    import re

    import httpx
    try:
        parts = ref.split(":")
        if len(parts) != 3:
            return None
        _, cond, side = parts
        # SSRF / path-injection guard: condition ids are hex/alnum; reject anything that
        # could escape the fixed host+path (slashes, dots, encoded chars, @, etc.).
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", cond) or side.lower() not in ("yes", "no"):
            return None
        r = httpx.get(f"https://clob.polymarket.com/markets/{cond}", timeout=4.0,
                      follow_redirects=False)
        m = r.json()
        if not m.get("closed"):
            return None
        winner = (m.get("outcome") or "").lower()        # 'yes' / 'no'
        survived = (winner == side.lower())
        return survived, f"polymarket:{cond}:{winner}"
    except Exception:
        return None
