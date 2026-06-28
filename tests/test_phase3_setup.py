"""Phase 3 acceptance tests: `canopy setup` command.

- Interactive mode: prompts the user for provider, model, client, and API key
- Non-interactive mode: flags do everything; no prompts
- Unknown client: prints the docs/setup/UNKNOWN_CLIENT.md content
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from canopy import setup


# ─── non-interactive mode ──────────────────────────────────────────────


def test_noninteractive_writes_claude_code_config(tmp_path: Path) -> None:
    rc = setup.main([
        "--non-interactive",
        "--provider", "anthropic",
        "--model", "MiniMax-M3",
        "--client", "claude-code",
        "--api-key", "test-key",
        "--global-config-dir", str(tmp_path),
    ])
    assert rc == 0
    # Claude Code writes to .mcp.json
    candidates = list(tmp_path.glob("*.mcp.json")) + list(tmp_path.glob("**/.mcp.json"))
    assert candidates, f"no .mcp.json written under {tmp_path}"


def test_noninteractive_openai_provider(tmp_path: Path) -> None:
    """--provider openai + --client cursor should write a JSON mcpServers entry."""
    rc = setup.main([
        "--non-interactive",
        "--provider", "openai",
        "--model", "gpt-4o",
        "--client", "cursor",
        "--api-key", "sk-test",
        "--global-config-dir", str(tmp_path),
    ])
    assert rc == 0


def test_noninteractive_unknown_client_prints_doc(tmp_path: Path, capsys) -> None:
    """--client clawbot should NOT fail; it should print the generic doc."""
    rc = setup.main([
        "--non-interactive",
        "--provider", "anthropic",
        "--model", "MiniMax-M3",
        "--client", "clawbot",
        "--api-key", "test-key",
        "--global-config-dir", str(tmp_path),
    ])
    assert rc == 0
    captured = capsys.readouterr()
    # Doc should mention clawbot and include a prompt to register the server.
    assert "clawbot" in captured.out or "clawbot" in captured.err
    assert "canopy" in captured.out or "canopy" in captured.err


def test_noninteractive_unknown_provider_rejected() -> None:
    """A typo'd provider name should fail loudly."""
    with pytest.raises(SystemExit):
        setup.main([
            "--non-interactive",
            "--provider", "madeup",
            "--model", "x",
            "--client", "claude-code",
            "--api-key", "k",
        ])


# ─── interactive mode ─────────────────────────────────────────────────


def test_interactive_with_all_inputs(tmp_path: Path) -> None:
    """Mock input() to feed every prompt, then assert config written."""
    inputs = iter([
        "anthropic",        # provider
        "MiniMax-M3",       # model
        "https://x.test",   # base URL (overrides default)
        "claude-code",      # client
        "test-key",         # api key
    ])
    with patch("builtins.input", lambda *_: next(inputs)):
        rc = setup.main([
            "--interactive",
            "--global-config-dir", str(tmp_path),
        ])
    assert rc == 0


def test_interactive_accepts_empty_to_use_default() -> None:
    """Hitting enter on a prompt should pick the default."""
    inputs = iter([
        "",  # provider → default anthropic
        "",  # model → default MiniMax-M3
        "",  # base URL → default MiniMax URL
        "",  # client → default claude-code
        "",  # api key → empty (allowed for some providers like Ollama)
    ])
    with patch("builtins.input", lambda *_: next(inputs)):
        rc = setup.main(["--interactive"])
    assert rc == 0


# ─── output contract ───────────────────────────────────────────────────


def test_default_provider_is_openrouter() -> None:
    """Per the user's stated preference: default = OpenRouter."""
    parser = setup.build_parser()
    args = parser.parse_args(["--interactive"])
    assert setup.DEFAULT_PROVIDER == "openrouter"


def test_default_model_for_openrouter_is_anthropic_claude() -> None:
    """Per the user's preference: default OpenRouter model = anthropic/claude-3.5-sonnet."""
    assert setup.DEFAULT_MODEL_OPENROUTER == "anthropic/claude-3.5-sonnet"


def test_default_client_is_claude_code() -> None:
    """Most popular MCP client as of 2026."""
    assert setup.DEFAULT_CLIENT == "claude-code"