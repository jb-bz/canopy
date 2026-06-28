"""Filesystem scanner.

Walks a directory tree, respects .gitignore, applies standard excludes,
and returns a nested-dict representation compatible with the treedocs
schema (same shape as ~/.hermes/scripts/canopy.py and DandyLyons/treedocs).

Leaves are dicts with keys:
  - _kind: "file" | "dir"
  - _description: str (always present, may be empty)
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from canopy.excludes import is_excluded


# Dot-dirs that are allowed even though they start with '.'.
_DOTDIR_ALLOWLIST: frozenset[str] = frozenset({
    ".github",
    ".gitlab",
    ".claude",
    ".hermes",
    ".canopy",  # index dir (defensive — also in STANDARD_EXCLUDES)
})


def _load_gitignore(root: Path) -> list[str]:
    gi = root / ".gitignore"
    if not gi.exists():
        return []
    patterns: list[str] = []
    for line in gi.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _gitignore_blocks(rel: str, name: str, patterns: list[str]) -> bool:
    """Cheap basename + dir-name matcher.

    Full gitignore semantics (anchors, negation, **) are out of scope.
    We match: any pattern whose basename (or pattern body after stripping
    a trailing slash) appears in `name`, treated as a regex with `*`
    expanded to `.*` and `$` anchored.

    This handles the common cases:
      - `*.pyc` → blocks any `.pyc` file at any depth
      - `build/` → blocks any `build` directory
      - `secret.py` → blocks a file with that exact name
    """
    if not patterns:
        return False
    for pat in patterns:
        body = pat.rstrip("/")
        regex = "^" + body.replace(".", r"\.").replace("*", ".*") + "$"
        if re.search(regex, name):
            return True
    return False


def _walk(p: Path, rel: str, gitignore_patterns: list[str]) -> dict | None:
    parts = tuple(rel.split("/")) if rel else ()

    if is_excluded(rel, parts):
        return None

    # Suppress hidden dirs except the allowlist.
    if p.name.startswith(".") and p.name not in _DOTDIR_ALLOWLIST:
        return None

    # Cheap gitignore match against basename only (covers the common cases).
    if _gitignore_blocks(rel, p.name, gitignore_patterns):
        return None

    if p.is_file():
        return {"_kind": "file", "_description": ""}
    if p.is_dir():
        children: dict = {"_kind": "dir", "_description": ""}
        try:
            entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return children
        for child in entries:
            child_rel = f"{rel}/{child.name}" if rel else child.name
            sub = _walk(child, child_rel, gitignore_patterns)
            if sub is not None:
                children[child.name] = sub
        return children
    return None


def scan_tree(root: Path) -> dict:
    """Walk the filesystem and return a nested dict tree.

    Always returns at minimum `{"_kind": "dir", "_description": ""}`.
    """
    gitignore_patterns = _load_gitignore(root)
    walked = _walk(root, "", gitignore_patterns)
    return walked if walked is not None else {"_kind": "dir", "_description": ""}


def paths_from_tree(tree: dict, prefix: str = "") -> list[str]:
    """Flatten the tree to a sorted list of repo-relative POSIX paths."""
    out: list[str] = []
    for name, node in tree.items():
        if name.startswith("_"):
            continue
        path = f"{prefix}/{name}" if prefix else name
        out.append(path)
        if isinstance(node, dict) and node.get("_kind") == "dir":
            out.extend(paths_from_tree(node, path))
    return sorted(out)


def compute_signature(paths: list[str]) -> str:
    """SHA256 over the sorted, newline-joined paths.

    Per upstream behavior, descriptions are intentionally NOT part of the
    signature — only structural changes (new/moved/deleted paths) trigger
    drift detection.
    """
    h = hashlib.sha256()
    for p in paths:
        h.update(p.encode("utf-8"))
        h.update(b"\n")
    return f"sha256:{h.hexdigest()[:16]}"