"""Hindsight retain — best-effort logging to a Hindsight bank.

`~/.hermes/scripts/canopy.py` lines 286-315. Silent on failure by design:
a fill should never fail because Hindsight is down.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def retain(facts: list[str], url: str, bank: str, *, timeout: int = 15) -> bool:
    """POST facts to a Hindsight bank. Returns True on success, False on any error.

    Hindsight retain endpoint (v1):
      POST {url}/v1/default/banks/{bank}/memories
      body: {"items": [{"content": "...", "context": "..."}], "async": false}
    """
    if not facts:
        return True
    try:
        body = json.dumps({
            "items": [{"content": f, "context": "canopy-fill"} for f in facts],
            "async": False,
        }).encode()
        endpoint = f"{url.rstrip('/')}/v1/default/banks/{bank}/memories"
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False