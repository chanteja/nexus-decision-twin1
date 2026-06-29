# backend/tests/test_twin.py
"""The Decision Twin façade: five pillars, complexity hidden, /v1 intact."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NEXUS_DEMO", "1")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import PILLARS, app  # noqa: E402

client = TestClient(app)

FIVE = ["Decision Twin", "Decision Graph", "Future Explorer",
        "Reality Verification", "Decision Timeline"]


def test_exactly_five_pillars():
    assert list(PILLARS.keys()) == FIVE


def test_status_surfaces_pillars():
    r = client.get("/v1/status").json()
    assert list(r["pillars"].keys()) == FIVE


def test_twin_root():
    r = client.get("/twin").json()
    assert r["name"] == "Decision Twin"
    assert r["pillars"] == FIVE
    assert "confidence" in r and "components" in r["confidence"]


def test_decision_confidence_has_four_components():
    c = client.get("/twin").json()["confidence"]["components"]
    assert set(c) == {"forecast_accuracy", "historical_calibration",
                      "evidence_quality", "assumption_stability"}


def test_graph_pillar():
    r = client.get("/twin/graph").json()
    assert "nodes" in r and "edges" in r and "influencers" in r


def test_futures_pillar():
    r = client.get("/twin/futures", params={"decision": "Should we expand into Europe?"}).json()
    assert r["recommended_future"] is not None
    assert len(r["futures"]) >= 2


def test_verification_pillar():
    r = client.get("/twin/verification").json()
    assert r["flow"][0] == "evidence"
    assert "verify_on_phone" in r["proof"]


def test_timeline_pillar():
    r = client.get("/twin/timeline").json()
    assert set(["past", "present", "future"]).issubset(r)


def test_v1_contract_unbroken():
    # the landing/demo speak /v1/* — these must still answer.
    for path in ["/v1/status", "/v1/graph", "/v1/calibration", "/v1/leaderboard",
                 "/v1/ledger", "/v1/trust", "/v1/markets"]:
        assert client.get(path).status_code == 200, path


def test_no_engine_words_leak_in_product_surface():
    # the product responses must not expose implementation vocabulary.
    banned = ["graphrag", "brier", "isotonic", "merkle chain", "ensemble engine"]
    for path in ["/twin", "/twin/verification", "/twin/timeline"]:
        body = client.get(path).text.lower()
        for w in banned:
            assert w not in body, f"{w!r} leaked in {path}"
