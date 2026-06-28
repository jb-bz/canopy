# Phase 3 — multi-provider, multi-client setup wizard

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end

## What ships

- `canopy/providers.py` — `Provider` Protocol + `AnthropicProvider` + `OpenAIProvider` + factory helpers
- `canopy/clients.py` — 7 built-in MCP clients + generic unknown-client doc renderer
- `canopy/setup.py` — interactive TUI + `--non-interactive` flag mode
- `canopy fill` accepts `--provider {anthropic,openai}` (default: anthropic for back-compat)
- `canopy setup` subcommand registered in the main CLI
- `docs/setup/UNKNOWN_CLIENT.md` — printed when `--client <name>` isn't in the built-in list
- 33 new tests (89 total)

## Coverage

**Providers (2):**
- Anthropic — works for Anthropic, MiniMax, GLM (any Anthropic-format endpoint)
- OpenAI — works for OpenAI, Mistral, Groq, Together, Ollama, LM Studio, vLLM, OpenRouter, LiteLLM proxy

**MCP clients (7 built-in, unlimited via doc):**
- Claude Code, Codex, OpenCode, Cline, Continue, Cursor, Windsurf
- Anything else: prints `docs/setup/UNKNOWN_CLIENT.md` with a self-contained prompt the user can paste to their agent

## Usage

```sh
# Interactive
canopy setup

# Non-interactive (CI / dotfiles)
canopy setup --non-interactive --provider anthropic --model MiniMax-M3 \
    --client claude-code --api-key sk-... --global-config

# Unknown client → prints doc
canopy setup --non-interactive --provider anthropic --client clawbot
```

## Verification

```
$ pytest tests/
89 passed in 0.14s

$ gitleaks detect --source .
no leaks found
```

CLI smoke test:
```
$ canopy setup --non-interactive --provider anthropic --model MiniMax-M3 \
    --client claude-code --api-key test-key \
    --global-config-dir /tmp/canopy-setup-test
wrote /tmp/canopy-setup-test/.mcp.json

$ cat /tmp/canopy-setup-test/.mcp.json
{
  "mcpServers": {
    "canopy": {
      "command": "python",
      "args": ["-m", "canopy", "serve"]
    }
  }
}
```

## Attribution

- Retrospective: [`../03-retros/phase-3.md`](../03-retros/phase-3.md)
- OpenAI Chat Completions API: https://platform.openai.com/docs/api-reference/chat
- Anthropic Messages API: https://docs.anthropic.com/claude/reference/messages_post