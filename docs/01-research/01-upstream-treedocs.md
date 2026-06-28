# Upstream comparison: DandyLyons/treedocs vs `~/.hermes/scripts/canopy.py`

**Date:** 2026-06-28
**Status:** Frozen — informs the entire `canopy` package design.

---

## Summary

There are two reference implementations we are drawing from:

1. **DandyLyons/treedocs** — the upstream Swift CLI bundled in an Xcode package.
2. **`~/.hermes/scripts/canopy.py`** — a ~540-line Python 3.10+ drop-in by jb-bz that already exists and works.

The `canopy` package is the "proper package" version of #2, with schema/format compatibility with #1. We're not writing a fresh design — we're package-ifying what already works.

## What the upstream tool does (the contract)

- Maintain a YAML map of a repo's file tree with one `_description` per path.
- Schema URL: `https://dandylyons.github.io/treedocs/schemas/0.2.0/treedocs.schema.json`
- Header on save advertises the schema URL (for `yaml-language-server` editor integration).
- YAML top-level: `{tree: {...}, signature: "sha256:..."}`.
- Each tree entry: `{_kind: "file" | "dir", _description: "..."}`.
- Signature = SHA256 over sorted, newline-joined paths. Descriptions NOT part of signature.
- Subcommands: `init`, `fill`, `check`, `show`, `explore`, `update`.

## What `~/.hermes/scripts/canopy.py` adds on top

| Feature | Where | What it does |
|---|---|---|
| `STANDARD_EXCLUDES` | line 64-70 | Set of dirs/files to never scan (`.git`, `node_modules`, `__pycache__`, etc.) |
| `_DOTDIR_ALLOWLIST` | line 108 | `.github`, `.gitlab`, `.claude`, `.hermes` are kept despite leading dot |
| LLM fill via bws + MiniMax | line 200+ | Fetches `MINIMAX_API_KEY` from bws at runtime; calls the Anthropic-compatible API to batch-fill descriptions |
| `--retain-hindsight` | line 543 | Optional: log fill runs to Hindsight bank `coding-agent-stack` |
| `--dry-run` for fill | line 542 | Don't write anything; just print what would change |

## What `canopy` (this package) keeps

- ✅ All upstream subcommands: `init`, `fill`, `check`, `show`, `explore`, `update`
- ✅ Same schema URL header on save
- ✅ Same YAML structure
- ✅ Same signature algorithm
- ✅ Same `STANDARD_EXCLUDES` set (and `canopy.yaml` is in the excludes so it never appears in its own scan)
- ✅ Same dot-dir allowlist
- ✅ `--root` and `--yaml` flags with the same defaults

## What we add

- ✅ Multi-file package with proper module boundaries (vs 540-line monolith)
- ✅ pytest test suite (none in `~/.hermes/scripts/canopy.py`)
- ✅ `pyproject.toml` with `console_scripts` entry point
- ✅ gitleaks pre-commit hook
- ✅ GitHub Actions CI workflow

## What we defer to Phase 1+

- ⏳ LLM fill loop (re-use `~/.hermes/scripts/canopy.py` line 200+ verbatim, just import the helper or copy-paste the function)
- ⏳ `--retain-hindsight` flag
- ⏳ Full gitignore semantics (anchors, negation, `**`) — current scope: basename match only

## Sources

- Upstream repo: https://github.com/DandyLyons/treedocs
- Schema URL: https://dandylyons.github.io/treedocs/schemas/0.2.0/treedocs.schema.json
- Local reference impl: `~/.hermes/scripts/canopy.py` (540 lines, MIT)