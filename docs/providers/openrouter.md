# OpenRouter

canopy's **default provider**. OpenRouter is a meta-router that gives you access to 100+ models (Anthropic Claude, OpenAI GPT, Meta Llama, Google Gemini, Mistral, DeepSeek, Cohere, etc.) through a single OpenAI-compatible API and one API key.

## Why OpenRouter is the default

Per user preference: **OpenRouter first**, then Anthropic, then OpenAI. Rationale:

- **One key, many models.** No need to sign up for every vendor individually.
- **Free-form model names.** Use `anthropic/claude-3.5-sonnet`, `openai/gpt-4o`, `meta-llama/llama-3.1-70b`, `google/gemini-2.0-flash-exp`, `deepseek/deepseek-chat`, etc.
- **OpenAI-compatible.** The API is just `/v1/chat/completions` — same shape as OpenAI, but you can route to any vendor.
- **App attribution.** Sends `HTTP-Referer` and `X-Title` headers per OpenRouter's requirement. canopy does this automatically.

## When to use this provider

Almost always. OpenRouter is a sensible default for:

- New users who don't know which vendor to commit to
- Users who want to A/B test models cheaply
- Users who need a model that isn't on OpenAI / Anthropic directly (Llama, DeepSeek, etc.)

## Endpoint

```
POST https://openrouter.ai/api/v1/chat/completions
```

## Headers

| Header | Value |
|---|---|
| `content-type` | `application/json` |
| `authorization` | `Bearer YOUR_OPENROUTER_KEY` |
| `HTTP-Referer` | `https://github.com/jb-bz/canopy` (canopy's repo URL) |
| `X-Title` | `canopy` |

## Default model

`anthropic/claude-3.5-sonnet` — balanced quality/cost/latency.

## Setup

```sh
canopy setup --non-interactive \
    --provider openrouter \
    --model anthropic/claude-3.5-sonnet \
    --api-key "$OPENROUTER_API_KEY" \
    --client claude-code --global-config
```

Get an API key at https://openrouter.ai/keys.

## Free-form model selection

```sh
# Use Claude via OpenRouter
canopy fill --provider openrouter --model anthropic/claude-3.5-sonnet

# Use Llama 3.1 70B
canopy fill --provider openrouter --model meta-llama/llama-3.1-70b-instruct

# Use DeepSeek
canopy fill --provider openrouter --model deepseek/deepseek-chat

# Use Gemini via OpenRouter (cheaper than direct Gemini API in some regions)
canopy fill --provider openrouter --model google/gemini-2.0-flash-exp:free
```

See the full model catalog at https://openrouter.ai/models.

## Pricing

OpenRouter passes through each vendor's list price minus a small fee. See https://openrouter.ai/models for per-model pricing.

## Why it's in canopy

User preference. One key, every model.