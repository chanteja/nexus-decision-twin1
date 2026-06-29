from forward_ledger import (
    AnchorLog,
    Kind,
    Ledger,
    MemoryStore,
    Prediction,
    anchor,
    apply_learning,
    build_graph,
    canonical_id,
    counterfactuals,
    decide,
    movers,
    normalize,
    question_consensus,
    reliability_map,
)
from forward_ledger.recalibrate import MIN_N
from forward_ledger.recalibrate import apply as rmap_apply


def fwd(d, p, author="a", dom="g", survivor=0, ref=None):
    return Prediction(decision=d, branches=["s", "x"], weights=[p, round(1 - p, 4)],
                      survivor=survivor, confidence=p, why="w", watch="t",
                      author=author, domain=dom, kind=Kind.FORWARD,
                      oracle_ref=ref if ref is not None else ("seed:" + d))


# ── canonical questions ────────────────────────────────────────────────────
def test_canonical_question_folds_phrasing():
    a = canonical_id("Will AWS ship a forecasting primitive?", "")
    b = canonical_id("will aws ship a forecasting primitive", "")
    assert a == b                       # punctuation/case/filler folded
    assert normalize("The will of A to B") == "b"  # filler stripped


def test_canonical_question_oracle_ref_is_identity():
    a = canonical_id("phrasing one", "polymarket:x:yes")
    b = canonical_id("totally different words", "polymarket:x:yes")
    assert a == b                       # same market == same question


# ── L1 recalibration ───────────────────────────────────────────────────────
def test_reliability_map_identity_below_min_n():
    L = Ledger(MemoryStore())
    e = L.append(fwd("a", 0.8), created_at=1.0)
    L.resolve(e.id, True, "r", at=2.0)
    assert reliability_map(L) == [None] * 10     # not enough evidence yet


def test_reliability_map_bends_with_evidence():
    L = Ledger(MemoryStore())
    # 40 forecasts all sealed at p=0.85 but only ~half actually survive →
    # the 0.8 band should map DOWN toward reality (~0.5), the flywheel working.
    for i in range(MIN_N + 10):
        e = L.append(fwd(f"q{i}", 0.85), created_at=1.0)
        L.resolve(e.id, i % 2 == 0, "r", at=2.0)
    rmap = reliability_map(L)
    assert any(v is not None for v in rmap)
    assert rmap[8] is not None and rmap[8] < 0.85    # overconfidence corrected down


def test_recalibrate_is_monotone():
    L = Ledger(MemoryStore())
    for i in range(MIN_N + 4):
        e = L.append(fwd(f"q{i}", 0.6), created_at=1.0)
        L.resolve(e.id, i % 3 != 0, "r", at=2.0)
    rmap = reliability_map(L)
    vals = [rmap_apply(p / 10 + 0.05, rmap) for p in range(10)]
    assert vals == sorted(vals)          # isotonic: never decreasing


# ── L2 counterfactual corpus ───────────────────────────────────────────────
def test_counterfactuals_emitted_on_resolution():
    L = Ledger(MemoryStore())
    p = Prediction(decision="launch", branches=["bold", "safe", "wait"],
                   weights=[0.5, 0.3, 0.2], survivor=0, confidence=0.5, why="w",
                   watch="t", domain="product", kind=Kind.FORWARD, oracle_ref="seed:l")
    e = L.append(p, created_at=1.0)
    assert L.counterfactual_rows() == []          # nothing until it resolves
    L.resolve(e.id, False, "r", at=2.0)           # taken path FAILED
    rows = L.counterfactual_rows()
    assert len(rows) == 3                          # one row per branch
    taken = [r for r in rows if r["was_taken"]][0]
    assert taken["branch"] == "bold" and taken["taken_survived"] is False
    # untaken branches carry regret == their sealed prob when the taken path failed
    safe = [r for r in rows if r["branch"] == "safe"][0]
    assert safe["regret"] == 0.3


def test_counterfactual_regret_zero_when_taken_survives():
    L = Ledger(MemoryStore())
    p = Prediction(decision="d", branches=["a", "b"], weights=[0.7, 0.3], survivor=0,
                   confidence=0.7, why="w", watch="t", kind=Kind.FORWARD, oracle_ref="seed:d")
    e = L.append(p, created_at=1.0)
    L.resolve(e.id, True, "r", at=2.0)             # taken path WON
    rows = L.counterfactual_rows()
    assert all(r["regret"] == 0.0 for r in rows)   # no regret when you were right


def test_counterfactuals_aggregate_by_domain():
    L = Ledger(MemoryStore())
    for i in range(3):
        p = Prediction(decision=f"d{i}", branches=["a", "b"], weights=[0.6, 0.4],
                       survivor=0, confidence=0.6, why="w", watch="t", domain="m&a",
                       kind=Kind.FORWARD, oracle_ref=f"seed:{i}")
        e = L.append(p, created_at=1.0)
        L.resolve(e.id, False, "r", at=2.0)
    cf = counterfactuals(L, domain="m&a", min_regret=0.0)
    assert cf["scored_untaken"] == 3
    assert cf["domain_regret"][0]["domain"] == "m&a"
    assert cf["domain_regret"][0]["mean_regret"] == 0.4


# ── verify() invariant still holds after counterfactual emission ────────────
def test_resolution_with_cf_keeps_chain_valid():
    L = Ledger(MemoryStore())
    e = L.append(fwd("one", 0.7), created_at=1.0)
    h = e.hash
    L.resolve(e.id, True, "ref", at=2.0)
    assert L.verify() is True and L.by_id(e.id).hash == h


# ── reality graph ───────────────────────────────────────────────────────────
def test_graph_is_typed_not_a_line():
    L = Ledger(MemoryStore())
    e1 = L.append(fwd("q one", 0.8, author="alice", ref="polymarket:m1:yes"), created_at=1.0)
    L.append(fwd("q one rephrased", 0.6, author="bob", ref="polymarket:m1:yes"), created_at=1.0)
    L.resolve(e1.id, True, "r", at=2.0)
    g = build_graph(L)
    types = {n["type"] for n in g["nodes"]}
    assert {"Question", "Prediction", "Author", "Outcome"} <= types
    # both predictions accrete onto ONE canonical question node
    assert g["counts"]["Question"] == 1
    edge_types = {e["type"] for e in g["edges"]}
    assert "FORECASTS" in edge_types and "ON" in edge_types and "SETTLED_BY" in edge_types


def test_movers_ranks_by_resolved_trust():
    L = Ledger(MemoryStore())
    for i in range(3):
        e = L.append(fwd(f"g{i}", 0.85, author="sharp"), created_at=1.0)
        L.resolve(e.id, True, "r", at=2.0)
    m = movers(L)
    assert m["reality_movers"] and m["reality_movers"][0]["author"] == "sharp"


# ── L3 network-blended reasoning ────────────────────────────────────────────
def test_question_consensus_none_when_alone():
    L = Ledger(MemoryStore())
    c, ev = question_consensus(L, canonical_id("solo question", ""))
    assert c is None and ev == 0.0


def test_apply_learning_keeps_calls_independent():
    # v13: apply_learning must NOT herd the sealed call toward consensus. Peers exist
    # and agree, but the verdict's relative ranking is left to the reasoner — only L1
    # recalibration may touch magnitudes (a no-op here, since nothing has resolved).
    L = Ledger(MemoryStore())
    for i in range(4):
        L.append(fwd(f"phrasing {i}", 0.9, author=f"peer{i}", ref="polymarket:shared:yes"),
                 created_at=1.0)
    v = decide("a fresh take on the shared question")
    before = list(v.weights)
    v2 = apply_learning(v, L, "a fresh take on the shared question", "polymarket:shared:yes")
    assert "network-blended" not in v2.model       # the crowd no longer moves the seal
    assert v2.weights == before                    # untouched: nothing resolved → L1 identity


# ── anchor ──────────────────────────────────────────────────────────────────
def test_anchor_records_history(tmp_path):
    L = Ledger(MemoryStore())
    L.append(fwd("one", 0.6), created_at=1.0)
    log = AnchorLog(str(tmp_path / "a.jsonl"))
    out = anchor(L, log)
    assert out["anchored"]["merkle_root"] == L.merkle_root()
    assert len(out["history"]) == 1
    anchor(L, log)
    assert len(log.history()) == 2            # append-only anchor record
