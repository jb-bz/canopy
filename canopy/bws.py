"""Bitwarden Secrets wrapper.

The reference tool (`~/.hermes/scripts/canopy.py` lines 201-211) shells
out to the `bws` CLI and parses its JSON. We do the same here, but raise
a typed error instead of `SystemExit` so callers can decide what to do.
"""
from __future__ import annotations

import json
import subprocess
from typing import Any


class BwsError(RuntimeError):
    """Raised when `bws secret get` fails or returns malformed JSON."""


def fetch_secret(secret_id: str, *, timeout: int = 10) -> str:
    """Fetch a single secret's value from Bitwarden Secrets via the bws CLI.

    Returns the `value` field of the bws JSON response.
    """
    try:
        proc = subprocess.run(
            ["bws", "secret", "get", secret_id],
            capture_output=True, text=True, timeout=timeout, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise BwsError(f"bws secret get failed: {e}") from e

    try:
        data: Any = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise BwsError(f"bws returned invalid JSON: {e}") from e

    if not isinstance(data, dict) or "value" not in data:
        raise BwsError(f"bws JSON missing 'value' field: {proc.stdout[:200]!r}")

    return data["value"]