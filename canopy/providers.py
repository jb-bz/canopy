"""Provider abstraction for canopy fill.

A `Provider` knows how to send a system+user prompt to an LLM and get
the response text back.

Built-in providers (v0.4.0):

  AnthropicProvider      — Anthropic Messages API (Anthropic, MiniMax, GLM)
  OpenAIProvider         — OpenAI Chat Completions (OpenAI, Mistral, Groq, Together,
                           Ollama, LM Studio, vLLM, OpenRouter-compatible vendors)
  GeminiProvider         — Google Generative Language API (Gemini 1.5/2.0)
  BedrockProvider        — AWS Bedrock (Anthropic on AWS, Llama on AWS, Titan, Mistral)
  CohereProvider         — Cohere v2 chat API (Command R+)
  OpenRouterProvider     — OpenAI-compatible, accepts free-form `vendor/model` strings
  BYOProvider            — User-supplied `complete(system, user) -> str` function

Future vendors that we don't ship can use BYOProvider and a 30-line
adapter (see docs/providers/BYO.md).

The legacy `canopy.llm.call_minimax` function is preserved as a thin
wrapper around `AnthropicProvider` for back-compat with v0.1.0 callers.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import urllib.error
import urllib.request
from typing import Any, Callable, Protocol, runtime_checkable


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


# ─── Google Gemini ─────────────────────────────────────────────────────


class GeminiProvider:
    """Calls the Google Generative Language API (`POST generateContent`).

    Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
    Auth: `x-goog-api-key` header.
    Models: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp, etc.
    """

    def __init__(self, *, api_key: str, model: str, timeout: int = 60,
                 base_url: str = "https://generativelanguage.googleapis.com") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": 2048},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ProviderError(f"Gemini HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise ProviderError(f"Gemini call failed: {e}") from e
        return _extract_gemini_text(payload)


def _extract_gemini_text(payload: dict[str, Any]) -> str:
    """Concatenate text parts from a Gemini generateContent response."""
    parts: list[str] = []
    for candidate in payload.get("candidates", []) or []:
        content = candidate.get("content") or {}
        for part in content.get("parts", []) or []:
            text = part.get("text") if isinstance(part, dict) else None
            if text:
                parts.append(text)
    return "".join(parts)


# ─── AWS Bedrock (Anthropic Messages shape + SigV4 auth) ──────────────


class BedrockProvider:
    """Calls AWS Bedrock InvokeModel for any model whose request shape is Anthropic Messages.

    Endpoint: `POST https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke`
    Auth: AWS SigV4 (signed with access_key + secret_key, region, service='bedrock').
    Models: anthropic.claude-3-sonnet, anthropic.claude-3-haiku,
            meta.llama3-70b-instruct, amazon.titan-text-premier, mistral.mistral-7b-instruct, ...

    No boto3 dependency — SigV4 is implemented inline using stdlib hmac/hashlib.
    See `bedrock_sigv4_sign()` for the signing algorithm.
    """

    def __init__(self, *, api_key: str, secret_key: str, region: str, model: str,
                 timeout: int = 60) -> None:
        # api_key is the AWS access key ID; secret_key is the secret access key.
        self.api_key = api_key
        self.secret_key = secret_key
        self.region = region
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        # Bedrock's Anthropic models use Anthropic Messages body shape.
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": user}],
        }
        if system:
            body["system"] = system
        body_bytes = json.dumps(body).encode()

        host = f"bedrock-runtime.{self.region}.amazonaws.com"
        path = f"/model/{self.model}/invoke"
        url = f"https://{host}{path}"

        signed_headers = bedrock_sigv4_sign(
            method="POST",
            host=host,
            path=path,
            body=body_bytes,
            access_key=self.api_key,
            secret_key=self.secret_key,
            region=self.region,
            service="bedrock",
        )

        req = urllib.request.Request(url, data=body_bytes, headers=signed_headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ProviderError(f"Bedrock HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise ProviderError(f"Bedrock call failed: {e}") from e
        return _extract_anthropic_text(payload)


def bedrock_sigv4_sign(
    *,
    method: str,
    host: str,
    path: str,
    body: bytes,
    access_key: str,
    secret_key: str,
    region: str,
    service: str,
) -> dict[str, str]:
    """Build the AWS SigV4 Authorization header + required headers.

    Implements AWS Signature Version 4 for service-to-service auth without
    pulling in boto3. Reference: https://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")  # YYYYMMDD

    payload_hash = hashlib.sha256(body).hexdigest()

    canonical_headers = (
        f"content-type:application/json\n"
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"

    canonical_request = (
        f"{method}\n"
        f"{path}\n"
        "\n"  # query string (empty)
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    )

    def _sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    k_date = _sign(f"AWS4{secret_key}".encode(), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"{algorithm} "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    return {
        "Authorization": authorization,
        "Content-Type": "application/json",
        "Host": host,
        "X-Amz-Content-Sha256": payload_hash,
        "X-Amz-Date": amz_date,
    }


# ─── Cohere v2 Chat API ────────────────────────────────────────────────


class CohereProvider:
    """Calls the Cohere v2 chat API (`POST https://api.cohere.com/v2/chat`).

    Auth: `Authorization: Bearer <api_key>`.
    Models: command-r-plus, command-r, command-light, etc.
    """

    def __init__(self, *, api_key: str, model: str, timeout: int = 60,
                 base_url: str = "https://api.cohere.com") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": [{"type": "text", "text": user}]})

        body = {"model": self.model, "messages": messages}
        req = urllib.request.Request(
            f"{self.base_url}/v2/chat",
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
            raise ProviderError(f"Cohere HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise ProviderError(f"Cohere call failed: {e}") from e
        return _extract_cohere_text(payload)


def _extract_cohere_text(payload: dict[str, Any]) -> str:
    """Extract text from a Cohere v2 chat response (message.content[])."""
    content = (payload.get("message") or {}).get("content") or []
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if text:
                parts.append(text)
    return "".join(parts)


# ─── OpenRouter ────────────────────────────────────────────────────────


class OpenRouterProvider:
    """Calls OpenRouter (`POST https://openrouter.ai/api/v1/chat/completions`).

    OpenAI-compatible API. Accepts free-form model names like
    `anthropic/claude-3.5-sonnet`, `openai/gpt-4o-mini`, `meta-llama/llama-3-70b`, etc.

    Sends extra attribution headers (`HTTP-Referer`, `X-Title`) per
    OpenRouter's app-attribution requirement.
    """

    OPENROUTER_BASE_URL = "https://openrouter.ai/api"

    def __init__(self, *, api_key: str, model: str, timeout: int = 60,
                 app_referer: str = "https://github.com/jb-bz/canopy",
                 app_title: str = "canopy") -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.app_referer = app_referer
        self.app_title = app_title

    def complete(self, system: str, user: str) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        body = {"model": self.model, "messages": messages}
        req = urllib.request.Request(
            f"{self.OPENROUTER_BASE_URL}/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "content-type": "application/json",
                "authorization": _bearer(self.api_key),
                "HTTP-Referer": self.app_referer,
                "X-Title": self.app_title,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ProviderError(f"OpenRouter HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise ProviderError(f"OpenRouter call failed: {e}") from e
        return _extract_openai_text(payload)


# ─── BYO (Bring Your Own) ──────────────────────────────────────────────


class BYOProvider:
    """Wraps a user-supplied `complete(system, user) -> str` function.

    Use this when your vendor isn't in our built-in list. Pass any callable
    that takes (system_prompt: str, user_prompt: str) and returns the
    response text. canopy handles the rest of the fill pipeline.

    Example:
        def my_complete(system: str, user: str) -> str:
            import urllib.request, json
            ...  # your vendor's HTTP call
            return response_text

        provider = BYOProvider(complete_fn=my_complete)
        result = provider.complete(system, user)
    """

    def __init__(self, *, complete_fn: Callable[[str, str], str]) -> None:
        self._fn = complete_fn

    def complete(self, system: str, user: str) -> str:
        # Exceptions from the user's function propagate unchanged.
        # canopy doesn't swallow them; if you want resilience, wrap your fn.
        return self._fn(system, user)


# ─── factory helpers ───────────────────────────────────────────────────


def anthropic_provider_for(*, api_key: str, base_url: str, model: str) -> AnthropicProvider:
    """Build an Anthropic-format provider. The default for MiniMax."""
    return AnthropicProvider(api_key=api_key, base_url=base_url, model=model)


def openai_provider_for(*, api_key: str, base_url: str, model: str) -> OpenAIProvider:
    """Build an OpenAI-compat provider. Default for OpenAI / Ollama / etc."""
    return OpenAIProvider(api_key=api_key, base_url=base_url, model=model)