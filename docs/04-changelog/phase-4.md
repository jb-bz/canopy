# Phase 4 — 6 providers + BYO + per-provider docs

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end

## What ships

- 6 built-in LLM providers in `canopy/providers.py`:
  - **OpenRouter** (default) — one key, every model
  - **Anthropic** — direct or Anthropic-compat (MiniMax, GLM)
  - **OpenAI** — Chat Completions (OpenAI, Mistral, Groq, Together, Ollama, etc.)
  - **Gemini** — Google Generative Language API
  - **Bedrock** — AWS Bedrock with inline SigV4 signing (no boto3 dep)
  - **Cohere** — v2 chat API
- **BYO** (Bring Your Own) — `BYOProvider(complete_fn=...)` for any HTTP API in 30 lines
- Per-provider docs in `docs/providers/`:
  - `README.md` — index + future-OSS-project seed
  - `anthropic.md`, `openai.md`, `openrouter.md`, `gemini.md`, `bedrock.md`, `cohere.md`, `BYO.md`
- `canopy setup` updated: provider list = 6 options, default = OpenRouter + `anthropic/claude-3.5-sonnet`
- 11 new tests (100 total)
- ADR-0006: OpenRouter as default
- Repo banner image at `docs/assets/canopy-banner.png` + README banner

## Coverage

**Before v0.4.0:** 2 providers (Anthropic, OpenAI), no BYO, no per-provider docs.

**After v0.4.0:** 6 providers + BYO + docs for every one + SigV4 from scratch.

## Verification

```
$ pytest tests/
........................................................................ [ 72%]
............................                                             [100%]
100 passed in 0.14s

$ gitleaks detect --source .
no leaks found
```

CLI smoke test (`canopy setup --non-interactive --provider openrouter --model anthropic/claude-3.5-sonnet --client claude-code`) goes through; base URL defaults to OpenRouter's `https://openrouter.ai/api/v1`.

## Attribution

- Anthropic Messages API: https://docs.anthropic.com/claude/reference/messages_post
- OpenAI Chat Completions: https://platform.openai.com/docs/api-reference/chat
- OpenRouter API: https://openrouter.ai/docs
- Gemini API: https://ai.google.dev/gemini-api/docs
- AWS Bedrock InvokeModel + SigV4: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html
- Cohere v2 Chat: https://docs.cohere.com/reference/chat
- AWS SigV4 reference: https://docs.aws.amazon.com/general/latest/gr/sigv4-signed-request-examples.html