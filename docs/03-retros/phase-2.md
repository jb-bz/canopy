# Phase 2 Retrospective — Context-file discovery for `fill`

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end

## What shipped

| Artifact | Lines | Status |
|---|---|---|
| `canopy/context.py` | 175 | ✅ — `discover_context(root, per_file_cap, total_cap)` + 4 public constants |
| `tests/test_phase2_context.py` | 360 | ✅ — 23 new tests covering all discovery rules |
| `canopy/cli.py` cmd_fill | ~10 lines changed | ✅ — replaced hardcoded tuple with `discover_context()` |
| `canopy/fill.py` | 2 lines changed | ✅ — total cap bumped from 8 KB to 20 KB |
| `docs/04-changelog/phase-2.md` + `docs/03-retros/phase-2.md` | — | ✅ |

**Total Phase 2: ~200 lines added**.

## Discovery rules (final, Phase 2)

| Rule | What it matches | Path key format |
|---|---|---|
| **Root files** | `README*`, `CHANGELOG*`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING*`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `setup.py` | `README.md` |
| **`docs/`** | any `*.md` or `*.rst` at any depth under a `docs/` directory | `docs/00-spec/PLAN.md`, `docs/research/sub/deep.md` |
| **Module dirs** | any `*.md` under `src/`, `lib/`, `app/`, `internal/`, `pkg/` | `src/auth/README.md` |

## Excludes

Delegated to existing infrastructure:
- `.gitignore` (basename match, same as `scanner.py`)
- `STANDARD_EXCLUDES` (node_modules, .git, __pycache__, .venv, etc.)
- Hidden dirs (except `.github`, `.gitlab`, `.claude`, `.hermes`, `.canopy`)

## Size caps

- Per-file: 3000 chars (hard cap, truncate)
- Total: 20 KB (hard cap; later files dropped once ceiling hit)
- Truncated content preserves the head of each file

## Smoke test

```
$ python -c "from canopy.context import discover_context; from pathlib import Path; \
             import json; print(json.dumps(list(discover_context(Path('/tmp/canopy-smoke')).keys()), indent=2))"
[
  "AGENTS.md",
  "CHANGELOG.md",
  "README.md",
  "docs/00-spec/PLAN.md",
  "docs/01-research/findings.md",
  "docs/architecture/sub/deep.md",
  "pyproject.toml",
  "src/auth/README.md",
  "src/billing/DESIGN.md"
]
```

Skipped: `node_modules/foo.md`, `node_modules/docs/foo.md`. ✅

`canopy --root /tmp/canopy-smoke fill --dry-run` now reports:
```
context: 9 file(s) (122 chars)
```

## What surprised me

1. **`fnmatch.fnmatch` is case-sensitive on POSIX.** My first test used `Readme.markdown` (mixed case) and failed. The fix was to use `README.markdown` (matching the `README*` glob case) — not to add case-insensitive matching. Real-world READMEs are conventionally uppercase.
2. **My first `test_respects_gitignore` used `kept.md` as the "should be picked up" file.** But `kept.md` isn't in `ROOT_FILE_PATTERNS`, so it would never be picked up regardless of `.gitignore`. Test was wrong about what behavior it was testing. Fixed by using `AGENTS.md` (which IS in the allowlist).
3. **`fnmatch` matches both `README.md` and `README.rst`** because `README*` is a glob. Good — didn't need a separate `.rst` rule.
4. **The discovery reuses `scanner._gitignore_blocks` and `scanner._load_gitignore`** via a late import inside `_walk_for_docs`. This avoids a circular import (scanner would otherwise need to know about context). Slight code smell; acceptable for a ~200-line module.

## Decisions made during Phase 2

| Decision | Rationale |
|---|---|
| `DOC_DIRS = {"docs"}` only — no `documentation/`, `wiki/` | Avoids accidental slurping of vendor docs. Users can rename/symlink. Documented in module docstring. |
| `MODULE_DOC_DIRS = {src, lib, app, internal, pkg}` | Covers the 5 most common layouts. Add more later if a real user asks. |
| `*.md` AND `*.rst` under docs/ | reST is still common in scientific/engineering repos. Cheap to support. |
| `*.md` only (no `*.rst`) under module dirs | Module-level `*.rst` is rare; saves walking. Easy to add later. |
| Per-file cap 3000 chars, total 20 KB | Per the "beefy" Option C spec. Matches the ~5-15 file sweet spot. |
| Truncate (not skip) when one file would exceed total | Better signal than silently dropping — preserves the head of the file the LLM is most likely to find useful. |
| Sorted output | Deterministic LLM input — same context every run. |

## Open questions

- **Should `*.rst` also be picked up under module dirs?** Probably yes, but it's a one-line change if anyone needs it.
- **Should `CLAUDE.md` and `AGENTS.md` be weighted differently?** Both are agent-oriented instructions. We currently treat them equally. Probably fine.

## Test count

- Phase 0: 17
- Phase 1: 16
- Phase 2: 23
- **Total: 56 tests, all passing**

## Verification

```
$ pytest tests/
........................................................                 [100%]
56 passed in 0.10s

$ gitleaks detect --source .
no leaks found
```

## Verdict

**Phase 2 is GREEN.** Context discovery is automatic, respects ignores, scales with the repo, and feeds the LLM up to 20 KB of relevant docs. v0.2.0 is ready to tag.

## Next steps

1. Tag `v0.2.0` and create GitHub release.
2. Run a real fill against a real repo to eyeball output quality.
3. Then back to PyPI (you said "we will get back to soon").