# backend/tests/test_pipeline.py
"""P6/P7: the end-to-end decision pipeline and the recommendation engine's six explanations."""
import os

os.environ.setdefault("NEXUS_DEMO", "1")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402
from forward_ledger import (  # noqa: E402
    Kind,
    Ledger,
    MemoryStore,
    Prediction,
    recommend,
    run_pipeline,
)

client = TestClient(app)


def _seal(L, d, asm, gid):
    L.append(Prediction(decision=d, branches=["a", "b"], weights=[0.6, 0.4], survivor=0,
                        confidence=0.6, why="w", watch="t", kind=Kind.FORWARD,
                        oracle_ref="seed:" + d, assumptions=asm, graph_id=gid))


def test_pipeline_runs_all_eight_stages_and_reuses_graph():
    L = Ledger(MemoryStore())
    _seal(L, "Launch Brazil GTM", ["demand grows >18%", "FX stays stable"], "g:latam")
    out = run_pipeline(L, "Open Mexico next", assumptions=["demand grows >18%"])
    assert out["pipeline"][0] == "intent" and out["pipeline"][-1] == "learning"
    # reused the related graph rather than forking a new one
    assert out["decision_memory"]["reused_existing_graph"] is True
    assert out["decision_memory"]["graph_id"] == "g:latam"
    assert "expected_survival" in out["future_explorer"]
    assert out["reality_verification"]["status"].startswith("not sealed")


def test_recommendation_explains_all_six_dimensions():
    L = Ledger(MemoryStore())
    out = run_pipeline(L, "Acquire a competitor", assumptions=["synergies materialise"])
    rec = out["recommendation"]
    for key in ("why", "evidence", "business_impact", "confidence", "alternatives",
                "recommended_action"):
        assert rec[key], f"recommendation missing {key}"
    assert isinstance(rec["evidence"], list) and rec["evidence"]
    assert isinstance(rec["alternatives"], list) and rec["alternatives"]


def test_recommendation_stance_tracks_survival():
    low = recommend("x", {"expected_survival": 0.1, "distribution": {"p10_worst": 0.05},
                          "drivers": [], "stdev": 0.1}, ["a"])
    high = recommend("x", {"expected_survival": 0.85, "distribution": {"p10_worst": 0.7},
                           "drivers": [], "stdev": 0.05}, ["a"])
    assert low["stance"] == "hold" and high["stance"] == "proceed"


def test_pipeline_endpoint_live():
    j = client.get("/twin/pipeline", params={
        "decision": "Should we enter Southeast Asia?",
        "assumptions": "regulatory approval lands, local partner delivers"}).json()
    assert len(j["pipeline"]) == 8
    assert j["recommendation"]["recommended_action"]
    assert j["knowledge_extraction"]["source"] == "provided"
