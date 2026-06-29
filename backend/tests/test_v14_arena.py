"""v14 — the Reality Arena: one legible Reality Score, an aged Human-vs-AI cohort
that resolves live, and the honesty guarantees that keep the demo cohort separated
from the genuine forward record."""
import time

from forward_ledger import (
    FORECASTERS,
    Kind,
    Ledger,
    MemoryStore,
    arena_answers,
    arena_oracle,
    calibration,
    has_arena,
    kind_of,
    reality_score,
    resolve_due,
    resolve_live,
    seed_arena,
)


# ── the Reality Score is honest about an empty record ───────────────────────
def test_reality_score_empty_is_provisional():
    rs = reality_score(Ledger(MemoryStore()))
    assert rs["leaderboard"] == []
    assert rs["baseline"] == 1000


def test_kind_classification():
    assert kind_of("claude") == "ai"
    assert kind_of("gpt") == "ai"
    assert kind_of("gemini") == "ai"
    assert kind_of("human-expert") == "human"
    assert kind_of("student-team") == "human"
    assert kind_of("nexus-consensus") == "ensemble"


# ── the arena seeds, is idempotent, and stays pending until reality arrives ──
def test_seed_arena_idempotent_and_pending():
    L = Ledger(MemoryStore())
    n1 = seed_arena(L)
    assert n1 == 10 * len(FORECASTERS)          # 10 questions × 5 forecasters
    assert has_arena(L)
    n2 = seed_arena(L)                          # idempotent
    assert n2 == 0
    # every arena seal predates its (future or past) resolution; chain is valid
    assert L.verify() is True
    rs = reality_score(L)
    # before resolution: everyone provisional, scored == False, baseline score
    assert all(row["scored"] is False for row in rs["leaderboard"])
    assert {row["forecaster"] for row in rs["leaderboard"]} == set(FORECASTERS)


# ── resolving the arena makes the board come alive and rank by calibration ──
def test_arena_resolves_and_ranks():
    L = Ledger(MemoryStore())
    seed_arena(L)
    orc = arena_oracle()                        # holds the arena answer key
    now = time.time()
    settled = resolve_due(L, orc, now=now)      # the 8 already-due questions
    settled += resolve_live(L, orc, now=now)    # release the 2 held live questions
    assert len(settled) == 10 * len(FORECASTERS)
    rs = reality_score(L)
    ranked = [r for r in rs["leaderboard"] if r["scored"]]
    assert len(ranked) == len(FORECASTERS)
    # board is sorted by reality_score desc
    scores = [r["reality_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)
    # the calibrated forecasters (human-expert, claude) out-rank the coin-flip crowd
    by = {r["forecaster"]: r["reality_score"] for r in ranked}
    assert by["human-expert"] > by["student-team"]
    assert by["claude"] > by["student-team"]
    # scored forecasters sit above the 1000 baseline once they have a track record
    assert by["human-expert"] > 1000
    # first-to-be-right is credited to someone
    assert any(r["first_right"] > 0 for r in ranked)


def test_arena_answers_cover_every_question():
    L = Ledger(MemoryStore())
    seed_arena(L)
    ans = arena_answers()
    refs = {e.prediction["oracle_ref"] for e in L.all()}
    assert refs.issubset(set(ans.keys()))       # the oracle can settle every arena ref


# ── the genuine forward headline stays honest about the demo cohort ─────────
def test_calibration_headline_flags_demo_cohort():
    L = Ledger(MemoryStore())
    seed_arena(L)
    orc = arena_oracle(); now = time.time()
    resolve_due(L, orc, now=now); resolve_live(L, orc, now=now)
    c = calibration(L)
    # even though resolved forward n is now >= 30, the headline must remain illustrative
    assert "illustrative" in c["headline"]
    assert c["cohorts"]["demo_forward_resolved"] == 10 * len(FORECASTERS)
    assert c["cohorts"]["real_forward_resolved"] == 0


# ── the verifiable ordering property holds for every aged seal ──────────────
def test_aged_seals_precede_resolution():
    L = Ledger(MemoryStore())
    seed_arena(L)
    now = time.time()
    orc = arena_oracle()
    resolve_due(L, orc, now=now); resolve_live(L, orc, now=now)
    for e in L.resolved(Kind.FORWARD):
        assert e.created_at < e.resolved_at      # sealed strictly before the outcome
    assert L.verify() is True
