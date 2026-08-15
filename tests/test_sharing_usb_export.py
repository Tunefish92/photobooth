"""USB export tests. See test_sharing_mailer.py and test_sharing_webdav.py
for the email/WebDAV backends (mocked smtplib/httpx rather than a live
server or credentials)."""

import sys
from pathlib import Path

import pytest

from photobooth.core.session import CaptureSession
from photobooth.sharing.usb_export import (
    export_session,
    export_to_first_available,
    find_removable_mounts,
)


def make_session_with_files(tmp_path: Path) -> CaptureSession:
    session = CaptureSession(mode="single", target_shot_count=1)
    shot = tmp_path / "shot_00.jpg"
    shot.write_bytes(b"shot-bytes")
    session.add_shot(shot)
    result = tmp_path / "result.jpg"
    result.write_bytes(b"result-bytes")
    session.result_path = result
    return session


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="tests the non-Linux early-return path")
def test_find_removable_mounts_returns_empty_off_linux():
    assert find_removable_mounts() == []


def test_export_to_first_available_returns_none_when_no_mounts(monkeypatch):
    monkeypatch.setattr("photobooth.sharing.usb_export.find_removable_mounts", lambda: [])
    assert export_to_first_available(CaptureSession(mode="single", target_shot_count=1)) is None


def test_export_session_copies_shots_and_result(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    session = make_session_with_files(src_dir)
    mount = tmp_path / "usb"
    mount.mkdir()

    dest = export_session(session, mount)

    assert dest == mount / "photobooth" / session.id
    assert (dest / "shot_00.jpg").read_bytes() == b"shot-bytes"
    assert (dest / "result.jpg").read_bytes() == b"result-bytes"


def test_export_session_without_result_path_only_copies_shots(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    session = make_session_with_files(src_dir)
    session.result_path = None
    mount = tmp_path / "usb"
    mount.mkdir()

    dest = export_session(session, mount)

    assert (dest / "shot_00.jpg").is_file()
    assert list(dest.iterdir()) == [dest / "shot_00.jpg"]


def test_export_to_first_available_uses_the_first_mount(tmp_path: Path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    session = make_session_with_files(src_dir)
    mount_a = tmp_path / "mount_a"
    mount_a.mkdir()
    mount_b = tmp_path / "mount_b"
    mount_b.mkdir()
    monkeypatch.setattr(
        "photobooth.sharing.usb_export.find_removable_mounts", lambda: [mount_a, mount_b]
    )

    dest = export_to_first_available(session)

    assert dest == mount_a / "photobooth" / session.id
    assert not (mount_b / "photobooth").exists()
