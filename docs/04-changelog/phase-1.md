# Phase 1 — `fill` subcommand + bws/llm/hindsight modules

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end

## What ships

- `canopy/bws.py` — `fetch_secret(secret_id) -> str` with typed `BwsError`
- `canopy/llm.py` — `call_minimax(prompt, ...) -> str` with typed `LlmError`
- `canopy/fill.py` — `fill_missing(missing, ctx, ...) -> {path: desc}` with batching, JSON parsing, regex fallback
- `canopy/hindsight.py` — `retain(facts, url, bank) -> bool` best-effort
- `canopy/cli.py` — `cmd_fill` wired through argparse with `--dry-run`, `--retain-hindsight`, `--batch`, `--max-words`, `--bws-secret`, `--base-url`, `--model`, `--hindsight-url`, `--hindsight-bank`
- `tests/test_phase1.py` — 16 new tests (33 total)

## What's now usable

```sh
canopy --root /path/to/repo init
canopy --root /path/to/repo fill                  # LLM-fill all missing descriptions
canopy --root /path/to/repo fill --dry-run        # preview without calling LLM
canopy --root /path/to/repo fill --retain-hindsight  # log to Hindsight bank
```

Requires `bws` CLI installed and `BWS_ACCESS_TOKEN` in env (or `source ~/.config/bws/env`). Default secret UUID is the MiniMax key from `~/.hermes/scripts/canopy.py` line 57.

## Verification

```
$ pytest tests/ -v
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
collected 33 items

tests/test_phase0.py .................                                   [ 51%]
tests/test_phase1.py ................                                    [100%]

============================== 33 passed in 0.06s ==============================
```

CLI smoke test (init + dry-run fill + help):
```
$ canopy --root /tmp/smoke init
wrote /tmp/smoke/canopy.yaml
$ canopy --root /tmp/smoke fill --dry-run
missing descriptions: 0
new paths (will be added): 7
(dry-run) would call LLM and rewrite YAML
$ gitleaks detect --source .
no leaks found
```

## Attribution

- Retrospective: [`../03-retros/phase-1.md`](../03-retros/phase-1.md)
- Plan: [`../00-spec/PLAN.md`](../00-spec/PLAN.md) §7 Build Order
- ADRs: [`../02-decisions/`](../02-decisions/)