# backend/tests/test_security.py
"""Auth, input validation, CORS posture, and per-tenant isolation at the API edge."""
import os
import time

import pytest

os.environ.setdefault("NEXUS_DEMO", "1")

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import auth, config  # noqa: E402
from api.app import app  # noqa: E402

client = TestClient(app)


# ── input validation ────────────────────────────────────────────────────────
def test_rejects_unbounded_branches():
    r = client.post("/v1/decide", json={"decision": "x", "branches": 100000})
    assert r.status_code == 422


def test_rejects_empty_decision():
    assert client.post("/v1/decide", json={"decision": ""}).status_code == 422


def test_rejects_overlong_text():
    assert client.post("/v1/decide", json={"decision": "z" * 5000}).status_code == 422


def test_rejects_bad_tenant_id():
    r = client.post("/v1/decide", json={"decision": "x", "tenant": "../etc/passwd"})
    assert r.status_code == 422


# ── auth (dependency-level, env-driven) ──────────────────────────────────────
def test_auth_noop_in_demo():
    config.get_settings.cache_clear()
    p = auth.require_auth(None, authorization=None, x_api_key=None)
    assert p.key_id == "anonymous" and p.authenticated is False


def test_auth_enforced_when_keys_set(monkeypatch):
    monkeypatch.setenv("NEXUS_API_KEYS", "topsecret-key")
    config.get_settings.cache_clear()
    try:
        with pytest.raises(HTTPException) as ei:
            auth.require_auth(None, authorization=None, x_api_key=None)
        assert ei.value.status_code == 401
        assert auth.require_auth(None, authorization="Bearer topsecret-key", x_api_key=None).authenticated
        assert auth.require_auth(None, authorization=None, x_api_key="topsecret-key").authenticated
        with pytest.raises(HTTPException):
            auth.require_auth(None, authorization="Bearer wrong", x_api_key=None)
    finally:
        config.get_settings.cache_clear()


def test_production_fails_closed_without_keys(monkeypatch):
    monkeypatch.setenv("NEXUS_ENV", "production")
    monkeypatch.delenv("NEXUS_API_KEYS", raising=False)
    config.get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            config.get_settings().validate_boot()
    finally:
        config.get_settings.cache_clear()


# ── CORS posture ─────────────────────────────────────────────────────────────
def test_cors_default_is_not_wildcard():
    config.get_settings.cache_clear()
    assert "*" not in config.get_settings().cors_origins


# ── tenant isolation at the API edge ─────────────────────────────────────────
def test_tenant_writes_are_isolated():
    ref = f"seed:iso_{int(time.time()*1000)}"
    r = client.post("/v1/decide", json={
        "decision": "isolated tenant decision", "tenant": "tenant_alpha",
        "resolves_at": time.time() + 9999, "oracle_ref": ref, "author": "u"})
    assert r.status_code == 200 and r.json()["ledger"]["sealed"] is True
    sealed_id = r.json()["ledger"]["entry"]
    # the default-tenant public ledger must not contain another tenant's decision
    default_ids = {e["id"] for e in client.get("/v1/ledger?limit=500").json()["entries"]}
    assert sealed_id not in default_ids


def test_authenticated_tenant_is_bound_to_key():
    """Zero Trust: the acting tenant comes from the key, not the request body."""
    import pytest as _pytest
    from fastapi import HTTPException

    from api.auth import Principal, effective_tenant
    bound = Principal(key_id="k_x", tenant="acme", authenticated=True)
    assert effective_tenant(bound, None) == "acme"
    assert effective_tenant(bound, "acme") == "acme"
    with _pytest.raises(HTTPException) as ei:
        effective_tenant(bound, "globex")
    assert ei.value.status_code == 403
    anon = Principal(key_id="anonymous", tenant="demo_corp", authenticated=False)
    assert effective_tenant(anon, "whatever") == "whatever"


def test_reads_are_tenant_scoped():
    """A read resolves the caller's tenant ledger, never the global default."""
    from api.app import get_ledger, tenant_ledger
    from api.auth import Principal
    p = Principal(key_id="k_y", tenant="tenant_read_x", authenticated=True)
    assert tenant_ledger(p) is get_ledger("tenant_read_x")


def test_request_tenant_defaults_to_none_not_a_fixed_tenant():
    """Regression: a fixed tenant default collided with the key's bound tenant and 403'd
    the authenticated happy path. Unset tenant must mean 'use my identity's tenant'."""
    from api.app import CommitIn, DecideIn
    assert DecideIn(decision="x").tenant is None
    assert CommitIn(decision="x", weights=[0.6, 0.4], survivor=0, confidence=0.6,
                    resolves_at=1.0, oracle_ref="seed:x").tenant is None


def test_qr_target_rejects_untrusted_base():
    from api.app import _qr_target
    allowed = ["https://app.nexus.example"]
    # an allow-listed origin is embedded; an attacker origin is dropped to relative
    assert _qr_target("e1", "https://app.nexus.example", allowed) == \
        "https://app.nexus.example/verify.html?id=e1&api=https://app.nexus.example"
    assert _qr_target("e1", "https://evil.example", allowed) == "/verify.html?id=e1"
    assert _qr_target("e1", "", allowed) == "/verify.html?id=e1"


def test_demo_routes_hidden_in_production(monkeypatch):
    import api.app as A

    class _Stub:
        is_production = True
        auth_required = False
        default_tenant = "demo_corp"
        cors_origins = ["http://localhost:8000"]

    monkeypatch.setattr(A, "settings", _Stub())
    assert client.post("/v1/demo/resolve_live").status_code == 404
    assert client.post("/v1/demo/arena").status_code == 404


def test_idempotency_key_prevents_double_seal():
    import time as _t
    key = f"idem-{_t.time()}"
    body = {"decision": "hire 10 engineers", "resolves_at": _t.time() + 9999,
            "oracle_ref": f"seed:idem{_t.time()}", "author": "u"}
    r1 = client.post("/v1/decide", json=body, headers={"Idempotency-Key": key}).json()
    r2 = client.post("/v1/decide", json=body, headers={"Idempotency-Key": key}).json()
    assert r1["ledger"]["sealed"] is True
    assert r2.get("idempotent_replay") is True
    assert r1["ledger"]["entry"] == r2["ledger"]["entry"]   # same seal, not a new one


def test_commit_idempotency_returns_same_entry():
    import time as _t
    key = f"idem-c-{_t.time()}"
    body = {"decision": "ship v2", "weights": [0.6, 0.4], "survivor": 0, "confidence": 0.6,
            "resolves_at": _t.time() + 9999, "oracle_ref": f"seed:c{_t.time()}"}
    a = client.post("/v1/commit", json=body, headers={"Idempotency-Key": key}).json()
    b = client.post("/v1/commit", json=body, headers={"Idempotency-Key": key}).json()
    assert a["entry"] == b["entry"] and b.get("idempotent_replay") is True
