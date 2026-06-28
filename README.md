# canopy

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/canopy-banner.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/canopy-banner.svg">
    <img src="docs/assets/canopy-banner.svg" alt="canopy logo" width="600">
  </picture>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-100%20passing-brightgreen.svg)](tests/)

MIT-licensed Python clone of [DandyLyons/treedocs](https://github.com/DandyLyons/treedocs): a CLI tool that maintains a YAML map of a repository's file tree with one short human/LLM-written description per path, with SHA256 drift detection and a `--check` mode for CI.

## Why this exists

[DandyLyons/treedocs](https://github.com/DandyLyons/treedocs) is the original idea — but it ships as a Swift CLI bundled inside an Xcode package (~12 GB), which blocks adoption on non-Apple toolchains and on sandboxed macOS installs. `canopy` reimplements the same workflow in pure Python 3.10+ with a single PyYAML dependency, no Xcode required.

The on-disk YAML is byte-compatible with upstream — same schema URL, same keys. If you have an existing `treedocs.yaml` from the Swift tool, `canopy` reads and writes it without migration.

## Screenshots

### `canopy fill` against itself (dogfooding)

![canopy fill](docs/screenshots/06-fill.png)

### Before / after `canopy show` — the YAML tree with descriptions

![canopy show](docs/screenshots/03-show.png)

### `canopy explore` — compact agent-friendly view

![canopy explore](docs/screenshots/04-explore.png)

### `canopy --help` — full CLI surface

![canopy --help](docs/screenshots/01-help.png)

### `canopy check` — CI mode (exit 1 on drift)

![canopy check](docs/screenshots/05-check.png)

## Install

```sh
pip install -e ".[dev]"
canopy --help
```

## Usage

```sh
canopy init                              # create empty canopy.yaml
canopy fill [--batch 50] [--dry-run]     # LLM-fill missing descriptions
canopy check                             # exit 1 on drift or missing desc
canopy show [--depth N]                  # print the tree
canopy explore                           # agent-friendly compact tree
canopy update PATH DESC                  # set one description
```

## Environment

- `MINIMAX_API_KEY` — fetched at runtime via `bws` using `--bws-secret <UUID>` (default: `$BWS_MINIMAX_SECRET_ID` env var). Pattern: `source ~/.config/bws/env` then `export BWS_MINIMAX_SECRET_ID=<your-uuid>`.
- `HINDSIGHT_URL` — default `http://localhost:8888`
- `HINDSIGHT_BANK` — default `coding-agent-stack`

The `bws` CLI must be on `$PATH` (`brew install bws` if missing).

## License

MIT — see [`LICENSE`](LICENSE).

## Attribution

- Inspired by [DandyLyons/treedocs](https://github.com/DandyLyons/treedocs) — used under the upstream treedocs schema (CC0 / public schema reference).
- LLM fills use the same Anthropic-compatible API as `~/.hermes/scripts/canopy.py` (MiniMax via bws).