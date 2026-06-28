# 02-decisions

Architecture Decision Records. One file per non-obvious choice.

## Format

Each ADR: Status, Context, Decision, Consequences.

## Files

| File | Decision |
|---|---|
| [`0001-pyyaml-only-dep.md`](0001-pyyaml-only-dep.md) | Single dependency: PyYAML. No tree-sitter, no SQLite, no MCP, no CLI framework |
| [`0002-multi-file-package.md`](0002-multi-file-package.md) | Multi-file package layout (vs single-file monolith in `~/.hermes/scripts/canopy.py`) |
| [`0003-treedocs-schema-compat.md`](0003-treedocs-schema-compat.md) | Byte-compatible YAML with DandyLyons/treedocs — same schema URL, same keys |

ADRs are append-only. To change a decision, write a new ADR that supersedes the old one.