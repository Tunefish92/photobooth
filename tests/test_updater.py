"""Update-check/apply logic. Network (fetch_latest_version) and subprocess
(apply_update's git/uv calls) are monkeypatched -- no live GitHub API calls
or real git/uv invocations here, so this stays fast and hermetic.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from photobooth import updater


# -- parse_version / is_newer ------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("v1.2.3", (1, 2, 3)),
        ("1.2.3", (1, 2, 3)),
        ("V0.1.0", (0, 1, 0)),
        ("1.2.3-beta", (1, 2, 3)),
        ("2.0", (2, 0)),
        ("garbage", (0,)),
        ("v1.x.3", (1, 0, 3)),
    ],
)
def test_parse_version(text, expected):
    assert updater.parse_version(text) == expected


def test_is_newer_true_when_candidate_has_higher_version():
    assert updater.is_newer("v0.2.0", "0.1.0") is True


def test_is_newer_false_when_candidate_is_equal_or_older():
    assert updater.is_newer("v0.1.0", "0.1.0") is False
    assert updater.is_newer("v0.0.9", "0.1.0") is False


def test_is_newer_handles_different_component_counts():
    assert updater.is_newer("v1.0", "0.9.9") is True
    assert updater.is_newer("v0.9", "0.9.0") is False


# -- fetch_latest_version -----------------------------------------------------


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


def test_fetch_latest_version_returns_tag_name(monkeypatch):
    monkeypatch.setattr(
        "httpx.get", lambda *a, **kw: _FakeResponse({"tag_name": "v9.9.9"})
    )
    assert updater.fetch_latest_version() == "v9.9.9"


def test_fetch_latest_version_propagates_http_errors(monkeypatch):
    import httpx

    def _raise(*args, **kwargs):
        raise httpx.HTTPStatusError("boom", request=None, response=None)

    monkeypatch.setattr("httpx.get", _raise)
    with pytest.raises(httpx.HTTPStatusError):
        updater.fetch_latest_version()


# -- repo_root ----------------------------------------------------------------


def test_repo_root_is_venv_parent(monkeypatch):
    monkeypatch.setattr("sys.prefix", str(Path("/opt/photobooth/.venv")))
    assert updater.repo_root() == Path("/opt/photobooth")


# -- _find_executable -----------------------------------------------------


def test_find_executable_uses_path_when_available(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    assert updater._find_executable("git") == "/usr/bin/git"


def test_find_executable_falls_back_to_local_bin(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    (fake_home / ".local" / "bin").mkdir(parents=True)
    uv_path = fake_home / ".local" / "bin" / "uv"
    uv_path.write_text("#!/bin/sh\n")

    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    assert updater._find_executable("uv") == str(uv_path)


def test_find_executable_raises_when_nowhere_found(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)  # empty, no .local/.cargo

    with pytest.raises(FileNotFoundError):
        updater._find_executable("uv")


# -- apply_update ---------------------------------------------------------


def test_apply_update_runs_fetch_checkout_sync_in_order(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "_find_executable", lambda name: name)
    calls: list[list[str]] = []

    def fake_run(command, cwd, capture_output, text, timeout):
        calls.append(command)
        assert cwd == tmp_path
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    updater.apply_update("v0.2.0", repo_dir=tmp_path)

    assert calls == [
        ["git", "fetch", "--tags", "origin"],
        ["git", "checkout", "v0.2.0"],
        ["uv", "sync"],
    ]


def test_apply_update_raises_with_stderr_on_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "_find_executable", lambda name: name)

    def fake_run(command, cwd, capture_output, text, timeout):
        if command[1] == "checkout":
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="fatal: not a valid tag")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="not a valid tag"):
        updater.apply_update("vBogus", repo_dir=tmp_path)


def test_apply_update_stops_after_first_failure(monkeypatch, tmp_path):
    """git fetch failing must not proceed to checkout/sync against
    whatever half-updated state is left behind."""
    monkeypatch.setattr(updater, "_find_executable", lambda name: name)
    calls: list[list[str]] = []

    def fake_run(command, cwd, capture_output, text, timeout):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="network unreachable")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError):
        updater.apply_update("v0.2.0", repo_dir=tmp_path)

    assert calls == [["git", "fetch", "--tags", "origin"]]
