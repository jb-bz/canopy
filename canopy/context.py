"""Context-file discovery for the LLM fill prompt.

`canopy fill` ships a curated set of repo docs to the LLM as context.
This module discovers those files automatically instead of forcing users
to maintain a hardcoded list in CLI flags.

Discovery rules (Phase 2, Option C — "beefy"):

  1. **Root files** — match by basename glob:
       README*, CHANGELOG*, AGENTS.md, CLAUDE.md, CONTRIBUTING*,
       package.json, pyproject.toml, Cargo.toml, go.mod, setup.py

  2. **docs/** — any *.md or *.rst at any depth under a `docs/` directory.

  3. **Module dirs** — any *.md under any of: src/, lib/, app/, internal/, pkg/

Excludes (delegated to `canopy.scanner._load_gitignore` + `STANDARD_EXCLUDES`):
  - paths matched by `.gitignore`
  - any path component in STANDARD_EXCLUDES (`node_modules`, `.git`, etc.)
  - hidden directories (except the standard allowlist)

Size caps (matched to canopy/fill.py):
  - DEFAULT_PER_FILE_CAP (3000 chars per file)
  - DEFAULT_TOTAL_CAP   (20 KB total)
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

from canopy.excludes import is_excluded
from canopy.scanner import _load_gitignore


# Basename globs for root-level files we always want to feed the LLM.
# Order is preserved when matched; alphabetical sort happens after collection.
ROOT_FILE_PATTERNS: tuple[str, ...] = (
    "README*",
    "CHANGELOG*",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING*",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "setup.py",
)

# Directory names (anywhere) where *.md and *.rst are considered context.
DOC_DIRS: frozenset[str] = frozenset({"docs"})

# Module-level dirs where *.md is considered context (deeper than DOC_DIRS).
MODULE_DOC_DIRS: frozenset[str] = frozenset({"src", "lib", "app", "internal", "pkg"})

# File extensions recognized as "docs".
DOC_EXTS: frozenset[str] = frozenset({".md", ".rst"})


# Caps mirror canopy/fill.py — kept here so tests can verify them.
DEFAULT_PER_FILE_CAP: int = 3000
DEFAULT_TOTAL_CAP: int = 20_000


_DOTDIR_ALLOWLIST: frozenset[str] = frozenset({
    ".github", ".gitlab", ".claude", ".hermes", ".canopy",
})


def _matches_root(name: str) -> bool:
    """True if `name` matches any pattern in ROOT_FILE_PATTERNS."""
    for pat in ROOT_FILE_PATTERNS:
        if fnmatch.fnmatch(name, pat):
            return True
    return False


def _should_descend(name: str) -> bool:
    """True if we should walk into a directory."""
    if name.startswith(".") and name not in _DOTDIR_ALLOWLIST:
        return False
    return True


def _is_doc_file(path: Path, *, gitignore_patterns: list[str]) -> bool:
    """True if `path` should be included as a context doc file."""
    if path.suffix.lower() not in DOC_EXTS:
        return False
    rel = path.as_posix()
    parts = tuple(rel.split("/"))
    if is_excluded(rel, parts):
        return False
    # Cheap gitignore match against basename (consistent with scanner.py).
    from canopy.scanner import _gitignore_blocks  # late import to avoid cycles
    if _gitignore_blocks(rel, path.name, gitignore_patterns):
        return False
    return True


def _walk_for_docs(
    root: Path,
    *,
    gitignore_patterns: list[str],
) -> list[Path]:
    """Walk `root` and return all files matching the doc-file rules."""
    out: list[Path] = []

    def _walk(p: Path) -> None:
        if not _should_descend(p.name):
            return
        # gitignore on the directory itself
        from canopy.scanner import _gitignore_blocks  # local
        if _gitignore_blocks(p.as_posix(), p.name, gitignore_patterns):
            return

        if p.is_file():
            # Root-level file: must match a ROOT_FILE_PATTERNS glob.
            rel = p.relative_to(root).as_posix()
            if "/" not in rel and _matches_root(p.name):
                out.append(p)
                return
            # docs/<...>/*.md or *.rst at any depth
            if rel.startswith("docs/") and p.suffix.lower() in DOC_EXTS:
                out.append(p)
                return
            # <module_dir>/<...>/*.md (one or more segments under a module dir)
            top = rel.split("/", 1)[0]
            if top in MODULE_DOC_DIRS and p.suffix.lower() in DOC_EXTS:
                out.append(p)
                return
            return

        if p.is_dir():
            try:
                children = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            except (PermissionError, OSError):
                return
            for child in children:
                _walk(child)

    _walk(root)
    return out


def discover_context(
    root: Path,
    *,
    per_file_cap: int = DEFAULT_PER_FILE_CAP,
    total_cap: int = DEFAULT_TOTAL_CAP,
) -> dict[str, str]:
    """Return {relative_path: truncated_content} for all context-worthy files.

    Sorted alphabetically by key for deterministic LLM input. Files that
    can't be read (OSError) are silently skipped.

    The total cap is a hard ceiling: once adding the next file would exceed
    `total_cap`, that file is dropped. This matches the behavior the LLM
    can tolerate — extra files don't help past a certain point.
    """
    gitignore_patterns = _load_gitignore(root)
    candidates = _walk_for_docs(root, gitignore_patterns=gitignore_patterns)
    candidates.sort(key=lambda p: p.relative_to(root).as_posix())

    result: dict[str, str] = {}
    used = 0
    for p in candidates:
        rel = p.relative_to(root).as_posix()
        try:
            content = p.read_text(errors="ignore")
        except OSError:
            continue
        truncated = content[:per_file_cap]
        if used + len(truncated) > total_cap:
            # No room for this file at full size; try a partial.
            room = total_cap - used
            if room <= 0:
                break
            truncated = truncated[:room]
        result[rel] = truncated
        used += len(truncated)
        if used >= total_cap:
            break
    return result