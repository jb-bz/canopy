# Setting up canopy with an MCP-aware agent that isn't built-in

canopy ships with built-in support for **Claude Code, Codex, OpenCode, Cline, Continue, Cursor, and Windsurf** (the seven most popular MCP clients as of 2026). For any other MCP-aware agent, follow the steps below.

## What you need to register

| Field | Value |
|---|---|
| Server name | `canopy` |
| Command | `python -m canopy serve` |
| Transport | `stdio` (JSON-RPC over stdin/stdout) |
| Tools exposed | `query`, `context`, `impact`, `define`, `imports_of`, `stats` |

The Python interpreter used must be the one where `canopy` is installed
(`pip install canopy` first). If the agent's MCP subsystem runs commands
through a different shell, prefix the command with the full path to
Python, e.g. `/usr/local/bin/python3 -m canopy serve` or the venv path
`/path/to/venv/bin/python -m canopy serve`.

## Option 1 — Ask the agent to register canopy for you

Paste this prompt to your agent (clawbot, nanobot, etc.):

> Register an MCP server named `canopy` for me. The server command is
> `python -m canopy serve` and it speaks JSON-RPC over stdio. After
> registering, verify with the agent's MCP-status command and confirm
> canopy exposes the tools `query`, `context`, `impact`, `define`,
> `imports_of`, and `stats`.

Most agents that understand MCP can complete this in one turn. If your
agent doesn't auto-discover the new server, restart it.

## Option 2 — Manual registration

1. Find where your agent stores its MCP server config. Common locations:
   - `~/.<agent-name>/config.json`
   - `~/.<agent-name>/mcp.json`
   - `~/Library/Application Support/<agent-name>/settings.json` (macOS)
   - `$XDG_CONFIG_HOME/<agent-name>/config.json` (Linux)
2. Add a `canopy` entry. The shape depends on the agent — most use one of:
   ```json
   {
     "mcpServers": {
       "canopy": {
         "command": "python",
         "args": ["-m", "canopy", "serve"]
       }
     }
   }
   ```
   ```toml
   [mcp_servers.canopy]
   command = "python"
   args = ["-m", "canopy", "serve"]
   ```
   (Use whichever matches your agent's existing config style.)
3. Save the file. Restart the agent so it picks up the new server.
4. Verify with the agent's MCP-status command.

## Verifying it worked

```sh
canopy --version          # should print "canopy X.Y.Z"
canopy serve              # starts the stdio server; Ctrl-C to stop
```

If `canopy serve` runs without errors, the agent should be able to
spawn it and call its tools.

If the agent reports it can't find `canopy` or `python -m canopy serve`,
the most likely cause is a Python environment mismatch — the agent's
subprocess doesn't see the `canopy` package. Fix by either:

- Installing canopy in the agent's Python: `pip install canopy` from
  whatever environment the agent's MCP subsystem uses.
- Pointing the command at the absolute path to your canopy's Python:
  e.g. `/Users/you/.venv/bin/python -m canopy serve`.

## Adding {agent} to canopy's built-in list

If your agent becomes popular, open an issue at
https://github.com/jb-bz/canopy/issues with:

- The exact config file path the agent reads
- The shape of the JSON/TOML it expects
- A copy-pasteable config snippet

We'll add it to `canopy.clients.KNOWN_CLIENTS` so future setups
just work.

---

**Last updated:** 2026-06-28 (canopy v0.3.0)