import os
import time

os.environ["NEXUS_DEMO"] = "1"
os.environ["NEXUS_DEMO_HORIZON"] = "0.5"
os.environ["NEXUS_LEDGER_PATH"] = "/tmp/nexus_test_ledger.jsonl"
if os.path.exists("/tmp/nexus_test_ledger.jsonl"):
    os.remove("/tmp/nexus_test_ledger.jsonl")

from fastapi.testclient import TestClient

from api.app import app

c = TestClient(app)


def test_status_real():
    j = c.get("/v1/status").json()
    assert j["chain_valid"] is True and j["source"] == "live" and len(j["merkle_root"]) == 64


def test_decide_seals_when_resolvable():
    j = c.post("/v1/decide", json={"decision": "hire 10 engineers",
               "resolves_at": time.time() + 9999, "oracle_ref": "seed:t", "author": "u"}).json()
    assert len(j["weights"]) == 7 and "ledger" in j and j["ledger"]["sealed"] is True
    v = c.get(f"/v1/verify/{j['ledger']['entry']}").json()
    assert v["intact"] is True and v["sealed_before_outcome"] is True


def test_prove_closes_the_loop():
    time.sleep(0.6)
    j = c.post("/v1/prove").json()
    assert len(j["settled"]) >= 1
    assert j["calibration"]["forward"]["n"] >= 1


def test_calibration_separates_forward_and_backtest():
    j = c.get("/v1/calibration").json()
    assert j["backtest"]["n"] >= 10
    assert "context only" in j["backtest"]["note"]


def test_ledger_carries_merkle_root():
    j = c.get("/v1/ledger").json()
    assert len(j["digest"]["merkle_root"]) == 64 and j["digest"]["chain_valid"] is True


def test_graph_endpoint_is_typed():
    j = c.get("/v1/graph").json()
    assert "node_types" in j and "Question" in j["node_types"]
    assert "counts" in j and j["counts"]["Question"] >= 1
    assert any(e["type"] == "FORECASTS" for e in j["edges"])


def test_counterfactuals_form_after_prove():
    # by now backtest + demo-forward entries have resolved, so the corpus exists
    j = c.get("/v1/counterfactuals").json()
    assert j["total_branches"] >= 1
    assert "domain_regret" in j


def test_anchor_endpoint_publishes_root():
    j = c.post("/v1/anchor").json()
    assert j["anchored"]["merkle_root"] == c.get("/v1/status").json()["merkle_root"]
    assert len(j["history"]) >= 1


def test_calibration_exposes_learning_state():
    j = c.get("/v1/calibration").json()
    assert "learning" in j
    assert "fitted_reliability" in j["learning"]
    assert j["learning"]["needed_for_recalibration"] >= 1


def test_markets_keyed_by_canonical_question():
    j = c.get("/v1/markets").json()
    assert "canonical-question" in j["weighting"]
    for m in j["markets"]:
        assert m["question_id"].startswith("q:")
