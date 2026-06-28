"""`canopy setup` — interactive or non-interactive first-run configuration.

Two modes:

  - Interactive (default): walks the user through provider / model / client /
    API-key with sensible defaults.
  - Non-interactive (`--non-interactive`): all settings come from flags.
    Suitable for CI, dotfile repos, scripted deployments.

For unknown MCP clients (anything not in the seven built-ins), prints the
`docs/setup/UNKNOWN_CLIENT.md` doc instead of failing.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# ─── defaults ──────────────────────────────────────────────────────────

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL_ANTHROPIC = "MiniMax-M3"
DEFAULT_MODEL_OPENAI = "gpt-4o-mini"
DEFAULT_CLIENT = "claude-code"
DEFAULT_BASE_URL_ANTHROPIC = "https://api.minimax.io/anthropic"
DEFAULT_BASE_URL_OPENAI = "https://api.openai.com/v1"

KNOWN_PROVIDERS = ("anthropic", "openai")
KNOWN_PROVIDER_BASE_URLS = {
    "anthropic": DEFAULT_BASE_URL_ANTHROPIC,
    "openai": DEFAULT_BASE_URL_OPENAI,
}
KNOWN_PROVIDER_DEFAULT_MODELS = {
    "anthropic": DEFAULT_MODEL_ANTHROPIC,
    "openai": DEFAULT_MODEL_OPENAI,
}


# ─── interactive helpers ───────────────────────────────────────────────


def _prompt(label: str, default: str = "") -> str:
    """Read a line from stdin. Empty input returns `default`."""
    suffix = f" [{default}]" if default else ""
    sys.stdout.write(f"{label}{suffix}: ")
    sys.stdout.flush()
    try:
        line = input().strip()
    except EOFError:
        return default
    return line if line else default


def _prompt_choice(label: str, choices: tuple[str, ...], default: str) -> str:
    """Prompt with a numbered menu."""
    sys.stdout.write(f"{label} (choose one)\n")
    for i, c in enumerate(choices, start=1):
        marker = " (default)" if c == default else ""
        sys.stdout.write(f"  {i}) {c}{marker}\n")
    sys.stdout.write("> ")
    sys.stdout.flush()
    try:
        raw = input().strip()
    except EOFError:
        return default
    if not raw:
        return default
    # Accept either the number or the value.
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    if raw in choices:
        return raw
    return default


# ─── non-interactive + interactive common path ─────────────────────────


def _print_setup_summary(provider: str, model: str, client: str, base_url: str, api_key_set: bool) -> None:
    sys.stdout.write("\n--- canopy setup summary ---\n")
    sys.stdout.write(f"  provider:  {provider}\n")
    sys.stdout.write(f"  model:     {model}\n")
    sys.stdout.write(f"  base_url:  {base_url}\n")
    sys.stdout.write(f"  client:    {client}\n")
    sys.stdout.write(f"  api_key:   {'set' if api_key_set else '(empty — provider may not need one)'}\n\n")


def _run_non_interactive(args: argparse.Namespace) -> int:
    provider = args.provider
    if provider not in KNOWN_PROVIDERS:
        sys.stderr.write(f"error: unknown provider {provider!r}; known: {KNOWN_PROVIDERS}\n")
        return 2

    model = args.model or KNOWN_PROVIDER_DEFAULT_MODELS[provider]
    base_url = args.base_url or KNOWN_PROVIDER_BASE_URLS[provider]
    api_key = args.api_key or ""

    _print_setup_summary(provider, model, args.client, base_url, bool(api_key))

    client = args.client
    global_config_dir = Path(args.global_config_dir).expanduser() if args.global_config_dir else None

    # Defer import so the import-time graph is simpler.
    from canopy import clients

    if client not in clients.KNOWN_CLIENTS:
        sys.stdout.write(clients.render_unknown_client_doc(
            client_name=client,
            server_command="python -m canopy serve",
        ))
        sys.stdout.write("\n")
        return 0

    cfg = clients.resolve_client_config(client)

    # If --global-config-dir was passed, override the path inside cfg so tests
    # can run without touching the user's real home dir.
    if global_config_dir is not None:
        # Replace {home} placeholder with the override dir.
        cfg_path = cfg.config_path_template.replace("{home}", str(global_config_dir))
        cfg = clients.ClientConfig(
            name=cfg.name,
            config_path_template=cfg_path,
            config_format=cfg.config_format,
            mcp_section_key=cfg.mcp_section_key,
            server_command=cfg.server_command,
            server_args=list(cfg.server_args),
        )

    project_root = Path(args.project_root or ".").resolve()
    written = clients.register_for_client(cfg, project_root=project_root, global_=args.global_config)
    sys.stdout.write(f"wrote {written}\n")
    return 0


def _run_interactive(args: argparse.Namespace) -> int:
    provider = _prompt_choice("Provider", KNOWN_PROVIDERS, DEFAULT_PROVIDER)
    default_model = KNOWN_PROVIDER_DEFAULT_MODELS[provider]
    default_base = KNOWN_PROVIDER_BASE_URLS[provider]
    model = _prompt("Model", default_model)
    base_url = _prompt("Base URL", default_base)
    client = _prompt("MCP client (one of: known name, or any agent name for instructions)",
                     DEFAULT_CLIENT)
    api_key = _prompt("API key (leave empty for Ollama / local)", "")

    _print_setup_summary(provider, model, client, base_url, bool(api_key))

    from canopy import clients

    if client not in clients.KNOWN_CLIENTS:
        sys.stdout.write(clients.render_unknown_client_doc(
            client_name=client,
            server_command="python -m canopy serve",
        ))
        sys.stdout.write("\n")
        return 0

    cfg = clients.resolve_client_config(client)

    if args.global_config_dir:
        cfg_path = cfg.config_path_template.replace("{home}", str(Path(args.global_config_dir).expanduser()))
        cfg = clients.ClientConfig(
            name=cfg.name,
            config_path_template=cfg_path,
            config_format=cfg.config_format,
            mcp_section_key=cfg.mcp_section_key,
            server_command=cfg.server_command,
            server_args=list(cfg.server_args),
        )

    project_root = Path(args.project_root or ".").resolve()
    written = clients.register_for_client(cfg, project_root=project_root, global_=args.global_config)
    sys.stdout.write(f"wrote {written}\n")
    return 0


# ─── argparse + main ───────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canopy setup",
        description="First-run configuration for canopy (provider, model, MCP client).",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--interactive", action="store_true",
                      help="prompt for each setting (default mode)")
    mode.add_argument("--non-interactive", action="store_true",
                      help="read all settings from flags; no prompts")

    p.add_argument("--provider", choices=KNOWN_PROVIDERS,
                   help="LLM provider: 'anthropic' or 'openai'")
    p.add_argument("--model", help="model name (default depends on provider)")
    p.add_argument("--base-url", help="API base URL (default depends on provider)")
    p.add_argument("--client", default=DEFAULT_CLIENT,
                   help=f"MCP client name (default {DEFAULT_CLIENT}); any other name prints generic setup docs")
    p.add_argument("--api-key", help="API key (or set via env / bws later)")
    p.add_argument("--project-root", default=".",
                   help="where to write the config (default: cwd)")
    p.add_argument("--global-config", action="store_true",
                   help="write to the user's home-dir config (default: project-local)")
    p.add_argument("--global-config-dir",
                   help="override the home dir used for config writes (testing only)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.non_interactive:
        return _run_non_interactive(args)
    return _run_interactive(args)


if __name__ == "__main__":
    sys.exit(main())