# STATUS NOTE — jb-bz, 2026-06-28

## What happened

You caught a real scope drift on 2026-06-27 — I was building a GitNexus-clone code-knowledge-graph MCP server under the `canopy/` folder name, but `canopy.py` was already your tool for the YAML-based repo-orientation layer. The whole GitNexus-clone direction was wrong.

**You said "pivot to a treedocs clone."** That's what this status note is about.

## ✅ Done in this session

Pivoted `~/canopy/` from GitNexus-clone to MIT-licensed Python treedocs-clone. New shape:

- **Code (~480 LOC across 7 modules):**
  - `canopy/excludes.py` — STANDARD_EXCLUDES + is_excluded
  - `canopy/scanner.py` — filesystem walk + .gitignore + SHA256 signature
  - `canopy/yaml_io.py` — load/save/init (byte-compatible with upstream treedocs schema)
  - `canopy/missing.py` — missing-description detection
  - `canopy/cli.py` — argparse + 6 subcommands (init, fill-stub, check, show, explore, update)
  - `canopy/__main__.py` — `python -m canopy` entry
  - `canopy/__init__.py` — `__version__`
- **Tests:** 17 passing tests in `tests/test_phase0.py` (scanner, YAML I/O, missing-desc, drift)
- **`pyproject.toml`:** single runtime dep `PyYAML>=6.0`, dev dep `pytest`, console script `canopy`
- **YAML format:** byte-compatible with DandyLyons/treedocs (same schema URL `https://dandylyons.github.io/treedocs/schemas/0.2.0/treedocs.schema.json`, same top-level keys `tree` + `signature`, same per-entry keys `_kind` + `_description`)
- **Docs rewritten:** `00-spec/PLAN.md` (treedocs spec), `01-research/01-upstream-treedocs.md` (replaces all the GitNexus research), `02-decisions/` (3 new ADRs: pyyaml-only, multi-file-package, schema-compat), `03-retros/phase-0.md`, `04-changelog/phase-0.md`
- **gitleaks:** clean

## ⚠️ Deleted (correctly)

The entire GitNexus-clone trajectory: tree-sitter/SQLite/MCP research reports, all four GitNexus-shaped ADRs, the `canopy/parsers/` + `canopy/graph/` + `canopy/resolve/` + `canopy/tools/` modules, the old `phase-0.md` retro/changelog. Also uninstalled `tree-sitter` and `tree-sitter-python` from the venv so the test environment matches the new spec exactly.

## 🟢 Phase 0 status: GREEN

```
$ PYTHONPATH=. pytest tests/ -v
============================= 17 passed in 0.06s ==============================
```

End-to-end CLI smoke test (init → update → show → explore → check) works as expected. `show` and `explore` correctly reflect only what's in the YAML.

## ⚠️ Still pending your call

1. **No git commit yet.** Per your "don't push" instruction.
2. **No GitHub repo.** Per your "don't push to github yet" instruction.
3. **No `fill` subcommand yet** — stub returns 1, "not yet implemented (Phase 1)". Phase 1 will copy the bws + LLM helper from `~/.hermes/scripts/canopy.py` lines 200-330 into `canopy/fill.py` and wire it through `cli.py`.

## What's next (Phase 1)

1. Implement `canopy/fill.py`: bws + MiniMax LLM loop, batch=50 default, dry-run support.
2. Add tests with a mocked LLM endpoint.
3. Add `--retain-hindsight` flag (Phase 2 stretch).
4. git commit + GitHub repo creation (when you say go).

**No keys are written anywhere except `~/.config/bws/env` which already existed.**

— Hermes