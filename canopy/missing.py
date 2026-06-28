"""Missing-description detection.

Walks the YAML tree and returns entries that have no description. Used by:
  - canopy fill  → to know what to ask the LLM about
  - canopy check → to fail CI on entries that should have been filled
"""
from __future__ import annotations


def missing_descriptions(tree: dict, prefix: str = "") -> list[tuple[str, str]]:
    """Return list of (path, kind) for entries with no description.

    Only `_kind in {"file", "dir"}` entries are considered; the synthetic
    metadata keys (`_kind`, `_description` themselves) are skipped.
    """
    out: list[tuple[str, str]] = []
    for name, node in tree.items():
        if name.startswith("_"):
            continue
        if not isinstance(node, dict):
            continue
        path = f"{prefix}/{name}" if prefix else name
        desc = (node.get("_description") or "").strip()
        kind = node.get("_kind", "dir")
        if not desc and kind in {"file", "dir"}:
            out.append((path, kind))
        if kind == "dir":
            out.extend(missing_descriptions(node, path))
    return out