# 03-retros

Post-phase retrospectives. One file per shipped phase.

## Files

| File | Phase summary |
|---|---|
| [`phase-0.md`](phase-0.md) | Multi-file package skeleton, scanner, YAML I/O, drift, CLI working end-to-end |

## Format

Each retro: what shipped, what was NOT done, decisions, open questions, risks, verdict, next steps.

## Note on history

This package was originally started as a GitNexus-clone code-knowledge-graph MCP server (Phase 0 attempted tree-sitter + SQLite + MCP). That direction was wrong and got discarded. See [`../00-spec/PLAN.md` §13 (if added)](../00-spec/PLAN.md) and the git log (when committed) for the prior trajectory.

The current `canopy` package — a Python treedocs clone — is the correct scope. Everything in `docs/01-research/` is the upstream-treedocs comparison only; the tree-sitter/SQLite/MCP research was deleted along with the discarded code.