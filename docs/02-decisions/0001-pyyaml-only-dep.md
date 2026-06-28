# ADR-0001: Single dependency — PyYAML

**Status:** Accepted — 2026-06-28
**Supersedes:** —

## Context

We need to maintain a YAML map of a repo's file tree with SHA256 drift detection. Candidates for the dependency footprint:

1. **No external deps** — `json` instead of YAML. Rejected: breaks compat with upstream treedocs schema.
2. **PyYAML only** — single dep, mature, in every Linux distro's package manager. Reads + writes YAML with stable roundtrip.
3. **ruamel.yaml** — preserves comments on roundtrip. Rejected: upstream treedocs drops comments on save (per `~/.hermes/scripts/canopy.py` line 166), so we don't need this.
4. **Full CLI framework (click, typer)** — rejected: stdlib `argparse` covers 6 subcommands fine. Adding click doubles dep count for zero benefit.

We are explicitly NOT pulling in:
- ❌ tree-sitter (this is not a code-graph tool)
- ❌ SQLite (no embedded DB needed)
- ❌ mcp (no MCP server — that's a different tool)
- ❌ requests/httpx (LLM fill goes through `urllib.request` or the `~/.hermes/scripts/canopy.py` bws helper)

## Decision

**Single runtime dep: `PyYAML>=6.0`.** Single dev dep: `pytest`.

## Consequences

- ✅ Tiny wheel footprint (~150 KB).
- ✅ `pip install -e .` works anywhere; no compiler, no native build.
- ✅ Zero transitive deps to audit.
- ⚠️ Have to use stdlib `hashlib` (SHA256) and stdlib `argparse` — fine, both are stable.
- ⚠️ LLM fill will need `urllib.request` (stdlib) for the API call, or a copy of the bws helper from `~/.hermes/scripts/canopy.py` lines 200-330.