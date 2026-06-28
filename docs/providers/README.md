# Providers

canopy's `fill` command talks to LLM providers via a pluggable `Provider` abstraction. v0.4.0 ships with **six** built-in providers covering the most common cases:

| Provider | When to use | Doc |
|---|---|---|
| **OpenRouter** | Default. One API key gives you 100+ models from every vendor. Free-form model names. | [openrouter.md](openrouter.md) |
| **Anthropic** | Direct Anthropic API or Anthropic-compatible (MiniMax, GLM). | [anthropic.md](anthropic.md) |
| **OpenAI** | OpenAI Chat Completions API. Also works for Mistral, Groq, Together, Ollama, LM Studio, vLLM, OpenRouter-compatible vendors. | [openai.md](openai.md) |
| **Gemini** | Google Generative Language API. Gemini 1.5 / 2.0. | [gemini.md](gemini.md) |
| **Bedrock** | AWS Bedrock (Claude-on-AWS, Llama-on-AWS, Titan, Mistral-on-AWS). No boto3 dep. | [bedrock.md](bedrock.md) |
| **Cohere** | Cohere v2 chat API (Command R+, Command R). | [cohere.md](cohere.md) |
| **BYO** | Bring Your Own. Wire any HTTP API in 30 lines. | [BYO.md](BYO.md) |

## Picking a provider

**If you want one API key and access to everything**, start with OpenRouter — it routes to 100+ models and is what canopy defaults to.

**If you have direct vendor access** (Anthropic API key, OpenAI key, Google Cloud key, AWS credentials, Cohere key), pick that provider for slightly lower latency and direct billing.

**If your vendor isn't on the list**, use BYO — it's a 30-line subclass.

## Picking a model

canopy does NOT validate model names against a vendor's catalog. The model field is free-form text. If you mistype a model, the vendor returns 404 and `canopy fill` exits with a clear error message.

To see what models each provider offers:

- **OpenRouter**: https://openrouter.ai/models
- **Anthropic**: https://docs.anthropic.com/en/docs/about-claude/models
- **OpenAI**: https://platform.openai.com/docs/models
- **Gemini**: https://ai.google.dev/gemini-api/docs/models
- **Bedrock**: https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html
- **Cohere**: https://docs.cohere.com/docs/models

## Switching providers mid-session

```sh
canopy --root /path/to/repo fill --provider anthropic --model claude-3-5-sonnet-20241022
canopy --root /path/to/repo fill --provider openai    --model gpt-4o-mini
canopy --root /path/to/repo fill --provider openrouter --model meta-llama/llama-3-70b
canopy --root /path/to/repo fill --provider bedrock  --model anthropic.claude-3-sonnet-20240229-v1:0 --region us-east-1
```

No re-setup needed — flags override the saved config.

## The future OSS project idea

The `Provider` Protocol in `canopy/providers.py` is the seed of a standalone "model provider component" library. If the canopy project grows, the HTTP-to-vendor details (the `complete()` implementations) could be extracted into a separate package — say `canopy-providers` or `model-bridge` — and republished. Other tools (chat UIs, eval harnesses, code analyzers) could then depend on the provider library without dragging in canopy's repo-orientation machinery.

See [docs/02-decisions/0005-stdlib-only-runtime.md](../../02-decisions/0005-stdlib-only-runtime.md) and the Phase 4 retrospective (when written) for the design rationale.