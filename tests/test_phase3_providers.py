"""Phase 3 acceptance tests: provider abstraction.

Two providers ship in v0.3.0:
- AnthropicProvider — Anthropic Messages API (existing code, refactored)
- OpenAIProvider — OpenAI Chat Completions API (new)

Both implement the Provider protocol:
    complete(system: str, user: str) -> str

Both are unit-tested with mocked urlopen. Backwards compat: canopy.llm.call_minimax
still works (delegates to AnthropicProvider).
"""
from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock

import pytest

from canopy.providers import (
    AnthropicProvider,
    OpenAIProvider,
    Provider,
    ProviderError,
    anthropic_provider_for,
    openai_provider_for,
)


# ─── protocol surface ──────────────────────────────────────────────────


def test_both_providers_implement_protocol() -> None:
    """Both concrete providers satisfy the Provider protocol structurally."""
    p1 = AnthropicProvider(api_key="k", base_url="https://x", model="m")
    p2 = OpenAIProvider(api_key="k", base_url="https://x", model="m")
    for p in (p1, p2):
        assert isinstance(p, Provider)


# ─── Anthropic provider ────────────────────────────────────────────────


def test_anthropic_posts_to_v1_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.method
        captured["headers"] = {k.lower(): v for k, v in dict(req.headers).items()}
        captured["body"] = json.loads(req.data.decode())
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "content": [{"type": "text", "text": "hello"}]
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    p = AnthropicProvider(api_key="k", base_url="https://x.test", model="claude-x")
    out = p.complete("system prompt", "user prompt")

    assert out == "hello"
    assert captured["url"] == "https://x.test/v1/messages"
    assert captured["headers"]["x-api-key"] == "k"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["body"]["model"] == "claude-x"
    assert captured["body"]["system"] == "system prompt"
    assert captured["body"]["messages"] == [{"role": "user", "content": "user prompt"}]


def test_anthropic_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    p = AnthropicProvider(api_key="k", base_url="https://x", model="m")
    with pytest.raises(ProviderError):
        p.complete("s", "u")


# ─── OpenAI provider ───────────────────────────────────────────────────


def test_openai_posts_to_v1_chat_completions(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.method
        captured["headers"] = {k.lower(): v for k, v in dict(req.headers).items()}
        captured["body"] = json.loads(req.data.decode())
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": "hi from openai"}}]
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    p = OpenAIProvider(api_key="k", base_url="https://api.openai.com", model="gpt-4o")
    out = p.complete("system prompt", "user prompt")

    assert out == "hi from openai"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer k"
    assert captured["body"]["model"] == "gpt-4o"
    # OpenAI takes system as a message with role=system, not a top-level field.
    assert captured["body"]["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]


def test_openai_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "unauthorized", {}, None)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    p = OpenAIProvider(api_key="k", base_url="https://x", model="m")
    with pytest.raises(ProviderError):
        p.complete("s", "u")


# ─── factory helpers ───────────────────────────────────────────────────


def test_anthropic_provider_for_minimax_returns_anthropic() -> None:
    """MiniMax speaks the Anthropic Messages API at /anthropic/v1/messages."""
    p = anthropic_provider_for(
        api_key="k",
        base_url="https://api.minimax.io/anthropic",
        model="MiniMax-M3",
    )
    assert isinstance(p, AnthropicProvider)


def test_openai_provider_for_openai_returns_openai() -> None:
    p = openai_provider_for(
        api_key="k",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
    )
    assert isinstance(p, OpenAIProvider)


def test_openai_provider_for_ollama_returns_openai() -> None:
    """Ollama exposes an OpenAI-compatible endpoint."""
    p = openai_provider_for(
        api_key="ollama",
        base_url="http://localhost:11434/v1",
        model="llama3",
    )
    assert isinstance(p, OpenAIProvider)


# ─── back-compat: old canopy.llm.call_minimax still works ────────────


def test_legacy_call_minimax_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    """canopy.llm.call_minimax must still work for v0.2.0 callers."""
    from canopy.llm import call_minimax

    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "content": [{"type": "text", "text": "legacy"}]
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = call_minimax("u", api_key="k", base_url="https://x", model="m", system="s")
    assert out == "legacy"
    assert captured["url"] == "https://x/v1/messages"