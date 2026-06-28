# Cohere

canopy ships with **CohereProvider** which calls the **Cohere v2 chat API**.

## When to use this provider

- You have a Cohere API key and want direct access (no OpenRouter middleman)
- You want to use Cohere's Command R+ / Command R models for the descriptions
- You're already paying Cohere

## Models

- `command-r-plus` (recommended; best quality)
- `command-r` (cheaper, smaller)
- `command-light` (cheapest, fastest)

Full list: https://docs.cohere.com/docs/models

## Default model

`command-r-plus`

## Endpoint

```
POST https://api.cohere.com/v2/chat
```

## Headers

| Header | Value |
|---|---|
| `content-type` | `application/json` |
| `authorization` | `Bearer YOUR_COHERE_KEY` |

## Request body shape

```json
{
  "model": "command-r-plus",
  "messages": [
    {"role": "system", "content": "You are a YAML description generator..."},
    {"role": "user", "content": [{"type": "text", "text": "Describe these paths..."}]}
  ]
}
```

Note Cohere v2 uses a list of content blocks (not a flat string) for the user message — same shape as the Anthropic tool-use content blocks.

## Response body shape

```json
{
  "message": {
    "role": "assistant",
    "content": [{"type": "text", "text": "{...JSON...}"}]
  }
}
```

## Setup

1. Get an API key at https://dashboard.cohere.com/api-keys
2. Run:
   ```sh
   canopy setup --non-interactive \
       --provider cohere \
       --model command-r-plus \
       --api-key "$COHERE_API_KEY" \
       --client claude-code --global-config
   ```

## Why it's in canopy

Cohere's Command R+ model is competitive with GPT-4o for structured-output tasks, and Cohere has generous free tier limits for low-volume use.