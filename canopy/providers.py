"""Provider abstraction for canopy fill.

A `Provider` knows how to send a system+user prompt to an LLM and get
the response text back. Two concrete providers ship in v0.3.0:

  - `AnthropicProvider` — Anthropic Messages API
    (used by Anthropic, MiniMax, GLM via anthropic-compat proxies, etc.)
  - `OpenAIProvider` — OpenAI Chat Completions API
    (used by OpenAI, Mistral, Groq, Together, Ollama, LM Studio, vLLM,
     OpenRouter, LiteLLM proxy, etc.)

Future adapters (Gemini, Cohere, etc.) can subclass `Provider` and ship
as a separate file. Users who need a vendor we don't support can write
their own adapter in 30 lines by implementing `complete()`.

The legacy `canopy.llm.call_minimax` function is preserved as a thin
wrapper around `AnthropicProvider` for back-compat with v0.1.0 callers.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """Raised when an LLM call fails (HTTP error, network error, parse error)."""


@runtime_checkable
class Provider(Protocol):
    """Anything that can take a system+user prompt and return text."""

    def complete(self, system: str, user: str) -> str: ...


def _bearer(auth_value: str) -> str:
    """Build an Authorization header value with the word Bearer + space + key."""
    return "Bearer " + auth_value


# ─── Anthropic Messages API ────────────────────────────────────────────


class AnthropicProvider:
    """Calls the Anthropic Messages API (`POST /v1/messages`).

    Works for Anthropic, MiniMax (which speaks Anthropic-format at
    /anthropic/v1/messages), GLM's anthropic-compat endpoint, etc.
    """

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout: int = 60) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": user}],
        }
        if system:
            body["system"] = system
        req = urllib.request.Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ProviderError(f"Anthropic HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise ProviderError(f"Anthropic call failed: {e}") from e
        return _extract_anthropic_text(payload)


def _extract_anthropic_text(payload: dict[str, Any]) -> str:
    """Concatenate text blocks from an Anthropic Messages response."""
    return "".join(
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    )


# ─── OpenAI Chat Completions API ───────────────────────────────────────


class OpenAIProvider:
    """Calls the OpenAI Chat Completions API (`POST /v1/chat/completions`).

    Works for OpenAI, Mistral, Groq, Together, Ollama (with --api openai
    or its built-in /v1 endpoint), LM Studio, vLLM, OpenRouter, LiteLLM
    proxy, and any other OpenAI-compatible server.
    """

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout: int = 60) -> None:
        self.api_key = api_key
        self.base_url = self._normalize_base_url(base_url)
        self.model = model
        self.timeout = timeout

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        """Strip a trailing /v1 so callers can pass either form."""
        u = base_url.rstrip("/")
        if u.endswith("/v1"):
            u = u[:-3]
        return u

    def complete(self, system: str, user: str) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        body = {"model": self.model, "messages": messages}
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "authorization": _bearer(self.api_key),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ProviderError(f"OpenAI HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise ProviderError(f"OpenAI call failed: {e}") from e
        return _extract_openai_text(payload)


def _extract_openai_text(payload: dict[str, Any]) -> str:
    """Extract the assistant message text from an OpenAI Chat Completions response."""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content") or ""


# ─── factory helpers ───────────────────────────────────────────────────


def anthropic_provider_for(*, api_key: str, base_url: str, model: str) -> AnthropicProvider:
    """Build an Anthropic-format provider. The default for MiniMax."""
    return AnthropicProvider(api_key=api_key, base_url=base_url, model=model)


def openai_provider_for(*, api_key: str, base_url: str, model: str) -> OpenAIProvider:
    """Build an OpenAI-compat provider. Default for OpenAI / Ollama / etc."""
    return OpenAIProvider(api_key=api_key, base_url=base_url, model=model)