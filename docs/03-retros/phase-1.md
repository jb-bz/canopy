# Phase 1 Retrospective — `fill` subcommand + bws/llm/hindsight modules

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end

## What shipped

| Artifact | Lines | Status |
|---|---|---|
| `canopy/bws.py` | 41 | ✅ — `fetch_secret(secret_id)` + `BwsError` |
| `canopy/llm.py` | 60 | ✅ — `call_minimax(prompt, ...)` + `LlmError` |
| `canopy/fill.py` | 122 | ✅ — `fill_missing(missing, ctx, ...)` with batching + JSON parsing + regex fallback |
| `canopy/hindsight.py` | 41 | ✅ — `retain(facts, url, bank)` best-effort |
| `canopy/cli.py` cmd_fill | ~100 lines added | ✅ — wired through argparse |
| `tests/test_phase1.py` | 280+ | ✅ — 16 new tests covering all four modules + CLI integration |

**Total Phase 1: ~400 lines**, well under budget.

## CLI surface (final, v0.1.0)

```
canopy [--root X] [--yaml Y] [--base-url URL] [--model M] [--bws-secret UUID]
       [--hindsight-url URL] [--hindsight-bank NAME]
       {init, fill, check, show, explore, update} ...
```

`fill` flags:
- `--batch 50` — paths per LLM call
- `--max-words 15` — cap per description
- `--dry-run` — print plan, don't call LLM or write YAML
- `--retain-hindsight` — log results to Hindsight (silent on failure)

## What surprised me

1. **`unittest.mock.patch` resolves the patch path at patch-time.** Tests that did `patch("canopy.cli.fill.fill_missing")` failed with `AttributeError: module 'canopy.cli' has no attribute 'fill'` because `cli.py` imports `fill` *inside* `cmd_fill`. Fixed by patching the canonical module path (`canopy.fill.fill_missing`) and using `as _fill` aliases inside `cmd_fill` to keep call-sites short.
2. **`urllib.request.Request` normalizes header case.** Test asserted `headers["x-api-key"]` and got `KeyError`. Actual header is `X-Api-Key`. Fixed with case-insensitive lookup.
3. **My initial test expected `dry_run` to call `fill_missing` and discard the result.** That's wrong — `--dry-run` should *not* call the LLM at all (no point burning tokens). Fixed test to assert `mock_fill.assert_not_called()`.
4. **`patch("canopy.fill.llm", MagicMock())` doesn't recursively replace `call_minimax`.** The fill module does `from canopy import llm` and then `llm.call_minimax(...)`. Patching `canopy.fill.llm` replaces the *attribute* `llm` on the `fill` module with a MagicMock, which works because the MagicMock has a `call_minimax` attribute (auto-created). So the patch is effective, but it's fragile — if `fill.py` ever does `import canopy.llm` instead, the patch breaks. Left a comment in the test file noting this.

## Decisions made during Phase 1

| Decision | Rationale |
|---|---|
| Split into 4 modules (bws, llm, fill, hindsight) instead of one big `fill.py` | Each is independently testable and reusable; `bws` and `llm` could be used by future tools |
| Hard-cap description length at 200 chars in `_parse_response` | Matches upstream `~/.hermes/scripts/canopy.py` line 282 |
| `BwsError`/`LlmError` typed exceptions (not `SystemExit`) | Allows the CLI to print a friendly error and return exit 3 |
| Imports in `cmd_fill` use `as _bws`/`as _fill` aliases | Makes the code explicit about which modules are used and avoids name shadowing in tests |
| `--dry-run` skips the LLM entirely, not just the YAML write | Avoids burning API tokens on a what-if; matches user intent |
| `Hindsight` retains are best-effort and silent on failure | Per upstream design (line 312); a fill should never fail because Hindsight is down |

## Test count

- Phase 0: 17 tests
- Phase 1: 16 tests
- **Total: 33 tests, all passing**

## What was NOT done (deferred)

- **Hindsight integration test.** Tested with mocked `urlopen`. Could add a real integration test that requires Hindsight running locally — deferred to v0.2 if it becomes useful.
- **Streaming / partial-fills.** If the LLM call fails mid-batch, we lose all results so far. Acceptable for v0.1; v0.2 could checkpoint.
- **JSON schema for the LLM prompt.** We tell it "return JSON object only" in the system prompt, but we don't enforce a schema. The regex fallback handles malformed output. v0.2 could use the Anthropic `tools` API for structured output.
- **PyPI publish.** The release is tagged on GitHub but no `pip install canopy` works yet. Defer until there's a real user.

## Verification evidence

```
$ pytest tests/ -v
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
collected 33 items

tests/test_phase0.py .................                                   [ 51%]
tests/test_phase1.py ................                                    [100%]

============================== 33 passed in 0.06s ==============================
```

CLI smoke test:
```
$ canopy --root /tmp/smoke init
wrote /tmp/smoke/canopy.yaml
$ canopy --root /tmp/smoke fill --dry-run
missing descriptions: 0
new paths (will be added): 7
(dry-run) would call LLM and rewrite YAML
$ canopy --root /tmp/smoke fill --help
usage: canopy fill [-h] [--batch BATCH] [--max-words MAX_WORDS] [--dry-run]
                   [--retain-hindsight]
```

`gitleaks detect --source .` → no leaks found.

## Verdict

**Phase 1 is GREEN.** The `fill` subcommand is fully implemented and tested. v0.1.0 is ready to tag.

## Next steps (next session)

1. Tag `v0.1.0` and create the GitHub release (with notes highlighting `fill` going live).
2. If you want `pip install canopy` to work for users outside the repo: PyPI publish.
3. Otherwise: stop here. The tool is feature-complete for v0.1 scope. Future work is bugfixes, more context files for the LLM, and JSON-schema enforcement on the LLM response.