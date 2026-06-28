"""MCP client registration for canopy.

`canopy setup` registers canopy as an MCP server for one or more
agent clients. Each client has its own config file path and shape.
This module knows about the seven popular clients; anything else
prints a generic doc that the user can paste to their agent.

The 7 supported clients (v0.3.0):
  - claude-code : Claude Code  → ~/.mcp.json (JSON)
  - codex       : OpenAI Codex → ~/.codex/config.toml (TOML)
  - opencode    : OpenCode     → ~/.config/opencode/config.json (JSON)
  - cline       : Cline        → ~/.config/Code/User/globalStorage/.../mcp.json (JSON)
  - continue    : Continue.dev → ~/.continue/config.json (JSON)
  - cursor      : Cursor       → ~/.cursor/mcp.json (JSON)
  - windsurf    : Windsurf     → ~/.codeium/windsurf/mcp_config.json (JSON)

Anything else: `render_unknown_client_doc()` returns a markdown doc
that explains how to wire canopy into any MCP-aware agent.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


ConfigFormat = Literal["json", "toml"]


@dataclass(frozen=True)
class ClientConfig:
    """Description of how to register canopy with one MCP client."""

    name: str
    """Stable identifier, e.g. 'claude-code'."""

    config_path_template: str
    """Where the config file lives, with {home} as a placeholder for $HOME."""

    config_format: ConfigFormat
    """'json' or 'toml'. Determines renderer."""

    mcp_section_key: str
    """For JSON: key under which mcpServers live. For TOML: the [section] path."""

    server_command: str
    """The command to run (e.g. 'python -m canopy serve'). Stored as-is."""

    server_args: list[str]
    """Additional args (most clients want ['-m', 'canopy', 'serve'])."""


def _expand(path: str) -> Path:
    """Expand {home} → $HOME and the user (~)."""
    expanded = path.replace("{home}", os.path.expanduser("~"))
    return Path(expanded).expanduser()


# The server command shared across all clients.
_SERVER_CMD = "python"
_SERVER_ARGS = ["-m", "canopy", "serve"]


KNOWN_CLIENTS: dict[str, ClientConfig] = {
    "claude-code": ClientConfig(
        name="claude-code",
        config_path_template="{home}/.mcp.json",
        config_format="json",
        mcp_section_key="mcpServers",
        server_command=_SERVER_CMD,
        server_args=list(_SERVER_ARGS),
    ),
    "codex": ClientConfig(
        name="codex",
        config_path_template="{home}/.codex/config.toml",
        config_format="toml",
        mcp_section_key="mcp_servers.canopy",
        server_command=_SERVER_CMD,
        server_args=list(_SERVER_ARGS),
    ),
    "opencode": ClientConfig(
        name="opencode",
        config_path_template="{home}/.config/opencode/config.json",
        config_format="json",
        mcp_section_key="mcp",
        server_command=_SERVER_CMD,
        server_args=list(_SERVER_ARGS),
    ),
    "cline": ClientConfig(
        name="cline",
        config_path_template="{home}/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
        if os.uname().sysname == "Darwin"
        else "{home}/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json",
        config_format="json",
        mcp_section_key="mcpServers",
        server_command=_SERVER_CMD,
        server_args=list(_SERVER_ARGS),
    ),
    "continue": ClientConfig(
        name="continue",
        config_path_template="{home}/.continue/config.json",
        config_format="json",
        mcp_section_key="experimental.modelContextProtocolServers",
        server_command=_SERVER_CMD,
        server_args=list(_SERVER_ARGS),
    ),
    "cursor": ClientConfig(
        name="cursor",
        config_path_template="{home}/.cursor/mcp.json",
        config_format="json",
        mcp_section_key="mcpServers",
        server_command=_SERVER_CMD,
        server_args=list(_SERVER_ARGS),
    ),
    "windsurf": ClientConfig(
        name="windsurf",
        config_path_template="{home}/.codeium/windsurf/mcp_config.json",
        config_format="json",
        mcp_section_key="mcpServers",
        server_command=_SERVER_CMD,
        server_args=list(_SERVER_ARGS),
    ),
}


def resolve_client_config(name: str) -> ClientConfig:
    """Look up a client by name. Raises KeyError for unknown clients."""
    try:
        return KNOWN_CLIENTS[name]
    except KeyError:
        raise KeyError(
            f"unknown client: {name!r}; "
            f"known: {sorted(KNOWN_CLIENTS)}; "
            f"for unknown clients, call render_unknown_client_doc({name!r})"
        ) from None


# ─── config-file rendering ─────────────────────────────────────────────


def _render_json_config(cfg: ClientConfig) -> str:
    """Render the JSON config file from scratch (will be merged with existing)."""
    server_entry = {"command": cfg.server_command, "args": list(cfg.server_args)}
    return json.dumps({cfg.mcp_section_key: {"canopy": server_entry}}, indent=2)


def _render_toml_config(cfg: ClientConfig) -> str:
    """Render the TOML config snippet for Codex-style configs."""
    # We emit the canopy-specific block. Caller merges with existing TOML
    # (text-merge because we don't want to pull in a toml lib).
    cmd = cfg.server_command
    args_str = ", ".join(f'"{a}"' for a in cfg.server_args)
    lines = [
        f"[mcp_servers.canopy]",
        f'command = "{cmd}"',
        f"args = [{args_str}]",
    ]
    return "\n".join(lines) + "\n"


def register_for_client(
    cfg: ClientConfig,
    *,
    project_root: Path,
    global_: bool = False,
) -> Path:
    """Write the canopy MCP server entry to the client's config file.

    Returns the path that was written. Creates parent dirs if needed.
    Merges with existing config (does not clobber other entries).
    """
    out = _expand(cfg.config_path_template)
    out.parent.mkdir(parents=True, exist_ok=True)

    server_entry = {"command": cfg.server_command, "args": list(cfg.server_args)}

    if cfg.config_format == "json":
        existing: dict = {}
        if out.exists():
            try:
                existing = json.loads(out.read_text()) or {}
            except json.JSONDecodeError:
                existing = {}
        section = existing.setdefault(cfg.mcp_section_key, {})
        section["canopy"] = server_entry
        out.write_text(json.dumps(existing, indent=2) + "\n")
        return out

    if cfg.config_format == "toml":
        snippet = _render_toml_config(cfg)
        existing_text = out.read_text() if out.exists() else ""
        out.write_text(_merge_toml(existing_text, snippet))
        return out

    raise ValueError(f"unsupported config_format: {cfg.config_format!r}")


def _merge_toml(existing: str, snippet: str) -> str:
    """Replace the [mcp_servers.canopy] section in `existing` with `snippet`.

    Crude but works for the single-section case we care about.
    """
    pattern = re.compile(
        r"\[mcp_servers\.canopy\][^\[]*",
        re.MULTILINE | re.DOTALL,
    )
    if pattern.search(existing):
        return pattern.sub(snippet, existing)
    # No existing section — append.
    sep = "" if existing.endswith("\n") or not existing else "\n"
    return existing + sep + "\n" + snippet


# ─── unknown-client doc ───────────────────────────────────────────────


UNKNOWN_CLIENT_DOC_PATH = Path(__file__).parent.parent / "docs" / "setup" / "UNKNOWN_CLIENT.md"


def render_unknown_client_doc(*, client_name: str, server_command: str = "python -m canopy serve") -> str:
    """Render the markdown doc that explains how to wire canopy into any MCP-aware agent.

    The doc is a static template — fetched from docs/setup/UNKNOWN_CLIENT.md
    if it exists, otherwise generated on the fly.
    """
    if UNKNOWN_CLIENT_DOC_PATH.exists():
        template = UNKNOWN_CLIENT_DOC_PATH.read_text()
    else:
        template = _FALLBACK_UNKNOWN_CLIENT_TEMPLATE
    return (
        template
        .replace("{client_name}", client_name)
        .replace("{server_command}", server_command)
    )


_FALLBACK_UNKNOWN_CLIENT_TEMPLATE = """# Setting up canopy with {client_name}

canopy ships with built-in support for Claude Code, Codex, OpenCode, Cline,
Continue, Cursor, and Windsurf. For any other MCP-aware agent ({client_name}),
you have two options:

## Option 1 — Ask {client_name} to register canopy automatically

Paste this prompt to {client_name}:

> Register an MCP server named `canopy` for me.
> The server command is `{server_command}` and it speaks JSON-RPC over stdio.
> After registering, verify with the agent's MCP-status command and confirm
> canopy exposes tools `query`, `context`, `impact`, `define`, `imports_of`,
> and `stats`.

Most agents that understand MCP can do this in a single turn.

## Option 2 — Manual registration

1. Find where {client_name} stores its MCP server config (usually a JSON file
   like `mcp.json` or `config.json` somewhere in the user's home directory).
2. Add a `canopy` entry pointing at the command `{server_command}`.
3. Restart {client_name} so it picks up the new server.
4. Verify with the agent's MCP-status command.

## Verifying it worked

```sh
canopy --version          # should print "canopy X.Y.Z"
canopy serve              # starts the stdio server; Ctrl-C to stop
```

If `canopy serve` runs without errors, the agent should be able to spawn it
and call its tools.

## Adding {client_name} to canopy's built-in list

If {client_name} becomes popular, open an issue at
https://github.com/jb-bz/canopy/issues with:
- The exact config file path {client_name} reads
- The shape of the JSON/TOML it expects
- A copy-pasteable config snippet

We'll add it to `canopy.clients.KNOWN_CLIENTS` so future setups Just Work.
"""