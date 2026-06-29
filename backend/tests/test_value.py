# backend/tests/test_value.py
"""Business-impact model: measured facts vs declared-input estimates."""
import os

os.environ.setdefault("NEXUS_DEMO", "1")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402
from forward_ledger import Kind, Ledger, MemoryStore, Prediction, value_summary  # noqa: E402

client = TestClient(app)


def _seal(L, d, asm=None):
    return L.append(Prediction(decision=d, branches=["s", "x"], weights=[0.6, 0.4],
                    survivor=0, confidence=0.6, why="w", watch="t", kind=Kind.FORWARD,
                    oracle_ref="seed:" + d, assumptions=asm or []), created_at=1.0)


def test_measured_metrics_are_facts():
    L = Ledger(MemoryStore())
    _seal(L, "a", asm=["x"])               # sealed, has assumption, pending
    e = _seal(L, "b", asm=["y"])           # sealed, has assumption
    L.resolve(e.id, survived=True, ref="oracle:real", at=2.0)   # resolved w/ evidence
    m = value_summary(L)["measured"]
    assert m["decisions_on_record"] == 2
    assert m["assumption_coverage"] == 1.0          # both carry assumptions
    assert m["forecast_verification_rate"] == 0.5   # 1 of 2 resolved
    assert m["audit_readiness"] == 1.0              # the resolved one has evidence


def test_estimate_follows_declared_model():
    L = Ledger(MemoryStore())
    v = value_summary(L, analyst_hourly_usd=200, hours_per_review=50,
                      reviews_per_year=10, automation_fraction=0.5)["estimated_value"]
    assert v["estimate"] is True
    assert v["review_prep_hours_saved_per_year"] == 50 * 10 * 0.5      # 250
    assert v["labour_value_usd_per_year"] == round(250 * 200)          # 50000


def test_value_endpoint_live():
    j = client.get("/twin/value").json()
    assert "measured" in j and "estimated_value" in j and j["estimated_value"]["estimate"]
