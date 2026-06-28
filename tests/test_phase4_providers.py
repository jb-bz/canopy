"""Phase 4 acceptance tests: more providers + Bedrock SigV4 signing.

Adds:
- GeminiProvider (Google's Generative Language API)
- BedrockProvider (AWS SigV4-signed requests via stdlib)
- CohereProvider (Cohere v2 chat API)
- OpenRouterProvider (OpenAI-compatible, free-form model)
- BYOProvider (subclass hook so users can wire any HTTP API)

Tests use mocked urlopen so we never hit a real API.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import urllib.error
from unittest.mock import MagicMock

import pytest

from canopy.providers import (
    AnthropicProvider,
    BedrockProvider,
    BYOProvider,
    CohereProvider,
    GeminiProvider,
    OpenAIProvider,
    OpenRouterProvider,
    Provider,
    ProviderError,
    bedrock_sigv4_sign,
)


# ─── Protocol conformance ─────────────────────────────────────────────


def test_all_six_providers_implement_protocol() -> None:
    providers = [
        AnthropicProvider(api_key="k", base_url="https://x", model="m"),
        OpenAIProvider(api_key="k", base_url="https://x", model="m"),
        GeminiProvider(api_key="k", model="m"),
        BedrockProvider(
            api_key="AKIA...",  # access key
            secret_key="secret",
            region="us-east-1",
            model="anthropic.claude-3-sonnet",
        ),
        CohereProvider(api_key="k", model="c"),
        OpenRouterProvider(api_key="k", model="openai/gpt-4o-mini"),
        BYOProvider(complete_fn=lambda system, user: "ok"),
    ]
    for p in providers:
        assert isinstance(p, Provider)


# ─── Gemini ─────────────────────────────────────────────────────────────


def test_gemini_posts_to_generate_content(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in dict(req.headers).items()}
        captured["body"] = json.loads(req.data.decode())
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "candidates": [
                {"content": {"parts": [{"text": "hello from gemini"}]}}
            ]
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    p = GeminiProvider(api_key="k", model="gemini-2.0-flash")
    out = p.complete("system prompt", "user prompt")

    assert out == "hello from gemini"
    assert "generativelanguage.googleapis.com" in captured["url"]
    assert "/v1beta/models/gemini-2.0-flash:generateContent" in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "k"
    # Gemini uses contents[].parts[] with role=user, and systemInstruction for system.
    assert "contents" in captured["body"]
    assert "systemInstruction" in captured["body"]
    assert captured["body"]["systemInstruction"]["parts"][0]["text"] == "system prompt"


def test_gemini_no_system_prompt_omits_system_instruction(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode())
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "candidates": [{"content": {"parts": [{"text": "x"}]}}]
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    GeminiProvider(api_key="k", model="m").complete("", "u")
    assert "systemInstruction" not in captured["body"]


# ─── Bedrock SigV4 signing ─────────────────────────────────────────────


def test_bedrock_sigv4_sign_produces_aws_signature() -> None:
    """SigV4 should produce a deterministic Authorization header for fixed inputs."""
    headers = bedrock_sigv4_sign(
        method="POST",
        host="bedrock-runtime.us-east-1.amazonaws.com",
        path="/model/anthropic.claude-3-sonnet/invoke",
        body=b'{"messages":[]}',
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        service="bedrock",
    )
    assert "Authorization" in headers
    # AWS4-HMAC-SHA256 is the canonical algorithm name.
    assert headers["Authorization"].startswith("AWS4-HMAC-SHA256 ")
    assert "Credential=AKIAIOSFODNN7EXAMPLE/" in headers["Authorization"]
    assert "SignedHeaders=" in headers["Authorization"]
    assert "Signature=" in headers["Authorization"]
    assert headers["X-Amz-Content-Sha256"] == hashlib.sha256(b'{"messages":[]}').hexdigest()


def test_bedrock_provider_posts_invoke_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.method
        captured["headers"] = {k.lower(): v for k, v in dict(req.headers).items()}
        captured["body"] = json.loads(req.data.decode())
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "content": [{"type": "text", "text": "bedrock says hi"}]
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    p = BedrockProvider(
        api_key="AKIA123",
        secret_key="secret",
        region="us-east-1",
        model="anthropic.claude-3-sonnet",
    )
    out = p.complete("system", "user")
    assert out == "bedrock says hi"
    assert "bedrock-runtime.us-east-1.amazonaws.com" in captured["url"]
    assert "/model/anthropic.claude-3-sonnet/invoke" in captured["url"]
    assert captured["headers"]["authorization"].startswith("AWS4-HMAC-SHA256 ")
    # Bedrock uses Anthropic's Messages body shape.
    assert "anthropic_version" in captured["body"]
    assert captured["body"]["system"] == "system"


def test_bedrock_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 403, "forbidden", {}, None)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    p = BedrockProvider(api_key="k", secret_key="s", region="us-east-1", model="m")
    with pytest.raises(ProviderError):
        p.complete("s", "u")


# ─── Cohere ────────────────────────────────────────────────────────────


def test_cohere_posts_to_v2_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in dict(req.headers).items()}
        captured["body"] = json.loads(req.data.decode())
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "message": {"role": "assistant", "content": [{"type": "text", "text": "cohere says hi"}]}
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    p = CohereProvider(api_key="k", model="command-r-plus")
    out = p.complete("system", "user")
    assert out == "cohere says hi"
    assert captured["url"] == "https://api.cohere.com/v2/chat"
    assert captured["headers"]["authorization"] == "Bearer k"
    assert captured["body"]["model"] == "command-r-plus"
    # Cohere v2 uses a list of content blocks for the user message.
    assert captured["body"]["messages"][-1]["content"] == [{"type": "text", "text": "user"}]


# ─── OpenRouter ────────────────────────────────────────────────────────


def test_openrouter_posts_with_freeform_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenRouter accepts free-form model names like 'openai/gpt-4o-mini'."""
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in dict(req.headers).items()}
        captured["body"] = json.loads(req.data.decode())
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": "or says hi"}}]
        }).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    p = OpenRouterProvider(
        api_key="sk-or-...",
        model="anthropic/claude-3.5-sonnet",
    )
    out = p.complete("system", "user")
    assert out == "or says hi"
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["body"]["model"] == "anthropic/claude-3.5-sonnet"
    # OpenRouter sends extra headers for app attribution.
    # urllib normalizes header case; check case-insensitively.
    headers_lc = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_lc["http-referer"] == "https://github.com/jb-bz/canopy"
    assert headers_lc["x-title"] == "canopy"


# ─── BYO ────────────────────────────────────────────────────────────────


def test_byo_delegates_to_user_function() -> None:
    """BYO provider just calls whatever function the user gave us."""
    called_with: list[tuple[str, str]] = []

    def my_complete(system: str, user: str) -> str:
        called_with.append((system, user))
        return "custom"

    p = BYOProvider(complete_fn=my_complete)
    assert p.complete("s", "u") == "custom"
    assert called_with == [("s", "u")]


def test_byo_propagates_exceptions() -> None:
    """If the user's function raises, BYO should let it through unchanged."""
    class MyError(RuntimeError):
        pass

    def boom(system: str, user: str) -> str:
        raise MyError("user's fault")

    p = BYOProvider(complete_fn=boom)
    with pytest.raises(MyError):
        p.complete("s", "u")


def test_byo_requires_complete_fn() -> None:
    with pytest.raises(TypeError):
        BYOProvider()  # type: ignore[call-arg]