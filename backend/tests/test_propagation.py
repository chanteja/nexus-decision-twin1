# backend/tests/test_propagation.py
"""The living Decision Graph: a falsified assumption re-scores connected decisions."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("NEXUS_DEMO", "1")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402

client = TestClient(app)


def test_scenario_exposes_the_trigger():
    s = client.get("/twin/graph/scenario").json()
    assert "Brazil" in s["trigger_assumption"]
    assert s["failed_decision"]
    assert len(s["control_decisions"]) >= 1


def test_propagation_finds_the_failure_and_at_risk():
    r = client.get("/twin/graph/propagate").json()
    assert r["summary"]["already_failed"] >= 1
    assert r["summary"]["now_at_risk"] >= 1
    # the one that already failed is the Brazil launch
    assert any("Brazil" in f["decision"] for f in r["failed"])


def test_propagation_drops_confidence_on_connected_decisions():
    r = client.get("/twin/graph/propagate").json()
    for row in r["at_risk"]:
        assert row["confidence_after"] < row["confidence_before"]
        assert row["impact_score"] > 0


def test_controls_are_unaffected():
    r = client.get("/twin/graph/propagate").json()
    touched = {x["decision"] for x in r["failed"] + r["at_risk"]}
    # decisions that do not lean on Brazil demand must not be re-scored
    assert any("EU data platform" in d["decision"] for d in r["unaffected_decisions"])
    assert not any("EU data platform" in d for d in touched)


def test_recommendations_are_ranked_by_impact():
    recs = client.get("/twin/graph/propagate").json()["recommended_changes"]
    impacts = [r["impact_score"] for r in recs]
    assert impacts == sorted(impacts, reverse=True)
    assert all(r["action"] for r in recs)


def test_learning_is_visible():
    learning = client.get("/twin/graph/propagate").json()["learning"]
    assert learning["falsification_rate_after"] >= (learning["falsification_rate_before"] or 0)
    assert learning["decisions_rescored"] >= 1


def test_timeline_answers_what_changed_today():
    t = client.get("/twin/timeline").json()
    assert t["question"] == "What's changed today?"
    assert "headline" in t["changes_today"]


def test_recommendations_carry_executive_fields():
    """The review's 'hidden winner': every recommendation must read like an
    executive decision card — action, reason, dollar impact, why-now, evidence,
    and the alternative to take instead."""
    rec = client.get("/twin/graph/propagate").json()["recommended_changes"][0]
    for key in ("recommended_action", "reason", "why_now", "evidence", "alternative",
                "confidence", "financial_impact"):
        assert rec[key], f"missing executive field: {key}"
    assert isinstance(rec["evidence"], list) and rec["evidence"]
    assert rec["confidence"]["after"] < rec["confidence"]["before"]


def test_financial_impact_is_defensible_not_invented():
    """Dollar figures must follow the declared model (capital × Δconfidence) and be
    flagged as estimates, never precise fabrications."""
    r = client.get("/twin/graph/propagate").json()
    fi = r["recommended_changes"][0]["financial_impact"]
    assert fi["estimate"] is True and fi["model"]
    cap, dmag = fi["capital_at_risk_usd"], abs(r["recommended_changes"][0]["confidence"]["delta"])
    assert abs(fi["risk_repriced_usd"] - round(cap * dmag)) <= 1
    # the portfolio headline equals the sum of the per-decision figures
    total = sum(x["financial_impact"]["risk_repriced_usd"] for x in r["recommended_changes"])
    assert r["summary"]["capital_repriced_usd"] == total
