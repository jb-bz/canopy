"""Thin wrapper around `AnthropicProvider` for v0.1.0 callers.

Phase 3 introduced `canopy.providers` with a proper Provider abstraction.
`call_minimax` is preserved here so v0.1.0 / v0.2.0 callers keep working.
New code should use `AnthropicProvider` (or `OpenAIProvider`) directly.
"""
from __future__ import annotations

from canopy.providers import AnthropicProvider, ProviderError


# Re-export the exception under the old name so existing imports keep working.
__all__ = ["call_minimax", "LlmError"]


class LlmError(ProviderError):
    """Deprecated alias for `canopy.providers.ProviderError`."""


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
    """Call the Anthropic-compatible messages API. Preserved for back-compat.

    New code should construct `canopy.providers.AnthropicProvider(...)`
    and call `.complete(system, user)`.
    """
    # max_tokens is accepted for back-compat; AnthropicProvider uses 2048.
    del max_tokens
    return AnthropicProvider(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
    ).complete(system=system or "", user=user_prompt)