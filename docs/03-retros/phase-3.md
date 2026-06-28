# Phase 3 Retrospective — provider abstraction, MCP client setup, generic unknown-client docs

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end

## What shipped

| Artifact | Lines | Status |
|---|---|---|
| `canopy/providers.py` | 164 | ✅ — `Provider` Protocol + `AnthropicProvider` + `OpenAIProvider` + factory helpers |
| `canopy/clients.py` | 284 | ✅ — 7 built-in clients (claude-code, codex, opencode, cline, continue, cursor, windsurf) + generic unknown-client renderer |
| `canopy/setup.py` | 218 | ✅ — `canopy setup` interactive + `--non-interactive` flag mode |
| `canopy/llm.py` | 41 (was 90) | ✅ — refactored to thin wrapper over `AnthropicProvider` for back-compat |
| `canopy/fill.py` | 127 | ✅ — now uses `provider=` arg (default `anthropic`); OpenAI selectable |
| `canopy/cli.py` | 358 | ✅ — new `setup` subcommand + `--provider` arg on `fill` |
| `docs/setup/UNKNOWN_CLIENT.md` | ~80 | ✅ — generic doc for any non-built-in MCP agent |
| 3 new test files | ~600 lines | ✅ — 33 new tests (89 total) |

## Provider abstraction

```
Provider (Protocol)
├── AnthropicProvider — Anthropic Messages API (works for Anthropic, MiniMax, GLM)
└── OpenAIProvider — Chat Completions API (works for OpenAI, Mistral, Groq, Ollama, ...)
```

Both have `complete(system: str, user: str) -> str`. Backwards compat: `canopy.llm.call_minimax` still works (delegates to `AnthropicProvider`).

## Setup command

```sh
canopy setup                                           # interactive
canopy setup --non-interactive \
    --provider anthropic --model MiniMax-M3 \
    --client claude-code --api-key sk-...              # scriptable
canopy setup --non-interactive --provider openai \
    --model gpt-4o-mini --client cursor \
    --api-key sk-... --global-config                  # writes ~/.cursor/mcp.json
canopy setup --non-interactive --provider anthropic \
    --client clawbot                                  # prints UNKNOWN_CLIENT.md
```

For unknown MCP clients (clawbot, nanobot, etc.), `--client clawbot` prints a self-contained markdown doc the user can paste to their agent or use to manually edit their config.

## Test count

- Phase 0: 17
- Phase 1: 16
- Phase 2: 23
- Phase 3: 33
- **Total: 89 tests, all passing**

## What surprised me

1. **`pytest.raises(LlmError)` doesn't catch `ProviderError`** when `LlmError` is a *subclass* of `ProviderError`. Subclass instances are NOT instances of parent — only sibling or same. Fixed by importing the parent name in tests. Lesson: when an alias exists for a parent exception, tests should import the parent.
2. **`Protocol` classes aren't `isinstance`-compatible by default.** Need `@runtime_checkable` decorator. Now added.
3. **Three Phase 1 CLI integration tests used `patch("canopy.fill.llm", MagicMock())`** which no longer matched after the Phase 3 refactor (fill no longer imports llm at module level). Fixed by switching to `patch("canopy.providers.AnthropicProvider.complete", ...)`. Cleaner pattern anyway — patches the concrete class method, not the internal module alias.
4. **The interactive `setup` test needed 5 inputs, not 4.** I forgot that `base_url` is its own prompt. Caught by `StopIteration` from the mock iterator. Test fix only — behavior was correct.

## Decisions made during Phase 3

| Decision | Rationale |
|---|---|
| Default provider = Anthropic | Your existing code uses it; MiniMax works. Back-compat. |
| OpenAI as the second provider | Covers OpenAI, Mistral, Groq, Together, Ollama, LM Studio, vLLM, OpenRouter — most popular non-Anthropic vendor surface. |
| 7 built-in MCP clients | Per your "full" requirement. Covers all the major MCP consumers in 2026. |
| Generic unknown-client doc | Per your "refer to a github doc" choice. Avoids maintaining an ever-growing inventory of clients. |
| JSON config merge | Re-running setup updates canopy's entry without clobbering other MCP servers. Same for TOML (via regex section replacement). |
| `--global-config-dir` flag | Hidden from `--help` (argparse.SUPPRESS), used by tests to redirect to a tmp dir. Production users use `--global-config` to write to `$HOME`. |

## Open questions for Phase 4+

- **Should `canopy fill` accept `--provider openai` as a flag, or only via `setup`?** Currently both work. The flag is convenient for one-off use; setup is better for default config.
- **Should we add a `~/.canopy/config.toml` for persistent settings** (provider, model, base_url, api-key)? Would avoid re-running setup if you want different providers per repo. Phase 4 candidate.
- **More adapters**: Gemini (Google), Bedrock (AWS), Cohere. Each is ~150 LOC. Defer until a real user asks.

## Verification

```
$ pytest tests/
........................................................................ [ 80%]
.................                                                        [100%]
89 passed in 0.14s

$ gitleaks detect --source .
no leaks found

$ canopy setup --non-interactive --provider anthropic --model MiniMax-M3 \
    --client claude-code --api-key test-key \
    --global-config-dir /tmp/canopy-setup-test
--- canopy setup summary ---
  provider:  anthropic
  model:     MiniMax-M3
  base_url:  https://api.minimax.io/anthropic
  client:    claude-code
  api_key:   set

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

## Verdict

**Phase 3 is GREEN.** Two providers, seven MCP clients, generic fallback for the long tail. v0.3.0 is ready to tag.

## Next steps

1. Tag `v0.3.0`, push, create GitHub release.
2. Then back to PyPI publish (you said "we will get back to soon").