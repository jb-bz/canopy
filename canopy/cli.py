"""canopy CLI entry point.

Subcommands: init, fill, check, show, explore, update.

Matches the surface of ~/.hermes/scripts/canopy.py so behavior is identical
for users migrating from the drop-in script. All output goes to stdout;
diagnostics go to stderr.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from canopy import __version__
from canopy.excludes import DEFAULT_YAML_NAME
from canopy.missing import missing_descriptions
from canopy.scanner import compute_signature, paths_from_tree, scan_tree
from canopy.yaml_io import init_yaml, load_yaml, save_yaml


def _yaml_path(args: argparse.Namespace) -> Path:
    """Resolve the YAML path from --yaml (or the default)."""
    name = getattr(args, "yaml", None) or DEFAULT_YAML_NAME
    return Path(args.root) / name


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"error: {root} does not exist", file=sys.stderr)
        return 2
    ypath = init_yaml(root, _yaml_path(args))
    print(f"wrote {ypath}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Exit 1 on drift or missing description. CI-friendly."""
    root = Path(args.root).resolve()
    ypath = _yaml_path(args)
    if not ypath.exists():
        print(f"missing: {ypath}", file=sys.stderr)
        return 2
    data = load_yaml(ypath)
    tree = data.get("tree", {})
    stored_sig = data.get("signature", "")

    scanned = scan_tree(root)
    scanned_paths = paths_from_tree(scanned)
    current_sig = compute_signature(scanned_paths)
    stored_paths = set(paths_from_tree(tree))
    current_paths = set(scanned_paths)
    missing = current_paths - stored_paths
    extra = stored_paths - current_paths
    no_desc = missing_descriptions(tree)

    problems: list[str] = []
    if stored_sig and stored_sig != current_sig:
        problems.append(f"signature drift (stored={stored_sig} current={current_sig})")
    if missing:
        problems.append(f"{len(missing)} new paths not in YAML")
    if extra:
        problems.append(f"{len(extra)} paths in YAML no longer on disk")
    if no_desc:
        problems.append(f"{len(no_desc)} entries missing descriptions")

    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        return 1
    print(f"OK: {len(current_paths)} paths, signature {current_sig}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    ypath = _yaml_path(args)
    if not ypath.exists():
        print(f"missing: {ypath}", file=sys.stderr)
        return 2
    tree = load_yaml(ypath).get("tree", {})

    def _print(node: dict, prefix: str, depth: int) -> None:
        if args.depth is not None and depth > args.depth:
            return
        for name, child in sorted(node.items()):
            if name.startswith("_") or not isinstance(child, dict):
                continue
            desc = child.get("_description", "")
            line = f"{prefix}{name}{('/' if child.get('_kind') == 'dir' else '')}"
            if desc:
                line += f"  # {desc}"
            print(line)
            if child.get("_kind") == "dir":
                _print(child, prefix + "  ", depth + 1)

    _print(tree, "", 0)
    return 0


def cmd_explore(args: argparse.Namespace) -> int:
    """Compact one-line-per-entry view optimized for agent context."""
    ypath = _yaml_path(args)
    if not ypath.exists():
        print(f"missing: {ypath}", file=sys.stderr)
        return 2
    tree = load_yaml(ypath).get("tree", {})
    lines: list[str] = []

    def _walk(node: dict, prefix: str) -> None:
        for name, child in sorted(node.items()):
            if name.startswith("_") or not isinstance(child, dict):
                continue
            path = f"{prefix}/{name}" if prefix else name
            desc = (child.get("_description") or "").strip() or "(no description)"
            lines.append(f"{path} :: {desc}")
            if child.get("_kind") == "dir":
                _walk(child, path)

    _walk(tree, "")
    print(f"# canopy explore: {len(lines)} paths in {ypath.name}")
    print("\n".join(lines))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    ypath = _yaml_path(args)
    if not ypath.exists():
        print(f"missing: {ypath} — run `init` first", file=sys.stderr)
        return 2
    data = load_yaml(ypath)
    tree = data.get("tree", {})
    parts = args.path.split("/")
    node = tree
    for part in parts[:-1]:
        if part not in node or not isinstance(node[part], dict):
            print(f"creating parent dir: {part}", file=sys.stderr)
            node[part] = {"_kind": "dir", "_description": ""}
        node = node[part]
    leaf_kind = "file"
    if parts[-1] in node and isinstance(node[parts[-1]], dict):
        leaf_kind = node[parts[-1]].get("_kind", "file")
    node[parts[-1]] = {"_kind": leaf_kind, "_description": args.desc}
    data["tree"] = tree
    data["signature"] = compute_signature(paths_from_tree(tree))
    save_yaml(ypath, data)
    print(f"updated {args.path}")
    return 0


# ─── defaults (re-used by `fill` and exposed as CLI flags) ────────────

import os

DEFAULT_MINIMAX_BASE = "https://api.minimax.io/anthropic"
DEFAULT_MINIMAX_MODEL = "MiniMax-M3"
# Default bws secret UUID. Operators can override via the BWS_MINIMAX_SECRET_ID
# env var (matches ~/.hermes/scripts/canopy.py line 57). We do NOT hardcode the
# UUID here so the published package is decoupled from any single bws project —
# users set their own UUID per repo or environment.
DEFAULT_BWS_SECRET_ID = os.environ.get("BWS_MINIMAX_SECRET_ID", "")
DEFAULT_HINDSIGHT_URL = "http://localhost:8888"
DEFAULT_HINDSIGHT_BANK = "coding-agent-stack"
DEFAULT_BATCH = 50
DEFAULT_MAX_DESC_WORDS = 15


def cmd_fill(args: argparse.Namespace) -> int:
    """LLM-fill missing descriptions via bws + MiniMax.

    Phase 1. Copies the fill orchestration pattern from
    `~/.hermes/scripts/canopy.py` lines 200-330, with `--dry-run`,
    `--retain-hindsight`, `--batch`, `--max-words`, `--bws-secret`,
    `--base-url`, `--model`, `--hindsight-url`, `--hindsight-bank` flags.
    """
    # Imports done at call time so that tests can `patch("canopy.fill.X")`
    # without triggering an attribute lookup on the cli module before fill
    # has been imported.
    from canopy import bws as _bws
    from canopy import fill as _fill
    from canopy import hindsight as _hindsight
    from canopy.missing import missing_descriptions as _missing_desc
    from canopy.scanner import compute_signature, paths_from_tree, scan_tree
    from canopy.yaml_io import load_yaml, save_yaml

    root = Path(args.root).resolve()
    ypath = _yaml_path(args)
    if not ypath.exists():
        print(f"no {ypath} — run `init` first", file=sys.stderr)
        return 2

    data = load_yaml(ypath)
    tree = data.get("tree", {})

    # Detect drift before filling (paths may have changed since last sync).
    scanned = scan_tree(root)
    scanned_paths = set(paths_from_tree(scanned))
    stored_paths = set(paths_from_tree(tree))
    missing_paths = scanned_paths - stored_paths
    extra_paths = stored_paths - scanned_paths

    missing_desc = _missing_desc(tree)
    if not missing_desc and not missing_paths:
        print("nothing to fill — all descriptions present and no structural drift")
        return 0

    print(f"missing descriptions: {len(missing_desc)}")
    print(f"new paths (will be added): {len(missing_paths)}")
    if extra_paths:
        print(f"removed paths (will be pruned): {len(extra_paths)}")

    # Build context from README, AGENTS.md, package manifest.
    ctx_files: dict[str, str] = {}
    for candidate in ("README.md", "AGENTS.md", "CLAUDE.md", "package.json", "pyproject.toml"):
        p = root / candidate
        if p.exists():
            try:
                ctx_files[candidate] = p.read_text(errors="ignore")
            except OSError:
                pass

    if args.dry_run:
        print("(dry-run) would call LLM and rewrite YAML")
        return 0

    try:
        filled = _fill.fill_missing(
            missing_desc,
            ctx_files,
            base_url=args.base_url,
            model=args.model,
            secret_id=args.bws_secret,
            max_words=args.max_words,
            batch_size=args.batch,
        )
    except (_bws.BwsError, _fill.llm.LlmError) as e:
        print(f"fill failed: {e}", file=sys.stderr)
        return 3

    # Apply fills into the tree.
    for path, desc in filled.items():
        parts = path.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {"_kind": "dir", "_description": ""})
        node[parts[-1]] = {"_kind": "file", "_description": desc}

    # Add new structural paths (empty desc — to be filled next pass).
    for path in sorted(missing_paths):
        parts = path.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {"_kind": "dir", "_description": ""})
        if parts[-1] not in node:
            node[parts[-1]] = {"_kind": "file", "_description": ""}

    # Recompute signature over merged tree.
    merged_paths = paths_from_tree(tree)
    data["tree"] = tree
    data["signature"] = compute_signature(merged_paths)
    save_yaml(ypath, data)

    print(f"filled {len(filled)} descriptions")

    if args.retain_hindsight:
        facts = [
            f"canopy fill: filled {len(filled)} descriptions for {root.name}",
            f"signature: {data['signature']}",
        ]
        ok = _hindsight.retain(facts, args.hindsight_url, args.hindsight_bank)
        print(f"hindsight retain: {'ok' if ok else 'failed (silent)'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canopy",
        description=f"canopy v{__version__} — MIT treedocs clone",
    )
    p.add_argument("--root", default=".", help="repo root (default cwd)")
    p.add_argument("--yaml", default=DEFAULT_YAML_NAME, help=f"YAML path (default {DEFAULT_YAML_NAME})")
    p.add_argument("--base-url", default=DEFAULT_MINIMAX_BASE, help="MiniMax API base URL")
    p.add_argument("--model", default=DEFAULT_MINIMAX_MODEL, help="MiniMax model name")
    p.add_argument("--bws-secret", default=DEFAULT_BWS_SECRET_ID, help="bws secret UUID for the MiniMax API key")
    p.add_argument("--hindsight-url", default=DEFAULT_HINDSIGHT_URL, help="Hindsight server URL (for --retain-hindsight)")
    p.add_argument("--hindsight-bank", default=DEFAULT_HINDSIGHT_BANK, help="Hindsight bank name (for --retain-hindsight)")
    p.add_argument("--version", action="version", version=f"canopy {__version__}")
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("init", help="create empty canopy.yaml if missing")
    s.set_defaults(fn=cmd_init)

    s = sp.add_parser("check", help="exit 1 on drift or missing description (CI-friendly)")
    s.set_defaults(fn=cmd_check)

    s = sp.add_parser("show", help="print the tree with descriptions")
    s.add_argument("--depth", type=int, default=None, help="max depth to print")
    s.set_defaults(fn=cmd_show)

    s = sp.add_parser("explore", help="compact one-line-per-path view (agent-friendly)")
    s.set_defaults(fn=cmd_explore)

    s = sp.add_parser("update", help="set one description")
    s.add_argument("path", help="repo-relative path (e.g. src/main.py)")
    s.add_argument("desc", help="description text")
    s.set_defaults(fn=cmd_update)

    s = sp.add_parser("fill", help="LLM-fill missing descriptions via bws + MiniMax")
    s.add_argument("--batch", type=int, default=DEFAULT_BATCH, help=f"paths per LLM call (default {DEFAULT_BATCH})")
    s.add_argument("--max-words", type=int, default=DEFAULT_MAX_DESC_WORDS, help=f"max words per description (default {DEFAULT_MAX_DESC_WORDS})")
    s.add_argument("--dry-run", action="store_true", help="print what would change; don't write the YAML or call the LLM")
    s.add_argument("--retain-hindsight", action="store_true", help="log fill results to Hindsight (silent on failure)")
    s.set_defaults(fn=cmd_fill)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())