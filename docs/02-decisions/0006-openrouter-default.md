# ADR-0006: OpenRouter as default provider

**Status:** Accepted — 2026-06-28
**Supersedes:** — (ADR-0003 said Anthropic was default for back-compat)
**Related:** ADR-0001, docs/providers/README.md

## Context

In v0.3.0, Anthropic was the default provider because canopy's reference implementation (`~/.hermes/scripts/canopy.py`) used it, and the early user base (one developer) only needed Anthropic/MiniMax.

In v0.4.0, we're opening canopy to a broader audience. The new users will likely have OpenAI, Gemini, or no provider preference at all. We need a sensible default.

Candidates:
1. **Anthropic** — keep the existing default; users from other vendors have to pick.
2. **OpenAI** — biggest market share, but requires OpenAI account.
3. **OpenRouter** — one API key gives access to 100+ models from every vendor.
4. **First-run interactive prompt** — no default; force a choice every time.

## Decision

**OpenRouter is the new default** per user preference (stated mid-Phase-3): "my default for models would be openrouter, then anthopic, openai, but should be open to having any model provided".

- `canopy setup` defaults to provider=openrouter, model=anthropic/claude-3.5-sonnet
- canopy accepts any free-form model name (no validation against vendor catalog)
- All other providers remain first-class — users who want Anthropic-direct or OpenAI-direct just pick from the interactive menu

## Consequences

- ✅ New users can run `canopy setup` and have a working fill with one OpenRouter key.
- ✅ Users can A/B models cheaply without re-setup.
- ✅ canopy still works for the original Anthropic/MiniMax user (back-compat preserved via `canopy.llm.call_minimax`).
- ⚠️ OpenRouter charges a small fee on top of vendor list price. Documented in `docs/providers/openrouter.md`.
- ⚠️ OpenRouter attribution headers (`HTTP-Referer`, `X-Title`) are sent on every request. Documented.

## Free-form model field

`--model` is **never validated** against a vendor's catalog. If the user types a wrong model name, the vendor returns 404 and `canopy fill` exits with a clear error. This is intentional: it lets users try new models on day one of a vendor's release without waiting for canopy to ship an update.