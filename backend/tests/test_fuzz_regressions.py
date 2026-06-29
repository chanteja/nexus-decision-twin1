# backend/tests/test_fuzz_regressions.py
"""Regressions for crashes found by monkey/fuzz testing — all must be 4xx, never 5xx."""
import os
import random

os.environ.setdefault("NEXUS_DEMO", "1")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)
INF, NAN = float("inf"), float("nan")


def test_value_endpoint_survives_nonfinite_and_huge_floats():
    for params in ({"hours_per_review": "nan"}, {"analyst_hourly_usd": "inf"},
                   {"analyst_hourly_usd": "1e308"}, {"hours_per_review": "1e308"},
                   {"reviews_per_year": "100000000000"}, {"automation_fraction": "inf"}):
        assert client.get("/twin/value", params=params).status_code == 200


def test_futures_branches_bounds_never_crash():
    for b in (0, -1, 1, 99999, 2):
        assert client.get("/twin/futures",
                          params={"decision": "x", "branches": b}).status_code == 200


def test_nonfinite_floats_are_rejected_422_not_500():
    assert client.post("/v1/decide",
                       json={"decision": "x", "resolves_at": NAN, "oracle_ref": "seed:t"}).status_code == 422
    assert client.post("/v1/decide",
                       json={"decision": "x", "resolves_at": INF, "oracle_ref": "seed:t"}).status_code == 422
    for w in ([INF, 0.4], [NAN, 0.4]):
        assert client.post("/v1/commit", json={
            "decision": "x", "weights": w, "survivor": 0, "confidence": 0.6,
            "resolves_at": 1.0, "oracle_ref": "seed:t"}).status_code == 422
    assert client.post("/v1/commit", json={
        "decision": "x", "weights": [0.6, 0.4], "survivor": 0, "confidence": NAN,
        "resolves_at": 1.0, "oracle_ref": "seed:t"}).status_code == 422


def test_bounded_monkey_no_server_errors():
    """A URL-safe fuzz pass: random JSON bodies + bounded query params must never 5xx."""
    R = random.Random(99)
    garbage = [None, True, 0, -1, 1e308, "", "x" * 5000, "🙈" * 50, "../../x",
               "'; DROP TABLE--", [], {}, [1, 2], 3.14, "-5", "1e9", INF, NAN]
    gets = ["/v1/status", "/v1/ledger", "/twin", "/twin/value", "/twin/timeline",
            "/twin/graph/propagate", "/twin/futures", "/v1/calibration", "/v1/trust"]
    for _ in range(600):
        roll = R.random()
        if roll < 0.4:
            ep = R.choice(gets)
            qs = {R.choice(["limit", "top", "branches", "samples", "decision", "assumptions",
                            "analyst_hourly_usd", "reviews_per_year", "min_regret"]):
                  str(R.choice(garbage))[:80] for _ in range(R.randint(0, 3))}
            r = client.get(ep, params=qs)
        elif roll < 0.7:
            body = {k: R.choice(garbage) for k in
                    ["decision", "branches", "resolves_at", "oracle_ref", "tenant",
                     "author", "assumptions", "seed"] if R.random() < 0.8}
            r = client.post("/v1/decide", json=body)
        else:
            body = {k: R.choice(garbage) for k in
                    ["decision", "weights", "survivor", "confidence", "resolves_at",
                     "oracle_ref", "branches"] if R.random() < 0.8}
            r = client.post("/v1/commit", json=body)
        assert r.status_code < 500, f"5xx on {r.request.method} {r.request.url}: {r.status_code}"
