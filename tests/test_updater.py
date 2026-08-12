"""Update-check/apply logic.

Most of these mock the network call (fetch_latest_version) and the
subprocess calls (apply_update's git/uv) for speed and hermeticity. The
integration test at the bottom of this file is the exception -- it runs
apply_update()'s git fetch/checkout against two real local git repos
(standing in for GitHub and the Pi's clone), only stubbing the `uv sync`
step, to actually prove the checkout lands on the tagged commit's content
and not just "whatever the default branch happens to be" -- pure argument-
order assertions on a mocked subprocess.run can't catch that class of bug.
"""

from __future__ import annotations

import shutil
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


# -- real-git integration test -----------------------------------------------


def _resolve_git() -> str:
    found = shutil.which("git")
    if found:
        return found
    windows_fallback = Path("C:/Program Files/Git/cmd/git.exe")
    if windows_fallback.is_file():
        return str(windows_fallback)
    pytest.skip("git executable not found on PATH or in the usual Windows install location")


def _git(git_exe: str, args: list[str], cwd: Path) -> None:
    result = subprocess.run(
        [git_exe, *args], cwd=cwd, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"


def test_apply_update_lands_on_the_tagged_commit_against_real_git_repos(monkeypatch, tmp_path):
    """End-to-end: two real git repos (an "origin" and a clone of it,
    standing in for GitHub and the Pi's checkout) with three commits --
    v0.1.0, v0.2.0, and an untagged commit after it representing unreleased
    work-in-progress on the default branch. The clone starts out sitting at
    v0.1.0 (simulating "the Pi is running the previous release"). Only
    `uv sync` is stubbed (it needs a real project to sync, which isn't what
    this test is about); the git fetch/checkout is 100% real.

    This is the check a mocked-subprocess test can't give you: that
    apply_update() actually lands on the *tagged* commit's content, not
    just wherever the origin's default branch happens to be (which here is
    one commit *ahead* of the release it should stop at).
    """
    git_exe = _resolve_git()

    origin = tmp_path / "origin"
    origin.mkdir()
    _git(git_exe, ["init", "-q", "-b", "main"], origin)
    _git(git_exe, ["config", "user.email", "test@example.com"], origin)
    _git(git_exe, ["config", "user.name", "Test"], origin)

    def commit_version(version: str, tag: str | None) -> None:
        (origin / "VERSION").write_text(version)
        _git(git_exe, ["add", "."], origin)
        _git(git_exe, ["commit", "-q", "-m", version], origin)
        if tag:
            _git(git_exe, ["tag", tag], origin)

    commit_version("0.1.0", "v0.1.0")
    commit_version("0.2.0", "v0.2.0")
    commit_version("0.3.0-dev", None)  # unreleased work past v0.2.0

    clone = tmp_path / "clone"
    _git(git_exe, ["clone", "-q", str(origin), str(clone)], tmp_path)
    _git(git_exe, ["checkout", "-q", "v0.1.0"], clone)  # "currently running" release
    assert (clone / "VERSION").read_text() == "0.1.0"

    # apply_update's own executable resolution: real git, stubbed uv (its
    # sync step is irrelevant to what this test is verifying).
    def fake_find_executable(name: str) -> str:
        return git_exe if name == "git" else name

    def fake_run(command: list[str], cwd: Path) -> None:
        if Path(command[0]).name.startswith("uv"):
            return  # pretend `uv sync` succeeded
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)

    monkeypatch.setattr(updater, "_find_executable", fake_find_executable)
    monkeypatch.setattr(updater, "_run", fake_run)

    updater.apply_update("v0.2.0", repo_dir=clone)

    assert (clone / "VERSION").read_text() == "0.2.0"  # landed exactly on the tag,
    # not on the untagged "0.3.0-dev" commit that came after it on origin/main

