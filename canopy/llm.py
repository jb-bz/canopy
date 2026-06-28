"""LLM client for the MiniMax / Anthropic-compatible API.

Wraps a single POST to `{base_url}/v1/messages`. No batching, no JSON
parsing — those live in `canopy.fill`. Keeping this module small makes
it trivially mockable and reusable for non-fill use cases.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request


class LlmError(RuntimeError):
    """Raised when the LLM call fails (HTTP error, network error, etc.)."""


def call_minimax(
    user_prompt: str,
    *,
    api_key: str,
    base_url: str,
    model: str,
    system: str | None = None,
    max_tokens: int = 2048,
    timeout: int = 60,
) -> str:
    """Call the Anthropic-compatible messages API.

    Returns the concatenated text from the response's `content` blocks.
    Raises `LlmError` on any HTTP / network failure.
    """
    messages = [{"role": "user", "content": user_prompt}]
    body: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system is not None:
        body["system"] = system

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise LlmError(f"HTTP {e.code}: {e.reason}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        raise LlmError(f"LLM call failed: {e}") from e

    text = "".join(
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    )
    return text