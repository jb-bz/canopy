# Anthropic / Anthropic-compatible providers

canopy ships with **AnthropicProvider** which calls the **Anthropic Messages API** at `POST /v1/messages`. This is the same protocol that powers [Claude](https://anthropic.com), and several other vendors expose compatible endpoints.

## When to use this provider

- You're calling **Anthropic directly** (Claude Opus, Sonnet, Haiku, etc.)
- You're using **MiniMax** at `https://api.minimax.io/anthropic` (Anthropic-format endpoint)
- You're using **GLM** or any other vendor that emulates the Anthropic Messages API

## Default model

`MiniMax-M3` — same as the rest of the user's stack (Hindsight, canopy's reference tool at `~/.hermes/scripts/canopy.py`).

## Endpoint

```
POST {base_url}/v1/messages
```

Examples:
- Anthropic direct: `https://api.anthropic.com`
- MiniMax: `https://api.minimax.io/anthropic`

## Headers

| Header | Value |
|---|---|
| `content-type` | `application/json` |
| `x-api-key` | Your API key |
| `anthropic-version` | `2023-06-01` |

## Request body shape

```json
{
  "model": "MiniMax-M3",
  "max_tokens": 2048,
  "system": "You are a YAML description generator...",
  "messages": [
    {"role": "user", "content": "Describe these paths..."}
  ]
}
```

## Response body shape

```json
{
  "content": [
    {"type": "text", "text": "{...JSON...}"}
  ],
  ...
}
```

canopy concatenates all `text` blocks from the `content` array.

## Setup

```sh
canopy setup --non-interactive \
    --provider anthropic \
    --model MiniMax-M3 \
    --base-url https://api.minimax.io/anthropic \
    --api-key "$BWS_MINIMAX_SECRET_ID" \
    --client claude-code --global-config
```

Or interactively: just run `canopy setup` and pick "anthropic" from the provider list.

## Backwards compatibility

`canopy.llm.call_minimax` is preserved as a thin wrapper around `AnthropicProvider`. Any code that called `call_minimax` in v0.1.0–v0.3.0 keeps working unchanged.

## Why it's in canopy

This is the provider the original `~/.hermes/scripts/canopy.py` was built against. Keeping it as the back-compat default ensures existing canopy users don't have to re-setup after upgrading.