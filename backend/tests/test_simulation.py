# backend/tests/test_simulation.py
"""The Future Explorer simulation engine: a real probabilistic model, not a stub."""
import os

os.environ.setdefault("NEXUS_DEMO", "1")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402
from forward_ledger import (  # noqa: E402
    Assumption,
    Kind,
    Ledger,
    MemoryStore,
    Prediction,
    explore_decision,
    simulate_decision,
)

client = TestClient(app)


def test_deterministic_given_seed():
    a = [Assumption("x", 0.6, 0.5), Assumption("y", 0.8, 0.4)]
    r1 = simulate_decision(0.7, a, n=2000, seed=42)
    r2 = simulate_decision(0.7, a, n=2000, seed=42)
    assert r1 == r2


def test_expected_matches_closed_form():
    # base .8, one assumption P(holds)=.5 load=.4 -> factor mean = 1-(1-.5)*.4 = .8
    r = simulate_decision(0.8, [Assumption("a", 0.5, 0.4)], n=1000, seed=1)
    assert abs(r["expected_survival"] - 0.8 * 0.8) < 1e-6


def test_percentiles_are_ordered():
    r = simulate_decision(0.7, [Assumption("a", 0.6, 0.7), Assumption("b", 0.5, 0.5)],
                          n=5000, seed=3)
    d = r["distribution"]
    assert d["p10_worst"] <= d["p50_expected"] <= d["p90_best"]


def test_more_load_bearing_or_less_likely_lowers_survival():
    base = 0.8
    mild = simulate_decision(base, [Assumption("a", 0.9, 0.2)], n=1, seed=0)["expected_survival"]
    heavy = simulate_decision(base, [Assumption("a", 0.5, 0.9)], n=1, seed=0)["expected_survival"]
    assert heavy < mild < base


def test_sensitivity_ranks_the_pivotal_assumption_first():
    # 'pivotal' is both uncertain (P=.5) and very load-bearing (load=.9); 'minor' is
    # near-certain and barely load-bearing -> pivotal must dominate variance_share.
    r = simulate_decision(0.9, [Assumption("minor", 0.95, 0.1),
                                Assumption("pivotal", 0.5, 0.9)], n=1, seed=0)
    assert r["drivers"][0]["assumption"] == "pivotal"
    assert r["drivers"][0]["variance_share"] > r["drivers"][1]["variance_share"]


def test_probabilities_are_learned_from_the_record():
    # a belief that the record keeps falsifying should get a LOWER P(holds) than an
    # unseen belief -> lower simulated survival. This is the flywheel.
    L = Ledger(MemoryStore())
    for i in range(6):
        e = L.append(Prediction(decision=f"d{i}", branches=["s", "x"], weights=[0.6, 0.4],
                                 survivor=0, confidence=0.6, why="w", watch="t",
                                 kind=Kind.FORWARD, oracle_ref=f"seed:{i}",
                                 assumptions=["fragile belief"]), created_at=1.0)
        L.resolve(e.id, survived=False, ref="o", at=2.0)   # the belief underwrote failures
    learned = explore_decision(L, "new bet", ["fragile belief"], base_survival=0.8, n=1)
    unseen = explore_decision(L, "new bet", ["never-tested belief"], base_survival=0.8, n=1)
    assert learned["drivers"][0]["prob_holds"] < unseen["drivers"][0]["prob_holds"]
    assert learned["expected_survival"] < unseen["expected_survival"]


def test_futures_endpoint_returns_a_real_simulation():
    r = client.get("/twin/futures", params={
        "decision": "Should we expand into Brazil?",
        "assumptions": "demand grows, FX stays stable, we can hire fast"}).json()
    sim = r["simulation"]
    assert set(sim["distribution"]) == {"p10_worst", "p50_expected", "p90_best"}
    assert len(sim["drivers"]) == 3
    assert sim["samples"] >= 200
