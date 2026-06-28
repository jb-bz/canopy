"""Phase 2 acceptance tests: context file discovery.

Covers:
- discover_context returns a dict of {display_name: content}
- Finds root files by basename (README*, CHANGELOG*, AGENTS.md, CLAUDE.md, etc.)
- Finds docs/**/*.md and docs/**/*.rst at any depth
- Finds module-level *.md under src/, lib/, app/, internal/, pkg/
- Respects .gitignore + STANDARD_EXCLUDES (node_modules/docs/foo.md skipped)
- Honors size caps: 3000 chars per file, 20 KB total
- Deterministic ordering (sorted)
- Returns empty dict when nothing matches
- Survives unreadable files (OSError) silently
"""
from __future__ import annotations

from pathlib import Path

import pytest

from canopy.context import (
    DEFAULT_TOTAL_CAP,
    DEFAULT_PER_FILE_CAP,
    ROOT_FILE_PATTERNS,
    discover_context,
)


# ─── root-level file discovery ────────────────────────────────────────


def test_finds_readme_at_root(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# My project\nThis is the readme.")
    result = discover_context(tmp_path)
    assert "README.md" in result
    assert "My project" in result["README.md"]


def test_finds_readme_with_variant_extension(tmp_path: Path) -> None:
    (tmp_path / "README.rst").write_text("readme reST")
    (tmp_path / "README.markdown").write_text("readme markdown")
    result = discover_context(tmp_path)
    assert "README.rst" in result
    assert "README.markdown" in result


def test_finds_changelog_agents_claude_contributing(tmp_path: Path) -> None:
    for name in ("CHANGELOG.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md"):
        (tmp_path / name).write_text(f"content of {name}")
    result = discover_context(tmp_path)
    for name in ("CHANGELOG.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md"):
        assert name in result
        assert result[name] == f"content of {name}"


def test_finds_package_manifests_at_root(tmp_path: Path) -> None:
    for name in ("package.json", "pyproject.toml", "Cargo.toml", "go.mod", "setup.py"):
        (tmp_path / name).write_text(f"# {name}")
    result = discover_context(tmp_path)
    for name in ("package.json", "pyproject.toml", "Cargo.toml", "go.mod", "setup.py"):
        assert name in result


def test_ignores_random_md_at_root(tmp_path: Path) -> None:
    """A top-level NOTES.md shouldn't be picked up unless explicitly listed."""
    (tmp_path / "NOTES.md").write_text("scratch notes")
    (tmp_path / "TODO.md").write_text("todo list")
    (tmp_path / "package.json").write_text("{}")
    result = discover_context(tmp_path)
    assert "NOTES.md" not in result
    assert "TODO.md" not in result
    assert "package.json" in result


# ─── docs/ subdirectory discovery ────────────────────────────────────


def test_finds_md_under_docs_at_any_depth(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PLAN.md").write_text("plan content")
    (tmp_path / "docs" / "research").mkdir()
    (tmp_path / "docs" / "research" / "findings.md").write_text("findings")
    (tmp_path / "docs" / "research" / "sub").mkdir()
    (tmp_path / "docs" / "research" / "sub" / "deep.md").write_text("deep")

    result = discover_context(tmp_path)

    # Each file appears with a path-relative key so the LLM can disambiguate.
    assert "docs/PLAN.md" in result
    assert "docs/research/findings.md" in result
    assert "docs/research/sub/deep.md" in result


def test_finds_rst_under_docs(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.rst").write_text("reST guide")
    result = discover_context(tmp_path)
    assert "docs/guide.rst" in result


def test_finds_md_under_other_doc_dirs(tmp_path: Path) -> None:
    """Non-'docs' names like 'documentation/' or 'wiki/' should NOT be picked up.

    The discovery rule is strictly `docs/`. If users want other dirs, they
    rename or symlink. Avoids accidentally slurping 50 MB of vendor docs.
    """
    (tmp_path / "documentation").mkdir()
    (tmp_path / "documentation" / "main.md").write_text("doc")
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "home.md").write_text("wiki")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "main.md").write_text("ok")
    result = discover_context(tmp_path)
    assert "documentation/main.md" not in result
    assert "wiki/home.md" not in result
    assert "docs/main.md" in result


# ─── module-level docs discovery ─────────────────────────────────────


@pytest.mark.parametrize("module_dir", ["src", "lib", "app", "internal", "pkg"])
def test_finds_md_under_module_dirs(tmp_path: Path, module_dir: str) -> None:
    base = tmp_path / module_dir
    base.mkdir()
    (base / "auth").mkdir()
    (base / "auth" / "README.md").write_text(f"{module_dir}/auth readme")
    (base / "billing").mkdir()
    (base / "billing" / "DESIGN.md").write_text(f"{module_dir}/billing design")

    result = discover_context(tmp_path)
    assert f"{module_dir}/auth/README.md" in result
    assert f"{module_dir}/billing/DESIGN.md" in result


def test_does_not_match_unrelated_dirs(tmp_path: Path) -> None:
    """Dirs that aren't on the allowlist (scripts/, tests/, etc.) are skipped."""
    for d in ("scripts", "tests", "examples", "build", "tools", ".github"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "NOTES.md").write_text("should not pick up")

    result = discover_context(tmp_path)
    for d in ("scripts", "tests", "examples", "build", "tools", ".github"):
        assert not any(k.startswith(f"{d}/") for k in result)


# ─── ignore rules ─────────────────────────────────────────────────────


def test_respects_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored.md\nbuild/\n")
    # `kept.md` is NOT in our ROOT_FILE_PATTERNS so it's not a context file
    # either way — use `AGENTS.md` to test that non-ignored files are picked up.
    (tmp_path / "AGENTS.md").write_text("keep me")
    (tmp_path / "ignored.md").write_text("ignore me")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "o.md").write_text("build artifact")

    result = discover_context(tmp_path)
    assert "AGENTS.md" in result
    assert "ignored.md" not in result
    assert not any(k.startswith("build/") for k in result)


def test_skips_node_modules_via_standard_excludes(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib").mkdir()
    (tmp_path / "node_modules" / "lib" / "docs").mkdir()
    (tmp_path / "node_modules" / "lib" / "docs" / "foo.md").write_text("vendor")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "real.md").write_text("real")

    result = discover_context(tmp_path)
    assert "docs/real.md" in result
    assert not any("node_modules" in k for k in result)


def test_skips_hidden_dirs(tmp_path: Path) -> None:
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "secret.md").write_text("hidden")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "workflows").mkdir()
    (tmp_path / ".github" / "workflows" / "ci.md").write_text("workflow")

    result = discover_context(tmp_path)
    assert ".hidden/secret.md" not in result
    assert ".github/workflows/ci.md" not in result


# ─── size caps ────────────────────────────────────────────────────────


def test_per_file_cap_truncates_large_files(tmp_path: Path) -> None:
    big = "x" * 10_000
    (tmp_path / "README.md").write_text(big)

    result = discover_context(tmp_path)
    assert len(result["README.md"]) == DEFAULT_PER_FILE_CAP


def test_total_cap_truncates_aggregate(tmp_path: Path) -> None:
    # Write 5 files each at the per-file cap.
    (tmp_path / "README.md").write_text("a" * DEFAULT_PER_FILE_CAP)
    (tmp_path / "CHANGELOG.md").write_text("b" * DEFAULT_PER_FILE_CAP)
    (tmp_path / "AGENTS.md").write_text("c" * DEFAULT_PER_FILE_CAP)
    (tmp_path / "CLAUDE.md").write_text("d" * DEFAULT_PER_FILE_CAP)
    (tmp_path / "CONTRIBUTING.md").write_text("e" * DEFAULT_PER_FILE_CAP)
    # Plus docs/ + module dirs push us past the total cap.
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "more.md").write_text("f" * DEFAULT_PER_FILE_CAP)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth").mkdir()
    (tmp_path / "src" / "auth" / "README.md").write_text("g" * DEFAULT_PER_FILE_CAP)

    result = discover_context(tmp_path)
    total = sum(len(v) for v in result.values())
    # After total cap, later files should be dropped (or truncated),
    # not all included at full per-file size.
    assert total <= DEFAULT_TOTAL_CAP


# ─── ordering & edge cases ────────────────────────────────────────────


def test_returned_dict_is_iterable_in_deterministic_order(tmp_path: Path) -> None:
    """Sorted order means the LLM sees the same context every run."""
    (tmp_path / "ZED.md").write_text("z")
    (tmp_path / "ALPHA.md").write_text("a")
    (tmp_path / "MIDDLE.md").write_text("m")

    r1 = discover_context(tmp_path)
    r2 = discover_context(tmp_path)
    assert list(r1.keys()) == list(r2.keys())
    # Sorted alphabetically.
    keys = list(r1.keys())
    assert keys == sorted(keys)


def test_returns_empty_dict_when_no_matches(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hi')")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): pass")
    result = discover_context(tmp_path)
    assert result == {}


def test_survives_unreadable_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If a file raises OSError, skip it silently rather than crash."""
    (tmp_path / "README.md").write_text("ok")

    from canopy import context

    real_open = Path.open

    def selective_open(self, *args, **kwargs):
        if self.name == "README.md":
            raise OSError("permission denied")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", selective_open)

    result = discover_context(tmp_path)
    # README.md was unreadable, so it's not in the result.
    assert "README.md" not in result


def test_root_file_patterns_constant_is_nonempty() -> None:
    """Sanity check: we haven't accidentally emptied the allowlist."""
    assert len(ROOT_FILE_PATTERNS) >= 5