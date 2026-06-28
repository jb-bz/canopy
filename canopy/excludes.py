"""Standard path excludes for canopy.

Borrowed from ~/.hermes/scripts/canopy.py so behavior matches the existing
drop-in tool. Adding a new exclude here is a breaking change for any repo
that previously expected those files to be scanned.
"""
from __future__ import annotations

DEFAULT_YAML_NAME = "canopy.yaml"

# Directories / files to skip at any depth. canopy.yaml is excluded so the
# doc file never appears in its own scan output.
STANDARD_EXCLUDES: frozenset[str] = frozenset({
    ".git",
    ".build",
    ".swiftpm",
    ".treedocs",
    ".agents",
    ".opencode",
    ".canopy",  # our own index/db directory (gitignored anyway)
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
    ".gradle",
    ".idea",
    ".vscode",
    ".DS_Store",
    DEFAULT_YAML_NAME,
})


def is_excluded(rel: str, parts: tuple[str, ...]) -> bool:
    """True if any path component is in STANDARD_EXCLUDES."""
    return any(p in STANDARD_EXCLUDES for p in parts)