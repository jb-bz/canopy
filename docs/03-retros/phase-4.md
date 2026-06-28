# Phase 4 Retrospective — 6 providers, BYO stub, per-provider docs

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end

## What shipped

| Artifact | Status |
|---|---|
| `canopy/providers.py` extended: +GeminiProvider, +BedrockProvider, +CohereProvider, +OpenRouterProvider, +BYOProvider, +bedrock_sigv4_sign() | ✅ |
| `canopy/setup.py` extended: provider list = openrouter/anthropic/openai/gemini/bedrock/cohere; default = openrouter + anthropic/claude-3.5-sonnet | ✅ |
| `docs/providers/README.md` — index of all providers | ✅ |
| `docs/providers/anthropic.md` — full Anthropic / MiniMax guide | ✅ |
| `docs/providers/openai.md` — full OpenAI / Ollama / etc. guide | ✅ |
| `docs/providers/openrouter.md` — full OpenRouter guide | ✅ |
| `docs/providers/gemini.md` — full Gemini guide | ✅ |
| `docs/providers/bedrock.md` — full Bedrock + SigV4 explainer | ✅ |
| `docs/providers/cohere.md` — full Cohere guide | ✅ |
| `docs/providers/BYO.md` — full BYO guide + future-OSS-project seed | ✅ |
| `docs/02-decisions/0006-openrouter-default.md` — ADR for default change | ✅ |
| `docs/assets/canopy-banner.png` — repo banner | ✅ |
| README banner image embedded | ✅ |
| 11 new tests in `tests/test_phase4_providers.py` (100 total) | ✅ |

## Provider matrix (final, v0.4.0)

| Provider | Endpoint | Auth | Default model | Tests |
|---|---|---|---|---|
| OpenRouter | `/v1/chat/completions` | `Bearer sk-or-...` | `anthropic/claude-3.5-sonnet` | ✅ |
| Anthropic | `/v1/messages` | `x-api-key` | `MiniMax-M3` | ✅ |
| OpenAI | `/v1/chat/completions` | `Bearer sk-...` | `gpt-4o-mini` | ✅ |
| Gemini | `:generateContent` | `x-goog-api-key` | `gemini-2.0-flash-exp` | ✅ |
| Bedrock | `:invoke` (SigV4) | AWS access key + secret | `anthropic.claude-3-sonnet-20240229-v1:0` | ✅ |
| Cohere | `/v2/chat` | `Bearer` | `command-r-plus` | ✅ |
| BYO | user-defined | user-defined | user-defined | ✅ |

## What surprised me

1. **`urllib.request.Request` lowercases header names**. My test asserted `"HTTP-Referer" in headers` but the dict had `http-referer`. Same data, different key. Fixed by looking up via `k.lower()` in tests.
2. **Cohere v2 uses content blocks** (`[{"type": "text", "text": "..."}]`) for the user message, not a flat string. My test had `"user"` instead of `[{"type": "text", "text": "user"}]`. Caught by the test; production code was right.
3. **Default provider change broke 1 existing test**. Phase 3 had `test_default_provider_is_anthropic` asserting the default. The user changed their mind to OpenRouter for v0.4.0; I updated both `setup.py` and the test. Backward-compat flag kept `Anthropic` as a first-class option — no code in `fill_missing()` cares which is "default".
4. **AWS SigV4 fits in ~30 lines** using only `hmac` + `hashlib`. No boto3 dep. Saves ~30 MB of wheel size and zero transitive deps.

## Decisions made during Phase 4

| Decision | Rationale |
|---|---|
| Default provider = OpenRouter | Per user preference. One key, many models. |
| Bedrock body shape = Anthropic Messages | Matches what we already test; users wanting Titan/Llama/Mistral-on-Bedrock use BYO. |
| Bedrock SigV4 inline (no boto3) | -30 MB wheel, no transitive deps, transparent signing. |
| BYO provider is a Protocol hook, not a plugin system | Simplest thing that works. No entry-point discovery, no plugin manifest. Users just subclass. |
| All providers in `canopy/providers.py` (one file) | Easier to read the matrix; splits when we extract to a standalone library. |
| `HTTP-Referer` + `X-Title` for OpenRouter | Required by OpenRouter's app-attribution terms. canopy sends canopy's repo URL. |
| Free-form `--model` field | No validation. Vendors ship new models faster than canopy can update. |

## The future OSS project idea — captured

`canopy/providers.py` is the seed of a standalone "model provider component" library. When the time comes:

1. Extract `Provider` Protocol + all built-in adapters into `canopy-providers` (or `model-bridge`) PyPI package.
2. canopy's repo-orientation machinery depends on `canopy-providers` instead of inlining it.
3. Other tools (chat UIs, eval harnesses, code analyzers) can depend on `canopy-providers` without dragging in canopy's YAML/scanner/excludes/etc.

The `BYO` provider is the public-facing proof that this separation is clean: a 30-line subclass, no monkey-patching.

## Test count

- Phase 0: 17
- Phase 1: 16
- Phase 2: 23
- Phase 3: 33
- Phase 4: 11
- **Total: 100 tests, all passing**

## Verification

```
$ pytest tests/
........................................................................ [ 72%]
............................                                             [100%]
100 passed in 0.14s

$ gitleaks detect --source .
no leaks found
```

## Verdict

**Phase 4 is GREEN.** Six providers + BYO + full per-provider docs + ADR. v0.4.0 ready to tag.

## Next steps

1. Tag `v0.4.0`, push, create GitHub release.
2. Then PyPI publish (the long-deferred "we'll get back to it" item).