"""LLM-fill orchestration.

Batches missing-description paths, calls the LLM in chunks, parses JSON,
falls back to regex extraction if the model returns malformed JSON, and
returns a `{path: description}` dict.

The reference impl `~/.hermes/scripts/canopy.py` lines 214-283 does the
same thing inline; we lift it into its own module so it's independently
testable.
"""
from __future__ import annotations

import json
import re

from canopy import bws, llm


# Hard caps mirroring the upstream reference.
_MAX_DESC_LEN = 200
_CONTEXT_FILE_TRUNC = 3000
# Default 20 KB total; canopy.cli passes the same value explicitly to
# canopy.context.discover_context so this is the fallback if called directly.
_CONTEXT_TOTAL_TRUNC = 20_000


def _build_context(ctx_files: dict[str, str]) -> str:
    """Render the context block (README/AGENTS.md/pyproject.toml/etc.) the LLM sees."""
    joined = "\n\n---\n\n".join(
        f"## {name}\n{content[:_CONTEXT_FILE_TRUNC]}"
        for name, content in ctx_files.items()
        if content
    )
    return joined[:_CONTEXT_TOTAL_TRUNC]


def _parse_response(text: str, batch: list[tuple[str, str]]) -> dict[str, str]:
    """Parse one LLM response. Returns {path: description} for that batch.

    Strategy:
    1. Strip code fences; try JSON.
    2. If JSON fails, regex-extract each path's quoted description from free text.
    """
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    out: dict[str, str] = {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for path, desc in parsed.items():
                if isinstance(desc, str):
                    out[path] = desc.strip()[:_MAX_DESC_LEN]
        return out
    except json.JSONDecodeError:
        pass

    # Fallback: regex per path
    for path, _ in batch:
        m = re.search(rf'"{re.escape(path)}"\s*:\s*"([^"]+)"', text)
        if m:
            out[path] = m.group(1).strip()[:_MAX_DESC_LEN]
    return out


def fill_missing(
    missing: list[tuple[str, str]],
    context_files: dict[str, str],
    *,
    base_url: str,
    model: str,
    secret_id: str,
    max_words: int,
    batch_size: int,
    provider: str = "anthropic",
) -> dict[str, str]:
    """Fill missing descriptions via the LLM. Returns {path: description}.

    `missing` is a list of (path, kind) tuples from `canopy.missing.missing_descriptions`.
    `context_files` is a dict of {filename: content} for files like README.md, AGENTS.md,
    pyproject.toml — used as LLM context.

    Implementation:
    - Fetches the API key from bws ONCE upfront (fail fast if bws is broken).
    - Builds the context once.
    - Calls the LLM in batches of `batch_size`, accumulating results.

    `provider` (Phase 3): 'anthropic' (default) or 'openai'. Selects which
    adapter from `canopy.providers` is used.
    """
    if not missing:
        return {}

    api_key = bws.fetch_secret(secret_id)
    context = _build_context(context_files)

    system_prompt = (
        "You write concise 1-line descriptions of repository files for a YAML "
        "tree-of-contents doc called treedocs. Be factual and brief "
        f"(max {max_words} words). Output ONLY valid JSON mapping path -> description."
    )

    # Phase 3: pick the right provider. Default to Anthropic for back-compat.
    from canopy.providers import (
        AnthropicProvider,
        OpenAIProvider,
        ProviderError,
    )
    if provider == "openai":
        prov = OpenAIProvider(api_key=api_key, base_url=base_url, model=model)
    else:
        prov = AnthropicProvider(api_key=api_key, base_url=base_url, model=model)

    results: dict[str, str] = {}
    for i in range(0, len(missing), batch_size):
        batch = missing[i : i + batch_size]
        paths_text = "\n".join(f"- {p} ({kind})" for p, kind in batch)
        user_prompt = (
            f"Repo context (truncated):\n{context}\n\n"
            f"Describe each path below:\n{paths_text}\n\n"
            f"Return JSON object only. Max {max_words} words per description."
        )
        try:
            text = prov.complete(system=system_prompt, user=user_prompt)
        except ProviderError:
            raise
        results.update(_parse_response(text, batch))

    return results