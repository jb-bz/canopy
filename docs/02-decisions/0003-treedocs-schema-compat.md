# ADR-0003: Byte-compatible YAML with DandyLyons/treedocs

**Status:** Accepted — 2026-06-28
**Supersedes:** —

## Context

Two possible on-disk formats:

1. **Custom format** — choose our own keys, our own schema URL. Pros: freedom to evolve. Cons: any existing `treedocs.yaml` from the upstream Swift tool won't load, and vice versa.
2. **Upstream-compatible format** — use the same schema URL (`https://dandylyons.github.io/treedocs/schemas/0.2.0/treedocs.schema.json`), same top-level keys (`tree`, `signature`), same per-entry keys (`_kind`, `_description`). Pros: zero-migration swap-in. Cons: any future canopy-specific feature has to fit in the schema.

## Decision

**Use the upstream schema 0.2.0 verbatim.** Header on every save advertises the schema URL for `yaml-language-server` editor support. Top-level keys: `tree`, `signature`. Per-entry keys: `_kind`, `_description`. No new top-level keys unless the upstream schema version bumps.

## Consequences

- ✅ `canopy.yaml` files produced by the Swift tool load cleanly in `canopy` and vice versa.
- ✅ Editor auto-complete / validation works out of the box (via the `yaml-language-server` schema directive).
- ✅ If the upstream schema bumps to 0.3.0, we follow it.
- ⚠️ Can't add canopy-only metadata. Mitigation: store canopy-specific state in a sidecar `.canopy/state.json` (gitignored) — used for cache, last-fill timestamp, etc.