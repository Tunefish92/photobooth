"""find_removable_devices()/resolve_mount_path() read three real Linux
paths (/media + /run/media, /proc/mounts, /dev/disk/by-uuid). /proc/mounts
is a plain text file, easy to fake -- but /dev/disk/by-uuid is a directory
of *symlinks*, and creating those needs elevated privileges on Windows
(where this suite also runs, for local dev). So the higher-level
orchestration tests below fake `_uuid_for_device_node` directly instead of
real symlinks; `_uuid_for_device_node` itself (the actual symlink-reading
logic) gets a narrower, Linux-only test that does create real ones.

sys.platform is forced to "linux" as the *last* step of each test's setup,
never as a blanket autouse fixture -- pytest's own tmp_path machinery
checks sys.platform internally, so patching it globally before tmp_path
finishes its setup breaks pytest itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from photobooth.backup import devices


@pytest.fixture
def fake_root(tmp_path: Path, monkeypatch):
    """Fake /media/pi/<label> + /proc/mounts, with `_uuid_for_device_node`
    stubbed to a lookup table -- returns a helper to add one "plugged in"
    removable drive."""
    media = tmp_path / "media" / "pi"
    media.mkdir(parents=True)
    proc_mounts = tmp_path / "proc_mounts"
    proc_mounts.write_text("", encoding="utf-8")
    uuid_by_device_node: dict[str, str] = {}

    monkeypatch.setattr(devices, "_MEDIA_ROOTS", (media.parent,))
    monkeypatch.setattr(devices, "_PROC_MOUNTS", proc_mounts)
    monkeypatch.setattr(devices, "_uuid_for_device_node", lambda node: uuid_by_device_node.get(node, ""))
    monkeypatch.setattr(sys, "platform", "linux")

    def add_device(label: str, uuid: str) -> Path:
        mount_point = media / label
        mount_point.mkdir()
        device_node = f"/dev/sd_{label}1"
        uuid_by_device_node[device_node] = uuid
        proc_mounts.write_text(
            proc_mounts.read_text("utf-8") + f"{device_node} {mount_point} vfat rw 0 0\n",
            encoding="utf-8",
        )
        return mount_point

    return add_device


def test_find_removable_devices_returns_empty_off_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert devices.find_removable_devices() == []


def test_find_removable_devices_returns_empty_with_nothing_plugged_in(fake_root):
    assert devices.find_removable_devices() == []


def test_find_removable_devices_finds_a_plugged_in_drive(fake_root):
    mount_point = fake_root("MYDRIVE", "1234-ABCD")

    found = devices.find_removable_devices()

    assert len(found) == 1
    assert found[0].uuid == "1234-ABCD"
    assert found[0].label == "MYDRIVE"
    assert found[0].mount_path == mount_point


def test_find_removable_devices_finds_multiple_drives(fake_root):
    fake_root("FIRST", "aaaa-1111")
    fake_root("SECOND", "bbbb-2222")

    found = devices.find_removable_devices()

    assert {d.uuid for d in found} == {"aaaa-1111", "bbbb-2222"}


def test_find_removable_devices_skips_a_mount_with_no_resolvable_uuid(fake_root, tmp_path):
    """A mount that isn't a real partition (or whose UUID just can't be
    found) is skipped -- a backup device has to be re-identifiable later,
    so there's nothing useful to offer for it."""
    media = tmp_path / "media" / "pi"
    mount_point = media / "NO_UUID"
    mount_point.mkdir()
    proc_mounts = devices._PROC_MOUNTS
    proc_mounts.write_text(f"/dev/sdz1 {mount_point} vfat rw 0 0\n", encoding="utf-8")

    assert devices.find_removable_devices() == []


def test_resolve_mount_path_finds_the_current_mount(fake_root):
    mount_point = fake_root("MYDRIVE", "1234-ABCD")

    assert devices.resolve_mount_path("1234-ABCD") == mount_point


def test_resolve_mount_path_returns_none_when_not_plugged_in(fake_root):
    fake_root("MYDRIVE", "1234-ABCD")

    assert devices.resolve_mount_path("not-the-right-uuid") is None


def test_resolve_mount_path_returns_none_for_empty_uuid(fake_root):
    assert devices.resolve_mount_path("") is None


def test_resolve_mount_path_follows_the_same_uuid_to_a_new_mount_point(fake_root, tmp_path):
    """The whole point of keying by UUID instead of mount path: the same
    physical drive, replugged (a different label or USB port -- Raspberry
    Pi OS mounts by label), still resolves to wherever it's *currently*
    mounted."""
    old_mount = fake_root("OLD_LABEL", "1234-ABCD")
    assert devices.resolve_mount_path("1234-ABCD") == old_mount

    # Simulate a replug: the old mount is gone, the same UUID shows up at
    # a new one (re-write /proc/mounts with only the new entry).
    new_mount = tmp_path / "media" / "pi" / "NEW_LABEL"
    new_mount.mkdir()
    devices._PROC_MOUNTS.write_text(
        f"/dev/sd_OLD_LABEL1 {new_mount} vfat rw 0 0\n", encoding="utf-8"
    )

    assert devices.resolve_mount_path("1234-ABCD") == new_mount


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs elevated privileges on Windows")
def test_uuid_for_device_node_reads_the_by_uuid_symlink(tmp_path: Path, monkeypatch):
    """Narrow test of the actual symlink-reading logic that the tests
    above stub out -- exercised for real here, on a platform where
    creating a symlink doesn't need admin/Developer Mode."""
    by_uuid = tmp_path / "by-uuid"
    by_uuid.mkdir()
    device_node = tmp_path / "dev" / "sda1"
    device_node.parent.mkdir()
    device_node.write_bytes(b"")
    (by_uuid / "1234-ABCD").symlink_to(device_node)
    monkeypatch.setattr(devices, "_BY_UUID_DIR", by_uuid)

    assert devices._uuid_for_device_node(str(device_node)) == "1234-ABCD"


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs elevated privileges on Windows")
def test_uuid_for_device_node_returns_empty_for_unknown_device(tmp_path: Path, monkeypatch):
    by_uuid = tmp_path / "by-uuid"
    by_uuid.mkdir()
    monkeypatch.setattr(devices, "_BY_UUID_DIR", by_uuid)

    assert devices._uuid_for_device_node("/dev/sdz9") == ""
