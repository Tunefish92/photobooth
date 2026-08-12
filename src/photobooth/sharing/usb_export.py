"""Copies a session's photos onto an auto-detected removable USB drive.

Raspberry Pi OS auto-mounts USB storage under /media/<user>/<label> (or
/run/media on some setups); we just scan those for writable mount points.
This is a Linux/kiosk feature -- on other platforms detection returns empty
rather than failing, so the button can stay hidden.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from photobooth.core.session import CaptureSession


def find_removable_mounts() -> list[Path]:
    if not sys.platform.startswith("linux"):
        return []
    mounts: list[Path] = []
    for base in (Path("/media"), Path("/run/media")):
        if not base.is_dir():
            continue
        for user_dir in base.iterdir():
            if user_dir.is_dir():
                mounts.extend(p for p in user_dir.iterdir() if p.is_dir())
    return mounts


def export_session(session: CaptureSession, mount: Path) -> Path:
    dest = mount / "photobooth" / session.id
    dest.mkdir(parents=True, exist_ok=True)
    for shot in session.shots:
        shutil.copy2(shot, dest / shot.name)
    if session.result_path is not None:
        shutil.copy2(session.result_path, dest / session.result_path.name)
    return dest


def export_to_first_available(session: CaptureSession) -> Path | None:
    mounts = find_removable_mounts()
    if not mounts:
        return None
    return export_session(session, mounts[0])
