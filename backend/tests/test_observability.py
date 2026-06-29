# backend/tests/test_observability.py
"""Health/version probes, request-id correlation, and structured-log formatting."""
import json
import logging
import os

os.environ.setdefault("NEXUS_DEMO", "1")

from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402
from api.logging_config import JsonFormatter  # noqa: E402

client = TestClient(app)


def test_healthz_reports_chain_integrity():
    j = client.get("/healthz").json()
    assert j["status"] == "ok" and j["chain_valid"] is True and j["version"] == "19.0"


def test_version_endpoint():
    j = client.get("/version").json()
    assert j["version"] == "19.0" and "env" in j


def test_request_id_header_present_and_echoed():
    r = client.get("/version")
    assert r.headers.get("X-Request-ID")
    rid = "test-correlation-id-123"
    r2 = client.get("/version", headers={"X-Request-ID": rid})
    assert r2.headers["X-Request-ID"] == rid


def test_json_formatter_emits_structured_fields():
    rec = logging.LogRecord("nexus", logging.INFO, __file__, 1, "request", (), None)
    rec.request_id = "abc"
    rec.status = 200
    out = json.loads(JsonFormatter().format(rec))
    assert out["msg"] == "request" and out["request_id"] == "abc" and out["status"] == 200
    assert out["level"] == "INFO"
