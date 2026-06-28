"""YAML I/O for canopy.

Reads and writes the treedocs schema (same as upstream). The on-disk YAML
is byte-compatible with DandyLyons/treedocs — `canopy` can read files
produced by the Swift tool and vice versa.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from canopy.excludes import DEFAULT_YAML_NAME

# Match upstream schema URL so editor auto-complete / validation works.
SCHEMA_URL = "https://dandylyons.github.io/treedocs/schemas/0.2.0/treedocs.schema.json"


def _empty() -> dict:
    return {"tree": {"_kind": "dir", "_description": ""}, "signature": ""}


def load_yaml(path: Path) -> dict:
    """Load canopy.yaml from disk. Returns the empty skeleton if missing."""
    if not path.exists():
        return _empty()
    loaded = yaml.safe_load(path.read_text()) or {}
    # Tolerate partial files — fall back to empty skeleton if "tree" key missing.
    if "tree" not in loaded or not isinstance(loaded.get("tree"), dict):
        return _empty()
    return loaded


def save_yaml(path: Path, data: dict) -> None:
    """Write canopy.yaml atomically with a managed header.

    Per upstream, YAML comments are dropped on save (we don't roundtrip
    them). The header advertises the schema URL for editor support and
    marks the file as managed.
    """
    header = (
        f"# yaml-language-server: $schema={SCHEMA_URL}\n"
        f"# managed by canopy — do not hand-edit\n"
        f"# last_synced: {datetime.now(timezone.utc).isoformat()}\n"
    )
    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, width=120)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(header + body)
    tmp.replace(path)


def init_yaml(root: Path, yaml_path: Path | None = None) -> Path:
    """Create an empty canopy.yaml in `root` if one doesn't exist.

    Returns the path to the YAML file (existing or new).
    """
    if yaml_path is None:
        yaml_path = root / DEFAULT_YAML_NAME
    if not yaml_path.exists():
        save_yaml(yaml_path, _empty())
    return yaml_path