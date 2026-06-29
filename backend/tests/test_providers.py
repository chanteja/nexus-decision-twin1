# backend/tests/test_providers.py
"""Model-agnostic reasoning providers: selection, OpenAI-compatible path, validation."""
import json

from forward_ledger import providers
from forward_ledger.ensemble import decide_local


def test_local_default_is_deterministic(monkeypatch):
    monkeypatch.delenv("NEXUS_REASONING_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.delenv("BEDROCK_MODELS", raising=False)
    v = providers.reason("Should we expand to Brazil?", branches=7)
    assert v.weights == decide_local("Should we expand to Brazil?", branches=7).weights


def test_provider_selection(monkeypatch):
    monkeypatch.setenv("NEXUS_REASONING_PROVIDER", "local")
    assert [p.name for p in providers.get_providers()] == ["local"]
    monkeypatch.setenv("NEXUS_REASONING_PROVIDER", "openai")
    assert [p.name for p in providers.get_providers()] == ["openai", "local"]
    monkeypatch.setenv("NEXUS_REASONING_PROVIDER", "auto")
    assert providers.get_providers()[-1].name == "local"  # always a final fallback


class _Resp:
    def __init__(self, payload): self._p = payload
    def json(self): return self._p


def test_openai_compatible_provider_parses_and_validates(monkeypatch):
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.example.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-x")
    content = json.dumps({"branches": ["a", "b"], "weights": [0.7, 0.3],
                          "survivor": 0, "why": "w", "watch": "t"})
    import httpx
    monkeypatch.setattr(httpx, "post",
                        lambda *a, **k: _Resp({"choices": [{"message": {"content": content}}]}))
    v = providers.OpenAICompatibleProvider().reason("decide", branches=2)
    assert v is not None and v.model.startswith("openai-compatible:")
    assert abs(sum(v.weights) - 1.0) < 1e-6 and v.survivor == 0


def test_openai_provider_rejects_fabricated_weights(monkeypatch):
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.example.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-x")
    bad = json.dumps({"branches": ["a", "b"], "weights": [9.9, -2.0], "survivor": 0})
    import httpx
    monkeypatch.setattr(httpx, "post",
                        lambda *a, **k: _Resp({"choices": [{"message": {"content": bad}}]}))
    assert providers.OpenAICompatibleProvider().reason("decide", branches=2) is None
