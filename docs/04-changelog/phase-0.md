# Phase 0 — multi-file package skeleton + scanner + YAML I/O + drift + CLI

**Date:** 2026-06-28
**Status:** 🟢 GREEN — verified end-to-end
**Branch:** main (no commits yet — pending user review)

## What ships in this phase

- Multi-file `canopy/` Python package (7 modules, ~480 LOC)
- `pyproject.toml` with `PyYAML>=6.0` (runtime) + `pytest` (dev), `console_scripts` entry point
- 6 CLI subcommands: `init`, `fill` (stub), `check`, `show`, `explore`, `update`
- YAML output **byte-compatible** with upstream DandyLyons/treedocs (same schema URL, same keys)
- SHA256 signature-based drift detection (descriptions excluded, per upstream behavior)
- Standard excludes (`.git`, `node_modules`, `__pycache__`, …) — copied from `~/.hermes/scripts/canopy.py`
- .gitignore-aware scanner (basename matching, full gitignore semantics deferred)
- gitleaks pre-commit hook + GitHub Actions workflow
- MIT LICENSE, README, .gitignore
- Full docs structure: `00-spec/PLAN.md`, `01-research/`, `02-decisions/` (3 ADRs), `03-retros/`, `04-changelog/`

## Verification

```sh
$ cd ~/canopy
$ source .venv/bin/activate
$ pip install pyyaml pytest     # one at a time, see ADR-0001
$ PYTHONPATH=. pytest tests/ -v
============================= 17 passed in 0.06s ==============================

$ python -m canopy --version
canopy 0.0.1

$ python -m canopy --root /tmp/smoke init
wrote /tmp/smoke/canopy.yaml
$ python -m canopy --root /tmp/smoke update src/main.py "CLI entry point"
updated src/main.py
$ python -m canopy --root /tmp/smoke show
README.md  # top-level readme
src/       # source code
  main.py  # CLI entry point
$ python -m canopy --root /tmp/smoke explore
# canopy explore: 2 paths in canopy.yaml
README.md :: top-level readme
src :: source code
$ python -m canopy --root /tmp/smoke check
FAIL: signature drift (...)
$ echo $?
1

$ gitleaks detect --source .
no leaks found
```

## Known gaps (Phase 1+)

- `fill` is a stub (Phase 1)
- No `--retain-hindsight` flag (Phase 2)
- No git commit, no GitHub repo (pending user approval per "don't push" rule)

## Attribution

- Spec: [`../00-spec/PLAN.md`](../00-spec/PLAN.md)
- ADRs: [`../02-decisions/`](../02-decisions/)
- Research: [`../01-research/`](../01-research/)
- Retrospective: [`../03-retros/phase-0.md`](../03-retros/phase-0.md)