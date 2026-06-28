# Phase 2 — Context-file discovery for `fill`

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end

## What ships

- `canopy/context.py` — `discover_context(root, per_file_cap=3000, total_cap=20000) -> dict[str, str]`
- Auto-discovers: root files (README*, CHANGELOG*, AGENTS.md, CLAUDE.md, CONTRIBUTING*, package.json, pyproject.toml, Cargo.toml, go.mod, setup.py) + `docs/**/*.{md,rst}` + `src|lib|app|internal|pkg/**/*.md`
- Honors `.gitignore` + `STANDARD_EXCLUDES` (node_modules, .git, __pycache__, etc.)
- Per-file cap 3000 chars, total cap 20 KB (up from 8 KB in v0.1.0)
- `cmd_fill` now calls `discover_context()` instead of a hardcoded file tuple
- 23 new tests in `tests/test_phase2_context.py` (56 total, all green)

## Why

The hardcoded tuple in v0.1.0 only caught 5 file types at the repo root. Real context (nested `docs/00-spec/PLAN.md`, module-level READMEs, research notes) was invisible to the LLM. Phase 2 fixes that.

## Usage (unchanged from v0.1.0)

```sh
canopy --root /path/to/repo fill --dry-run    # see what context will be sent
canopy --root /path/to/repo fill              # actually fill
```

The new `context: N file(s) (M chars)` line in `--dry-run` output shows what was found.

## Verification

```
$ pytest tests/
........................................................                 [100%]
56 passed in 0.10s

$ gitleaks detect --source .
no leaks found
```

CLI smoke test against a fixture repo with `docs/`, `src/auth/`, `src/billing/`, `node_modules/`:
```
$ canopy --root /tmp/canopy-smoke fill --dry-run
missing descriptions: 0
new paths (will be added): 17
context: 9 file(s) (122 chars)
(dry-run) would call LLM and rewrite YAML
```

Discovered files (9): `AGENTS.md, CHANGELOG.md, README.md, docs/00-spec/PLAN.md, docs/01-research/findings.md, docs/architecture/sub/deep.md, pyproject.toml, src/auth/README.md, src/billing/DESIGN.md`. Skipped: everything under `node_modules/`.

## Attribution

- Retrospective: [`../03-retros/phase-2.md`](../03-retros/phase-2.md)
- Plan: [`../00-spec/PLAN.md`](../00-spec/PLAN.md) §7 Build Order
- Related: the original cap (8 KB) was in `~/.hermes/scripts/canopy.py` line 229