"""Phase 0 acceptance test: scan → YAML → roundtrip → drift detection.

This is the smallest end-to-end vertical slice that proves the canopy
package works. Exercises:
  - filesystem scanning with .gitignore + standard excludes
  - YAML load/save
  - missing-description detection
  - SHA256 signature computation + drift detection

If this test passes, the v0.1 skeleton is wired correctly.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from canopy.scanner import scan_tree, paths_from_tree, compute_signature
from canopy.yaml_io import load_yaml, save_yaml, init_yaml, SCHEMA_URL
from canopy.missing import missing_descriptions
from canopy.excludes import STANDARD_EXCLUDES, is_excluded


# ─── excludes ───────────────────────────────────────────────────────────


def test_standard_excludes_blocks_node_modules():
    assert is_excluded("node_modules/foo.js", ("node_modules", "foo.js"))


def test_standard_excludes_blocks_pycache():
    assert is_excluded("src/__pycache__/x.pyc", ("src", "__pycache__", "x.pyc"))


def test_standard_excludes_allows_top_level_file():
    assert not is_excluded("README.md", ("README.md",))


def test_standard_excludes_blocks_canopy_yaml():
    """canopy.yaml is excluded so it never appears in its own scan."""
    assert is_excluded("canopy.yaml", ("canopy.yaml",))


# ─── scanner ────────────────────────────────────────────────────────────


def test_scan_tree_returns_nested_dict(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("# a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("# b")

    tree = scan_tree(tmp_path)

    assert tree["_kind"] == "dir"
    assert tree["a.py"]["_kind"] == "file"
    assert tree["sub"]["_kind"] == "dir"
    assert tree["sub"]["b.py"]["_kind"] == "file"


def test_scan_tree_skips_node_modules(tmp_path: Path) -> None:
    (tmp_path / "src.py").write_text("# keep")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("// skip")

    tree = scan_tree(tmp_path)
    paths = paths_from_tree(tree)

    assert "src.py" in paths
    assert not any("node_modules" in p for p in paths)


def test_paths_from_tree_returns_sorted_unique_paths(tmp_path: Path) -> None:
    (tmp_path / "z.py").write_text("")
    (tmp_path / "a.py").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "m.py").write_text("")

    tree = scan_tree(tmp_path)
    paths = paths_from_tree(tree)

    assert paths == sorted(paths)
    # Directories appear as paths too (every entry of the tree is a path).
    assert paths == ["a.py", "sub", "sub/m.py", "z.py"]


def test_compute_signature_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    tree = scan_tree(tmp_path)
    sig1 = compute_signature(paths_from_tree(tree))
    sig2 = compute_signature(paths_from_tree(tree))
    assert sig1 == sig2
    assert sig1.startswith("sha256:")


def test_compute_signature_changes_when_paths_change(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("")
    tree1 = scan_tree(tmp_path)
    sig1 = compute_signature(paths_from_tree(tree1))

    (tmp_path / "b.py").write_text("")
    tree2 = scan_tree(tmp_path)
    sig2 = compute_signature(paths_from_tree(tree2))

    assert sig1 != sig2


def test_compute_signature_ignores_descriptions(tmp_path: Path) -> None:
    """Per upstream behavior, descriptions are NOT part of the signature."""
    (tmp_path / "a.py").write_text("")
    tree1 = scan_tree(tmp_path)
    paths1 = paths_from_tree(tree1)
    sig1 = compute_signature(paths1)

    # Mutate the tree to add a description, signature must not change.
    tree1["a.py"]["_description"] = "added later"
    sig2 = compute_signature(paths_from_tree(tree1))

    assert sig1 == sig2


# ─── YAML ───────────────────────────────────────────────────────────────


def test_load_yaml_returns_empty_init_when_missing(tmp_path: Path) -> None:
    data = load_yaml(tmp_path / "nope.yaml")
    assert data == {"tree": {"_kind": "dir", "_description": ""}, "signature": ""}


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    ypath = tmp_path / "canopy.yaml"
    data = {
        "tree": {
            "_kind": "dir",
            "_description": "",
            "src": {
                "_kind": "dir",
                "_description": "source code",
                "main.py": {"_kind": "file", "_description": "entry point"},
            },
        },
        "signature": "sha256:abc",
    }
    save_yaml(ypath, data)
    loaded = load_yaml(ypath)
    assert loaded == data


def test_save_yaml_emits_schema_url_header(tmp_path: Path) -> None:
    ypath = tmp_path / "canopy.yaml"
    save_yaml(ypath, {"tree": {"_kind": "dir", "_description": ""}, "signature": ""})
    text = ypath.read_text()
    assert SCHEMA_URL in text


def test_init_yaml_writes_empty_skeleton(tmp_path: Path) -> None:
    ypath = tmp_path / "canopy.yaml"
    init_yaml(tmp_path, ypath)
    assert ypath.exists()
    data = load_yaml(ypath)
    assert data["tree"]["_kind"] == "dir"
    assert data["signature"] == ""


# ─── missing descriptions ───────────────────────────────────────────────


def test_missing_descriptions_returns_empty_descriptions(tmp_path: Path) -> None:
    tree = {
        "_kind": "dir",
        "_description": "",
        "src": {
            "_kind": "dir",
            "_description": "has desc",
            "main.py": {"_kind": "file", "_description": ""},  # missing
            "util.py": {"_kind": "file", "_description": "ok"},  # ok
        },
    }
    missing = missing_descriptions(tree)
    assert missing == [("src/main.py", "file")]


def test_missing_descriptions_handles_nested_dirs(tmp_path: Path) -> None:
    tree = {
        "_kind": "dir",
        "_description": "",
        "a": {
            "_kind": "dir",
            "_description": "",
            "b": {"_kind": "dir", "_description": ""},
            "leaf.py": {"_kind": "file", "_description": ""},
        },
    }
    missing = missing_descriptions(tree)
    paths = {p for p, _ in missing}
    assert "a" in paths
    assert "a/b" in paths
    assert "a/leaf.py" in paths


# ─── gitignore integration ──────────────────────────────────────────────


def test_scan_tree_respects_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored.py\nbuild/\n")
    (tmp_path / "kept.py").write_text("")
    (tmp_path / "ignored.py").write_text("")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "o.py").write_text("")

    tree = scan_tree(tmp_path)
    paths = paths_from_tree(tree)

    assert "kept.py" in paths
    assert "ignored.py" not in paths
    assert not any(p.startswith("build/") for p in paths)