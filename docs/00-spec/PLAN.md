# canopy — MIT-licensed Python treedocs clone

**Status:** Phase 0 (vertical slice complete, GREEN, verified end-to-end)
**License:** MIT
**Target:** `pip install -e .`, then `canopy init/fill/check/show/explore/update`

---

## 1. What this is

A CLI tool that maintains a YAML map of a repository's file tree with one short human/LLM-written description per path, with SHA256-based drift detection and a `--check` mode for CI. The on-disk YAML is byte-compatible with [DandyLyons/treedocs](https://github.com/DandyLyons/treedocs) (same schema URL, same key names).

## 2. Why

The upstream `treedocs` tool ships as a Swift CLI bundled inside an Xcode package (~12 GB). That blocks adoption on non-Apple toolchains and on sandboxed macOS installs. `canopy` is a clean Python 3.10+ reimplementation with a single PyYAML dependency — no Xcode, no Swift toolchain.

There is already a single-file `~/.hermes/scripts/canopy.py` (~540 lines) that does the same thing for personal use. This package is the "proper package" version of that script: installable, testable, multi-module, and ready to publish.

## 3. Repo layout

```
canopy/
├── README.md
├── LICENSE                       # MIT
├── pyproject.toml                # name=canopy, deps=pyyaml only
├── scripts/
│   └── pre-commit                # gitleaks secret scan
├── .github/
│   └── workflows/secrets.yml     # CI secret scan
├── canopy/
│   ├── __init__.py               # __version__
│   ├── __main__.py               # python -m canopy → cli.main
│   ├── cli.py                    # argparse, subcommand dispatch
│   ├── excludes.py               # STANDARD_EXCLUDES frozenset
│   ├── scanner.py                # filesystem walk + .gitignore + signature
│   ├── yaml_io.py                # load/save/init for canopy.yaml
│   └── missing.py                # missing-description detection
├── tests/
│   └── test_phase0.py            # 17 tests covering scanner/yaml/missing
└── docs/
    ├── 00-spec/PLAN.md           # this file
    ├── 01-research/              # upstream comparison
    ├── 02-decisions/             # ADRs
    ├── 03-retros/                # post-phase retrospectives
    └── 04-changelog/             # shipped-milestone snapshots
```

**Code line count: ~480 lines** (excluding tests/docs). Well under the implicit ~2000-line budget.

## 4. CLI surface

```sh
canopy init                              # create empty canopy.yaml if missing
canopy fill [--batch 50] [--dry-run]     # LLM-fill missing descriptions (Phase 1)
canopy check                             # exit 1 on drift or missing desc
canopy show [--depth N]                  # print tree with descriptions
canopy explore                           # one-line-per-path, agent-friendly
canopy update PATH DESC                  # set one description
```

All commands accept `--root PATH` (default cwd) and `--yaml PATH` (default `canopy.yaml`).

## 5. On-disk format

Single YAML file (default `canopy.yaml`) with the [upstream treedocs schema 0.2.0](https://dandylyons.github.io/treedocs/schemas/0.2.0/treedocs.schema.json). Example:

```yaml
# yaml-language-server: $schema=https://dandylyons.github.io/treedocs/schemas/0.2.0/treedocs.schema.json
# managed by canopy — do not hand-edit
# last_synced: 2026-06-28T05:30:10+00:00
tree:
  _kind: dir
  _description: ''
  src:
    _kind: dir
    _description: source code
    main.py:
      _kind: file
      _description: CLI entry point
signature: sha256:13caeb4d8622f0f1
```

## 6. Drift detection

`canopy check` recomputes the SHA256 over the sorted, newline-joined list of paths found on disk and compares against the `signature:` field in the YAML. Per upstream behavior, **descriptions are intentionally NOT part of the signature** — only structural changes (new/moved/deleted paths) trigger drift.

`check` also fails when:
- new paths exist on disk but are missing from the YAML
- paths are listed in the YAML but no longer exist on disk
- entries have no `_description`

Returns exit 0 on success, 1 on any problem, 2 if the YAML is missing.

## 7. Build order

| Phase | Deliverable | Status |
|---|---|---|
| **0** | Scan + YAML I/O + missing-desc + drift — fully tested, CLI working | 🟢 GREEN |
| 1 | `fill` subcommand wired to bws + MiniMax (LLM-fill loop), reuse pattern from `~/.hermes/scripts/canopy.py` | pending |
| 2 | `--retain-hindsight` flag (optional Hindsight logging) | pending |
| 3 | GitHub repo `jb-bz/canopy`, publish to PyPI if scope justifies it | pending |

## 8. Open questions

- **Fill batching.** How to chunk when there are 500 missing descriptions and only 200 fit in one LLM call? Default `--batch 50`; revisit based on real usage.
- **Description style guide.** Does the LLM get told "max 15 words" or do we leave it free-form? Upstream uses ~15-word cap; we'll mirror.
- **Hindsight integration.** Same bank (`coding-agent-stack`) as `~/.hermes/scripts/canopy.py`, or a new `canopy-py` bank?

## 9. Risks

- **Description conflicts.** Two users fill the same path differently → last writer wins. No locking. Acceptable for a single-user tool.
- **Gitignore scope.** We match basenames only, not full gitignore semantics (anchors, negation, `**`). Handles 95% of real repos; full spec deferred to Phase 2 if a user hits a wall.

## 10. What we explicitly are NOT building

- ❌ Code-knowledge graph / MCP server — that's a different tool (and was the wrong-direction Phase 0 we discarded)
- ❌ Symbol extraction / call graphs / PDG — none of that belongs in a YAML-doc tool
- ❌ File watcher / live reload — single `index` run is enough
- ❌ Multi-repo support — one `canopy.yaml` per repo

## 11. Dependencies (final pinned set)

```toml
dependencies = ["PyYAML>=6.0"]

[project.optional-dependencies]
dev = ["pytest"]
```

**No native build tools, no external services.** Total wheel footprint: ~150 KB.

## 12. Success criteria for Phase 0

1. ✅ `pip install -e .` works on Apple Silicon (only PyYAML + pytest).
2. ✅ `python -m canopy init && python -m canopy update PATH DESC` writes a valid YAML.
3. ✅ `python -m canopy check` returns 0 on a clean repo, 1 on drift.
4. ✅ `python -m canopy show` and `explore` render the tree.
5. ✅ LICENSE is MIT, on-disk format is compatible with upstream `treedocs`.