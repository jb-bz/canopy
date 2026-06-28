# Google Gemini

canopy ships with **GeminiProvider** which calls the **Google Generative Language API**.

## When to use this provider

- You want direct access to Google's Gemini models (no OpenRouter middleman)
- You have a Google Cloud project with the Generative Language API enabled
- You're running Gemini in Vertex AI and configured the endpoint to `https://generativelanguage.googleapis.com`

## Models

- `gemini-2.0-flash-exp` (recommended; fast + cheap)
- `gemini-1.5-pro` (highest quality)
- `gemini-1.5-flash` (fast)
- `gemini-1.5-flash-8b` (cheapest)

Full list: https://ai.google.dev/gemini-api/docs/models

## Default model

`gemini-2.0-flash-exp`

## Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
```

## Headers

| Header | Value |
|---|---|
| `content-type` | `application/json` |
| `x-goog-api-key` | Your Gemini API key |

## Request body shape

```json
{
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "Describe these paths..."}]
    }
  ],
  "systemInstruction": {
    "parts": [{"text": "You are a YAML description generator..."}]
  },
  "generationConfig": {"maxOutputTokens": 2048}
}
```

canopy omits `systemInstruction` when the system prompt is empty.

## Response body shape

```json
{
  "candidates": [
    {
      "content": {
        "parts": [{"text": "{...JSON...}"}],
        "role": "model"
      }
    }
  ]
}
```

canopy concatenates all `parts[].text` from all candidates.

## Setup

1. Create an API key at https://aistudio.google.com/apikey
2. Run:
   ```sh
   canopy setup --non-interactive \
       --provider gemini \
       --model gemini-2.0-flash-exp \
       --api-key "$GEMINI_API_KEY" \
       --client claude-code --global-config
   ```

## Why it's in canopy

Gemini 2.0 Flash is one of the cheapest models with quality comparable to GPT-4o for structured-output tasks like YAML description generation. Free tier available.