"""Phase 1 acceptance tests: fill subcommand end-to-end.

Covers:
- canopy.bws: fetch_secret reads bws JSON output
- canopy.llm: call_minimax POSTs to the Anthropic-compatible endpoint
- canopy.fill: batching, JSON parsing, regex fallback, dry-run
- canopy.hindsight: retain is best-effort and silent on failure
- canopy.cli.cmd_fill: integrates everything with --dry-run, --retain-hindsight
"""
from __future__ import annotations

import json
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from canopy.bws import BwsError, fetch_secret
from canopy.llm import LlmError, call_minimax
from canopy.fill import fill_missing
from canopy.hindsight import retain


# ─── bws ───────────────────────────────────────────────────────────────


def test_fetch_secret_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_proc = MagicMock(stdout=json.dumps({"value": "secret-key"}), returncode=0)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_proc)
    assert fetch_secret("any-uuid") == "secret-key"


def test_fetch_secret_raises_on_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_proc = MagicMock(stdout="not json", returncode=0)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_proc)
    with pytest.raises(BwsError):
        fetch_secret("any-uuid")


def test_fetch_secret_raises_on_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_proc = MagicMock(stdout=json.dumps({"id": "x"}), returncode=0)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_proc)
    with pytest.raises(BwsError):
        fetch_secret("any-uuid")


# ─── llm ───────────────────────────────────────────────────────────────


def test_call_minimax_posts_to_anthropic_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.method
        captured["headers"] = dict(req.headers)
        captured["body"] = json.loads(req.data.decode())
        resp = MagicMock()
        resp.read.return_value = json.dumps({
            "content": [{"type": "text", "text": '{"foo.py": "the foo file"}'}]
        }).encode()
        resp.__enter__ = lambda self: self
        resp.__exit__ = lambda self, *a: None
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = call_minimax("describe foo.py", api_key="k", base_url="https://x.test", model="m")
    assert out == '{"foo.py": "the foo file"}'
    assert captured["url"] == "https://x.test/v1/messages"
    # urllib normalizes header case; look up via case-insensitive lookup.
    headers_lc = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_lc["x-api-key"] == "k"
    assert headers_lc["anthropic-version"] == "2023-06-01"
    assert captured["body"]["model"] == "m"


def test_call_minimax_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(LlmError):
        call_minimax("p", api_key="k", base_url="https://x.test", model="m")


# ─── fill ──────────────────────────────────────────────────────────────


def test_fill_missing_batches_and_merges_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """3 paths, batch=2 → 2 LLM calls; results merged into one dict."""
    missing = [("a.py", "file"), ("b.py", "file"), ("c.py", "file")]
    calls: list[str] = []

    def fake_llm(prompt: str, **_):
        calls.append(prompt)
        if "a.py" in prompt and "b.py" in prompt:
            return '{"a.py": "alpha", "b.py": "bravo"}'
        return '{"c.py": "charlie"}'

    monkeypatch.setattr("canopy.fill.llm", MagicMock(call_minimax=fake_llm))
    monkeypatch.setattr("canopy.fill.bws", MagicMock(fetch_secret=lambda _id: "k"))

    result = fill_missing(missing, {}, batch_size=2, max_words=15,
                          base_url="https://x.test", model="m", secret_id="uuid")
    assert result == {"a.py": "alpha", "b.py": "bravo", "c.py": "charlie"}
    assert len(calls) == 2  # batched into 2 calls


def test_fill_missing_falls_back_to_regex_on_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model returns malformed JSON → regex extracts individual entries."""
    missing = [("a.py", "file"), ("b.py", "file")]
    monkeypatch.setattr("canopy.fill.llm", MagicMock(call_minimax=lambda prompt, **_: (
        'I cannot produce JSON.\n'
        '"a.py": "alpha description"\n'
        '"b.py": "bravo description"\n'
    )))
    monkeypatch.setattr("canopy.fill.bws", MagicMock(fetch_secret=lambda _id: "k"))

    result = fill_missing(missing, {}, batch_size=50, max_words=15,
                          base_url="https://x.test", model="m", secret_id="uuid")
    assert result == {"a.py": "alpha description", "b.py": "bravo description"}


def test_fill_missing_skips_missing_paths_in_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """If LLM returns JSON missing some paths, only present ones are recorded."""
    missing = [("a.py", "file"), ("b.py", "file"), ("c.py", "file")]
    monkeypatch.setattr("canopy.fill.llm", MagicMock(call_minimax=lambda prompt, **_: '{"a.py": "alpha"}'))
    monkeypatch.setattr("canopy.fill.bws", MagicMock(fetch_secret=lambda _id: "k"))
    result = fill_missing(missing, {}, batch_size=50, max_words=15,
                          base_url="https://x.test", model="m", secret_id="uuid")
    assert result == {"a.py": "alpha"}


def test_fill_missing_truncates_long_descriptions(monkeypatch: pytest.MonkeyPatch) -> None:
    missing = [("a.py", "file")]
    long = "x" * 500
    monkeypatch.setattr("canopy.fill.llm", MagicMock(call_minimax=lambda *a, **kw: json.dumps({"a.py": long})))
    monkeypatch.setattr("canopy.fill.bws", MagicMock(fetch_secret=lambda _id: "k"))
    result = fill_missing(missing, {}, batch_size=50, max_words=15,
                          base_url="https://x.test", model="m", secret_id="uuid")
    assert len(result["a.py"]) == 200  # hard cap


def test_fill_missing_empty_input_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """No missing paths → no LLM calls."""
    calls = []
    monkeypatch.setattr("canopy.fill.llm", MagicMock(call_minimax=lambda *a, **kw: (calls.append(1), "{}")[1]))
    monkeypatch.setattr("canopy.fill.bws", MagicMock(fetch_secret=lambda _id: "k"))
    result = fill_missing([], {}, batch_size=50, max_words=15,
                          base_url="https://x.test", model="m", secret_id="uuid")
    assert result == {}
    assert calls == []


# ─── hindsight ─────────────────────────────────────────────────────────


def test_hindsight_retain_returns_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    resp = MagicMock()
    resp.__enter__ = lambda self: self
    resp.__exit__ = lambda self, *a: None
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: resp)
    assert retain(["fact"], "http://h:8888", "bank") is True


def test_hindsight_retain_returns_false_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: (_ for _ in ()).throw(OSError("nope")))
    assert retain(["fact"], "http://h:8888", "bank") is False


def test_hindsight_retain_empty_facts_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: pytest.fail("should not call urlopen"))
    assert retain([], "http://h:8888", "bank") is True


# ─── cli integration ──────────────────────────────────────────────────


def test_cli_fill_dry_run_does_not_modify_yaml(tmp_path: Path) -> None:
    """`canopy --root X fill --dry-run` must not write the YAML."""
    from canopy.cli import main

    # Set up a minimal repo with one file and a YAML missing its description.
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')")

    ypath = tmp_path / "canopy.yaml"
    ypath.write_text("tree:\n  _kind: dir\n  _description: ''\nsignature: ''\n")

    fake_results = {"src/main.py": "entry point"}
    with patch("canopy.fill.fill_missing", return_value=fake_results) as mock_fill, \
         patch("canopy.fill.llm", MagicMock()), \
         patch("canopy.fill.bws", MagicMock()):
        rc = main(["--root", str(tmp_path), "fill", "--dry-run"])

    assert rc == 0
    mock_fill.assert_not_called()  # dry-run skips the LLM entirely
    text = ypath.read_text()
    assert "entry point" not in text
    assert "src/main.py" not in text


def test_cli_fill_writes_yaml_when_not_dry_run(tmp_path: Path) -> None:
    """Without --dry-run, fill results are written to the YAML."""
    from canopy.cli import main

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')")
    ypath = tmp_path / "canopy.yaml"
    ypath.write_text("tree:\n  _kind: dir\n  _description: ''\nsignature: ''\n")

    fake_results = {"src/main.py": "entry point"}
    with patch("canopy.fill.fill_missing", return_value=fake_results), \
         patch("canopy.fill.llm", MagicMock()), \
         patch("canopy.fill.bws", MagicMock()):
        rc = main(["--root", str(tmp_path), "fill"])

    assert rc == 0
    text = ypath.read_text()
    assert "entry point" in text


def test_cli_fill_retain_hindsight_called_when_flag_set(tmp_path: Path) -> None:
    from canopy.cli import main

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("")
    (tmp_path / "canopy.yaml").write_text("tree:\n  _kind: dir\n  _description: ''\nsignature: ''\n")

    fake_results = {"src/main.py": "entry point"}
    with patch("canopy.fill.fill_missing", return_value=fake_results), \
         patch("canopy.fill.llm", MagicMock()), \
         patch("canopy.fill.bws", MagicMock()), \
         patch("canopy.hindsight.retain", return_value=True) as mock_retain:
        rc = main(["--root", str(tmp_path), "fill", "--retain-hindsight"])

    assert rc == 0
    mock_retain.assert_called_once()
    # Hindsight bank should be the configured one.
    args, _ = mock_retain.call_args
    assert args[1] == "http://localhost:8888"
    assert args[2] == "coding-agent-stack"