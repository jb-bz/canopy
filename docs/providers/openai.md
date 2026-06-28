# OpenAI / OpenAI-compatible providers

canopy ships with **OpenAIProvider** which calls the **OpenAI Chat Completions API** at `POST /v1/chat/completions`. This is the de-facto industry-standard LLM API, and dozens of vendors expose compatible endpoints.

## When to use this provider

- You're calling **OpenAI directly** (GPT-4o, GPT-4o-mini, o1, etc.)
- You're using **Mistral**, **Groq**, **Together**, **Fireworks**, **DeepSeek**, **xAI (Grok)**
- You're running **Ollama**, **LM Studio**, **vLLM**, or any other local / self-hosted OpenAI-compat server
- You're pointing at **LiteLLM proxy** or **OpenRouter-compatible** (but prefer the dedicated `openrouter` provider for OpenRouter specifically — it adds attribution headers)

## Default model

`gpt-4o-mini` — cheap, fast, good enough for YAML descriptions.

## Endpoint

```
POST {base_url}/v1/chat/completions
```

Examples:
- OpenAI direct: `https://api.openai.com/v1`
- Ollama (with `--api openai` or built-in): `http://localhost:11434/v1`
- LM Studio: `http://localhost:1234/v1`
- Groq: `https://api.groq.com/openai/v1`
- Together: `https://api.together.xyz/v1`

canopy strips a trailing `/v1` from the base URL automatically, so you can pass either form.

## Headers

| Header | Value |
|---|---|
| `content-type` | `application/json` |
| `authorization` | `Bearer YOUR_API_KEY` |

## Request body shape

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a YAML description generator..."},
    {"role": "user", "content": "Describe these paths..."}
  ]
}
```

## Response body shape

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "{...JSON...}"
      }
    }
  ],
  ...
}
```

## Setup

```sh
canopy setup --non-interactive \
    --provider openai \
    --model gpt-4o-mini \
    --base-url https://api.openai.com/v1 \
    --api-key "$OPENAI_API_KEY" \
    --client claude-code --global-config
```

For Ollama (local, no API key needed):

```sh
canopy setup --non-interactive \
    --provider openai \
    --model llama3 \
    --base-url http://localhost:11434/v1 \
    --api-key ollama \
    --client claude-code --global-config
```

## Why it's in canopy

OpenAI is the most widely-deployed LLM API. Adding it makes canopy usable for the majority of developers who have an OpenAI or OpenAI-compat key without any extra setup steps.