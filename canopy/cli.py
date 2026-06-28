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


def cmd_fill(args: argparse.Namespace) -> int:
    """Stub for now. Phase 1 wires up the LLM via bws + MiniMax.

    Phase 0 ships the deterministic pieces (scanner + YAML I/O + drift).
    Phase 1 adds the fill loop, reusing the same bws pattern from
    ~/.hermes/scripts/canopy.py.
    """
    print("canopy fill: not yet implemented (Phase 1)", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canopy",
        description=f"canopy v{__version__} — MIT treedocs clone",
    )
    p.add_argument("--root", default=".", help="repo root (default cwd)")
    p.add_argument("--yaml", default=DEFAULT_YAML_NAME, help=f"YAML path (default {DEFAULT_YAML_NAME})")
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

    s = sp.add_parser("fill", help="LLM-fill missing descriptions (Phase 1)")
    s.set_defaults(fn=cmd_fill)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())