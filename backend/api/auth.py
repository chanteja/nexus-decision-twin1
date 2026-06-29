# backend/api/auth.py
"""API-key authentication, tenant binding, and the security audit log.

Each API key is bound to exactly one tenant (Zero Trust: the tenant a request acts on
is derived from the *authenticated identity*, never from client-supplied input). Keys
are compared in constant time; the principal id recorded in logs is a non-reversible
hash of the key, never the key itself. When auth is disabled (demo/local) the principal
is anonymous and scoped to the default tenant.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, status

from .config import get_settings

audit = logging.getLogger("nexus.audit")


@dataclass(frozen=True)
class Principal:
    key_id: str          # non-secret identifier (hash prefix) safe to log
    tenant: str          # the tenant this identity may act on
    authenticated: bool


def key_id(key: str) -> str:
    """A stable, non-reversible id for a key — safe to put in logs/audit."""
    return "k_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def log_audit(action: str, principal: Principal, request: Request | None = None,
              result: str = "ok", **fields) -> None:
    """Emit one structured audit event for a security-relevant action."""
    audit.info("audit", extra={
        "action": action, "result": result,
        "principal": principal.key_id, "tenant": principal.tenant,
        "authenticated": principal.authenticated,
        "request_id": getattr(getattr(request, "state", None), "request_id", None),
        "path": str(request.url.path) if request else None,
        **fields,
    })


def _match(presented: str, keys: set[str]) -> str | None:
    for k in keys:
        if hmac.compare_digest(presented, k):
            return k
    return None


def require_auth(request: Request = None,  # noqa: RUF013 (FastAPI injects; tests pass None)
                 authorization: str | None = Header(default=None),
                 x_api_key: str | None = Header(default=None)) -> Principal:
    """FastAPI dependency. Returns an authenticated, tenant-bound Principal, or 401.
    No-op (anonymous, default tenant) when auth is disabled (demo/local)."""
    settings = get_settings()
    if not settings.auth_required:
        return Principal(key_id="anonymous", tenant=settings.default_tenant, authenticated=False)
    presented = x_api_key
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()
    matched = _match(presented, settings.api_keys) if presented else None
    if not matched:
        audit.warning("audit", extra={
            "action": "auth", "result": "denied",
            "request_id": getattr(getattr(request, "state", None), "request_id", None),
            "path": str(request.url.path) if request else None,
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(key_id=key_id(matched),
                     tenant=settings.tenant_for_key(matched) or settings.default_tenant,
                     authenticated=True)


def effective_tenant(principal: Principal, requested: str | None) -> str:
    """The tenant a request may act on. For an authenticated principal it is ALWAYS the
    principal's bound tenant; a mismatching client-supplied tenant is forbidden (403).
    When auth is disabled (local/demo) the client may choose a tenant for testing."""
    if not principal.authenticated:
        return requested or principal.tenant
    if requested and requested != principal.tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="tenant does not match the authenticated identity")
    return principal.tenant
