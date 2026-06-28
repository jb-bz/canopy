# ADR-0002: Multi-file package layout

**Status:** Accepted — 2026-06-28
**Supersedes:** —

## Context

The reference implementation `~/.hermes/scripts/canopy.py` is a single ~540-line file with everything (scanner, YAML I/O, bws integration, LLM fill, argparse) mixed together. It works but is hard to test and hard to extend.

Candidates for the package layout:

1. **Single file** — exact mirror of `~/.hermes/scripts/canopy.py`. Pros: zero learning curve for users coming from the script. Cons: untestable in isolation; canopy.py itself has no tests.
2. **Multi-file package** — `canopy/` package with submodules: `scanner.py`, `yaml_io.py`, `missing.py`, `excludes.py`, `cli.py`. Pros: testable per module; clear boundaries. Cons: more files.
3. **Library + CLI split** — `canopy/` (importable) + `canopy-cli` (script). Pros: most "proper Python". Cons: heaviest for what's essentially a doc tool.

## Decision

**Multi-file package (option 2).** Module boundaries:

- `canopy/excludes.py` — `STANDARD_EXCLUDES` frozenset + `is_excluded()` (no deps)
- `canopy/scanner.py` — filesystem walk, gitignore, signature (depends on `excludes.py`)
- `canopy/yaml_io.py` — load/save/init (depends on `excludes.py`)
- `canopy/missing.py` — missing-description detection (no deps)
- `canopy/cli.py` — argparse + subcommand dispatch (depends on all of the above)
- `canopy/__main__.py` — `python -m canopy` entry (depends on `cli.py`)

Tests import modules directly; no need for full CLI invocation in unit tests.

## Consequences

- ✅ Each module has a single responsibility, easily testable.
- ✅ Phase 1's `fill` subcommand can live in its own `canopy/fill.py` (LLM logic) without bloating `cli.py`.
- ✅ Same command-line surface as the script — users don't need to learn anything new.
- ⚠️ More files to navigate. Mitigation: `docs/00-spec/PLAN.md` §3 has the full tree.