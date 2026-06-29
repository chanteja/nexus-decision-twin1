"""v13 — verifiable-foresight changes: assumption ledger (causal corpus), bound vs
provisional questions, consensus published as its own forecaster (not herded into the
seal), evidence hashing, difficulty-weighted reputation + first-to-be-right, and the
recalibration confidence band."""
from forward_ledger import (
    CONSENSUS_AUTHOR,
    Kind,
    Ledger,
    MemoryStore,
    Prediction,
    assumptions_corpus,
    canonical_id,
    consensus_forecast,
    first_to_call,
    is_bound,
    question_consensus,
    question_difficulty,
    reliability_band,
    trust_graph,
)
from forward_ledger.recalibrate import MIN_N


def fwd(d, p, author="a", dom="g", survivor=0, ref=None, assumptions=None):
    return Prediction(decision=d, branches=["s", "x"], weights=[p, round(1 - p, 4)],
                      survivor=survivor, confidence=p, why="w", watch="t",
                      author=author, domain=dom, kind=Kind.FORWARD,
                      oracle_ref=ref if ref is not None else ("seed:" + d),
                      assumptions=assumptions or [])


# ── bound vs provisional questions ──────────────────────────────────────────
def test_unbound_question_is_provisional():
    assert is_bound("polymarket:x:yes") is True
    assert is_bound("") is False
    assert canonical_id("free text", "").startswith("q:prov:")
    assert canonical_id("anything", "polymarket:x:yes").startswith("q:") and \
        "prov" not in canonical_id("anything", "polymarket:x:yes")


def test_provisional_questions_never_enter_consensus():
    L = Ledger(MemoryStore())
    for i in range(3):
        L.append(fwd(f"unbound {i}", 0.8, author=f"p{i}", ref=""), created_at=1.0)
    # unbound entries share a provisional canonical id but must not form a market peer set
    c, ev = question_consensus(L, canonical_id("unbound 0", ""))
    assert c is None and ev == 0.0


# ── evidence hash on resolution ─────────────────────────────────────────────
def test_resolution_records_evidence_hash():
    L = Ledger(MemoryStore())
    e = L.append(fwd("one", 0.7), created_at=1.0)
    assert e.resolution_evidence_hash == ""
    L.resolve(e.id, True, "polymarket:m1:yes", at=2.0)
    r = L.by_id(e.id)
    assert len(r.resolution_evidence_hash) == 64        # sha256 of the evidence ref
    assert L.verify() is True                            # core untouched


# ── assumption ledger (the causal corpus) ───────────────────────────────────
def test_assumptions_emitted_only_carry_failure_signal():
    L = Ledger(MemoryStore())
    a = ["premature scaling is fine", "the market stays hot"]
    e1 = L.append(fwd("startup A", 0.6, assumptions=a, ref="seed:A"), created_at=1.0)
    e2 = L.append(fwd("startup B", 0.6, assumptions=a, ref="seed:B"), created_at=1.0)
    L.resolve(e1.id, False, "r", at=2.0)        # bet failed → assumptions flagged
    L.resolve(e2.id, True, "r", at=2.0)         # bet won → recorded but not "failed_with"
    corpus = assumptions_corpus(L)
    assert corpus["total_rows"] == 4 and corpus["distinct"] == 2
    top = corpus["assumptions"][0]
    assert top["seen"] == 2 and top["failed_with"] == 1


def test_assumptions_empty_when_none_sealed():
    L = Ledger(MemoryStore())
    e = L.append(fwd("no assumptions", 0.7), created_at=1.0)
    L.resolve(e.id, False, "r", at=2.0)
    assert assumptions_corpus(L)["total_rows"] == 0


# ── consensus as its own forecaster (not herded) ────────────────────────────
def test_consensus_forecast_is_separate_and_self_excluding():
    L = Ledger(MemoryStore())
    for i in range(3):
        L.append(fwd(f"phr {i}", 0.9, author=f"peer{i}", ref="polymarket:shared:yes"),
                 created_at=1.0)
    cf = consensus_forecast(L, "new phrasing", "polymarket:shared:yes")
    assert cf is not None and cf["author"] == CONSENSUS_AUTHOR and cf["n_peers"] == 3
    # a consensus entry already on the book must not feed its own consensus
    L.append(Prediction(decision="phr c", branches=["a", "b"], weights=[cf["survival"], 1 - cf["survival"]],
                        survivor=0, confidence=cf["survival"], why="w", watch="t",
                        author=CONSENSUS_AUTHOR, kind=Kind.FORWARD, oracle_ref="polymarket:shared:yes"),
             created_at=1.0)
    c2, _ = question_consensus(L, canonical_id("x", "polymarket:shared:yes"))
    # still computed only over the 3 real peers, consensus author excluded
    assert abs(c2 - cf["survival"]) < 1e-6


def test_consensus_none_for_unbound():
    L = Ledger(MemoryStore())
    assert consensus_forecast(L, "free text", "") is None


# ── difficulty-weighted reputation + first-to-be-right ──────────────────────
def test_difficulty_high_when_crowd_split():
    L = Ledger(MemoryStore())
    # two forecasters split 0.9 / 0.1 on one market → crowd mean 0.5 → hard (~1.0)
    L.append(fwd("split q", 0.9, author="a", ref="polymarket:split:yes"), created_at=1.0)
    L.append(fwd("split q", 0.1, author="b", ref="polymarket:split:yes"), created_at=1.0)
    diff = question_difficulty(L)
    qid = canonical_id("split q", "polymarket:split:yes")
    assert diff[qid] > 0.9


def test_first_to_call_credits_earliest_correct_seal():
    L = Ledger(MemoryStore())
    early = L.append(fwd("q", 0.8, author="early", ref="polymarket:m:yes"), created_at=1.0)
    L.append(fwd("q", 0.8, author="late", ref="polymarket:m:yes"), created_at=5.0)
    L.resolve(early.id, True, "r", at=10.0)
    fm = first_to_call(L)
    assert fm["first_movers"][0]["author"] == "early"
    assert fm["first_movers"][0]["first_right"] == 1


def test_trust_graph_exposes_effective_trust_and_first_right():
    L = Ledger(MemoryStore())
    for i in range(3):
        e = L.append(fwd(f"q{i}", 0.85, author="sharp", ref=f"polymarket:m{i}:yes"), created_at=1.0)
        L.resolve(e.id, True, "r", at=2.0)
    tg = trust_graph(L)
    assert "effective_trust" in tg["authors"][0]
    assert "first_right" in tg["authors"][0]
    assert "difficulty-weighted" in tg["weighting"]


# ── recalibration confidence band ───────────────────────────────────────────
def test_reliability_band_reports_uncertainty():
    L = Ledger(MemoryStore())
    for i in range(10):
        e = L.append(fwd(f"q{i}", 0.85, ref=f"seed:{i}"), created_at=1.0)
        L.resolve(e.id, i % 2 == 0, "r", at=2.0)
    band = reliability_band(L)
    assert band["significant"] is False           # below MIN_N → not yet earned
    b8 = [b for b in band["bands"] if b["band"] == 0.85][0]
    assert b8["n"] == 10 and b8["ci95"][0] is not None and b8["ci95"][1] > b8["ci95"][0]


def test_reliability_band_significant_above_min_n():
    L = Ledger(MemoryStore())
    for i in range(MIN_N + 5):
        e = L.append(fwd(f"q{i}", 0.85, ref=f"seed:{i}"), created_at=1.0)
        L.resolve(e.id, i % 2 == 0, "r", at=2.0)
    assert reliability_band(L)["significant"] is True
