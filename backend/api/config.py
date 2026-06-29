# backend/api/config.py
"""Centralised, validated runtime configuration.

Secure-by-default posture: in ``production`` the API refuses to run a write surface
without configured API keys (fail closed). In ``demo``/local it stays open so the
offline demo and tests need zero setup. Everything is environment-driven; nothing
security-relevant is hard-coded.
"""
from __future__ import annotations

import os
from functools import lru_cache


def _csv(name: str) -> list[str]:
    return [x.strip() for x in os.environ.get(name, "").split(",") if x.strip()]


def _load_secret_key_spec() -> list[str]:
    """Load the API-key spec from AWS Secrets Manager when NEXUS_API_KEYS_SECRET is set.
    Best-effort and lazy: returns [] off-AWS so local/demo needs no setup. Each entry is
    ``tenant:key`` (preferred) or a bare ``key`` (mapped to the default tenant)."""
    arn = os.environ.get("NEXUS_API_KEYS_SECRET")
    if not arn:
        return []
    try:
        import json

        import boto3
        raw = boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"]
        try:
            data = json.loads(raw)
            raw = data.get("keys", "") if isinstance(data, dict) else str(data)
        except Exception:  # noqa: S110  # best-effort: secret may be a bare CSV string
            pass
        return [x.strip() for x in raw.split(",") if x.strip()]
    except Exception:
        return []


class Settings:
    def __init__(self) -> None:
        self.env: str = os.environ.get("NEXUS_ENV", "demo").lower()
        self.demo: bool = os.environ.get("NEXUS_DEMO", "1") == "1"
        self.default_tenant: str = os.environ.get("NEXUS_TENANT", "demo_corp")
        # auth — keys come from env (local) or AWS Secrets Manager (production).
        # Each entry is ``tenant:key`` (binds the key to a tenant — Zero Trust) or a
        # bare ``key`` (mapped to the default tenant). key_tenants maps key -> tenant.
        self.key_tenants: dict[str, str] = self._parse_key_spec(
            _csv("NEXUS_API_KEYS") + _load_secret_key_spec())
        self.api_keys: set[str] = set(self.key_tenants)
        # CORS: explicit allowlist; "*" only if the operator opts in explicitly.
        origins = _csv("NEXUS_CORS_ORIGINS")
        if not origins:
            origins = ["http://localhost:8000", "http://127.0.0.1:8000"]
        self.cors_origins: list[str] = origins
        # input bounds
        self.max_text: int = int(os.environ.get("NEXUS_MAX_TEXT", "2000"))
        self.max_branches: int = int(os.environ.get("NEXUS_MAX_BRANCHES", "12"))
        self.max_assumptions: int = int(os.environ.get("NEXUS_MAX_ASSUMPTIONS", "20"))

    def _parse_key_spec(self, entries: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for e in entries:
            if ":" in e:
                tenant, key = e.split(":", 1)
                tenant, key = tenant.strip(), key.strip()
            else:
                tenant, key = self.default_tenant, e.strip()
            if key:
                out[key] = tenant or self.default_tenant
        return out

    def tenant_for_key(self, key: str) -> str | None:
        return self.key_tenants.get(key)

    @property
    def is_production(self) -> bool:
        return self.env in ("production", "prod")

    @property
    def auth_required(self) -> bool:
        # writes are protected whenever keys exist, and always in production.
        return bool(self.api_keys) or self.is_production

    def validate_boot(self) -> None:
        if self.is_production and not self.api_keys:
            raise RuntimeError(
                "NEXUS_ENV=production but NEXUS_API_KEYS is empty — refusing to expose "
                "an unauthenticated write surface (fail closed).")
        if self.is_production and "*" in self.cors_origins:
            raise RuntimeError("NEXUS_ENV=production with wildcard CORS — refusing (set NEXUS_CORS_ORIGINS).")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
