"""Phase 3 acceptance tests: MCP client registration.

For each built-in client, the setup script writes the right config file
at the right path with the right shape. Unknown clients print the
docs/setup/UNKNOWN_CLIENT.md template instead.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from canopy.clients import (
    KNOWN_CLIENTS,
    ClientConfig,
    register_for_client,
    render_unknown_client_doc,
    resolve_client_config,
)


# ─── resolve_client_config ─────────────────────────────────────────────


def test_resolve_claude_code() -> None:
    cfg = resolve_client_config("claude-code")
    assert cfg.name == "claude-code"
    assert cfg.config_path_template.endswith(".mcp.json") or "claude" in cfg.config_path_template


def test_resolve_codex() -> None:
    cfg = resolve_client_config("codex")
    assert cfg.name == "codex"
    assert cfg.config_path_template.endswith(".toml")  # TOML config


def test_resolve_opencode() -> None:
    cfg = resolve_client_config("opencode")
    assert cfg.name == "opencode"
    assert cfg.config_path_template.endswith(".json")


def test_resolve_cline() -> None:
    cfg = resolve_client_config("cline")
    assert cfg.config_path_template.endswith(".json")


def test_resolve_continue() -> None:
    cfg = resolve_client_config("continue")
    assert cfg.config_path_template.endswith(".json")


def test_resolve_cursor() -> None:
    cfg = resolve_client_config("cursor")
    assert cfg.config_path_template.endswith(".json")


def test_resolve_windsurf() -> None:
    cfg = resolve_client_config("windsurf")
    assert cfg.config_path_template.endswith(".json")


def test_resolve_unknown_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        resolve_client_config("clawbot")


def test_all_seven_known_clients_are_registered() -> None:
    """Sanity: we support exactly these seven in v0.3.0."""
    expected = {"claude-code", "codex", "opencode", "cline", "continue", "cursor", "windsurf"}
    assert set(KNOWN_CLIENTS.keys()) == expected


# ─── register_for_client (write config file) ───────────────────────────


def test_register_for_claude_code_writes_mcp_json(tmp_path: Path) -> None:
    cfg = ClientConfig(
        name="claude-code",
        config_path_template=str(tmp_path / ".mcp.json"),
        config_format="json",
        mcp_section_key="mcpServers",
        server_command="python",
        server_args=["-m", "canopy", "serve"],
    )
    out = register_for_client(cfg, project_root=tmp_path, global_=False)
    assert out.exists()
    data = json.loads(out.read_text())
    assert "mcpServers" in data
    assert "canopy" in data["mcpServers"]
    server = data["mcpServers"]["canopy"]
    assert server["command"] == "python"
    assert server["args"] == ["-m", "canopy", "serve"]


def test_register_for_codex_writes_toml(tmp_path: Path) -> None:
    """Codex uses TOML — we render a config.toml-style block, not JSON."""
    cfg = ClientConfig(
        name="codex",
        config_path_template=str(tmp_path / "config.toml"),
        config_format="toml",
        mcp_section_key="mcp_servers.canopy",
        server_command="python -m canopy serve",
        server_args=[],
    )
    out = register_for_client(cfg, project_root=tmp_path, global_=False)
    text = out.read_text()
    assert "[mcp_servers.canopy]" in text or "[mcp_servers]" in text
    assert "python" in text
    assert "canopy" in text
    assert "serve" in text


def test_register_appends_to_existing_json(tmp_path: Path) -> None:
    """If the config already exists, append a new server without clobbering."""
    cfg = ClientConfig(
        name="claude-code",
        config_path_template=str(tmp_path / ".mcp.json"),
        config_format="json",
        mcp_section_key="mcpServers",
        server_command="python -m canopy serve",
        server_args=[],
    )
    # Pre-existing config with another server.
    existing = {"mcpServers": {"other": {"command": "echo", "args": ["hi"]}}}
    (tmp_path / ".mcp.json").write_text(json.dumps(existing))

    out = register_for_client(cfg, project_root=tmp_path, global_=False)
    data = json.loads(out.read_text())
    assert "other" in data["mcpServers"]
    assert "canopy" in data["mcpServers"]


def test_register_overwrites_existing_canopy_entry(tmp_path: Path) -> None:
    """Re-running setup should update, not duplicate, the canopy entry."""
    cfg = ClientConfig(
        name="claude-code",
        config_path_template=str(tmp_path / ".mcp.json"),
        config_format="json",
        mcp_section_key="mcpServers",
        server_command="python",
        server_args=["-m", "canopy", "serve"],
    )
    existing = {"mcpServers": {"canopy": {"command": "old", "args": []}}}
    (tmp_path / ".mcp.json").write_text(json.dumps(existing))

    out = register_for_client(cfg, project_root=tmp_path, global_=False)
    data = json.loads(out.read_text())
    assert data["mcpServers"]["canopy"]["command"] == "python"


# ─── unknown client doc ───────────────────────────────────────────────


def test_render_unknown_client_doc_returns_markdown() -> None:
    doc = render_unknown_client_doc(client_name="clawbot", server_command="python -m canopy serve")
    assert "#" in doc  # markdown heading
    assert "clawbot" in doc
    assert "python -m canopy serve" in doc
    assert "MCP" in doc.upper()


def test_unknown_client_doc_contains_installer_prompt() -> None:
    """The doc must contain something an agent can execute to wire canopy."""
    doc = render_unknown_client_doc(client_name="clawbot", server_command="python -m canopy serve")
    # Should contain a copy-pasteable prompt for the agent.
    assert "register" in doc.lower() or "configure" in doc.lower() or "install" in doc.lower()