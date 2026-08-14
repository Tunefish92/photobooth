"""Checks GitHub Releases for a newer version and applies it in place.

Update flow: fetch the latest release tag, compare it to the running
`__version__`, and if newer, `git checkout` that exact tag (not just
whatever HEAD of main happens to be -- the running code should always match
a real, tagged release) followed by `uv sync` to pick up any dependency
changes. The app then exits; the desktop autostart wrapper's restart loop
(see `scripts/run-kiosk.sh`) brings it back up running the new code. This
only ever does anything useful on the Pi deployment (a real git clone managed by
`scripts/install.sh`) -- on a Windows/macOS dev checkout it will generally
just fail the git/uv steps harmlessly if triggered.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import httpx

from photobooth import __version__

_RELEASES_API = "https://api.github.com/repos/Tunefish92/photobooth/releases"
_REQUEST_TIMEOUT_S = 10.0
_SUBPROCESS_TIMEOUT_S = 120.0


def parse_version(text: str) -> tuple[int, ...]:
    """"v1.2.3" / "1.2.3" / "1.2.3-beta" -> (1, 2, 3). Trailing non-numeric
    suffixes on the last component are dropped; unparsable components
    become 0 rather than raising, so a weird tag never crashes the
    comparison -- worst case it just looks no-newer.
    """
    text = text.strip()
    if text[:1] in ("v", "V"):
        text = text[1:]
    parts: list[int] = []
    for chunk in text.split("."):
        digits = ""
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def fetch_latest_version() -> str:
    """Blocking network call -- always run via run_in_background, never on
    the UI thread.

    Deliberately hits GET /releases (the full list, newest first) rather
    than GET /releases/latest: that "latest" endpoint explicitly excludes
    prereleases by GitHub's own definition ("the most recent non-prerelease,
    non-draft release"), and 404s entirely if every release is a
    prerelease -- which the project's own v0.1.0 (Beta) currently is. The
    list endpoint has no such filter, so this just takes the newest entry
    regardless of its prerelease flag.
    """
    response = httpx.get(
        _RELEASES_API,
        timeout=_REQUEST_TIMEOUT_S,
        headers={"Accept": "application/vnd.github+json"},
        params={"per_page": 1},
    )
    response.raise_for_status()
    releases = response.json()
    if not releases:
        raise ValueError("Repository has no releases")
    return str(releases[0]["tag_name"])


def repo_root() -> Path:
    """The app runs from `<repo>/.venv/bin/photobooth` per install.sh, so
    the venv's grandparent is the repo checkout."""
    return Path(sys.prefix).parent


def _find_executable(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for candidate_dir in (Path.home() / ".local" / "bin", Path.home() / ".cargo" / "bin"):
        candidate = candidate_dir / name
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(
        f"{name!r} executable not found on PATH, ~/.local/bin, or ~/.cargo/bin"
    )


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)!r} failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def apply_update(tag: str, repo_dir: Path | None = None) -> None:
    """Checks out `tag` exactly and re-syncs dependencies. Raises RuntimeError
    (with the failing command's stderr) on any failure; the caller is
    responsible for restarting the process afterwards -- this function never
    exits or restarts anything itself, so it stays plainly testable.
    """
    repo = repo_dir if repo_dir is not None else repo_root()
    git = _find_executable("git")
    uv = _find_executable("uv")

    _run([git, "fetch", "--tags", "origin"], cwd=repo)
    _run([git, "checkout", tag], cwd=repo)
    _run([uv, "sync"], cwd=repo)


__all__ = [
    "apply_update",
    "fetch_latest_version",
    "is_newer",
    "parse_version",
    "repo_root",
]

# Re-exported for convenience so callers don't need a separate import of
# photobooth.__version__ just to compare against fetch_latest_version()'s result.
CURRENT_VERSION = __version__
