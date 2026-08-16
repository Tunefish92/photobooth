"""run_backup() tests. resolve_mount_path() (the only real Linux-specific
dependency) is stubbed directly rather than faking /proc/mounts etc. --
that's devices.py's own job, covered in test_backup_devices.py.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from photobooth.backup import service
from photobooth.config.settings import BackupConfig


def _config(**overrides) -> BackupConfig:
    defaults = dict(enable=True, device_uuid="1234-ABCD", device_label="MYDRIVE", auto_interval_min=0)
    defaults.update(overrides)
    return BackupConfig(**defaults)


@pytest.fixture
def mount_path(tmp_path: Path, monkeypatch) -> Path:
    mount = tmp_path / "mount"
    mount.mkdir()
    monkeypatch.setattr(service, "resolve_mount_path", lambda uuid: mount if uuid else None)
    return mount


@pytest.fixture
def photos_root(tmp_path: Path) -> Path:
    root = tmp_path / "photos"
    (root / "2026-08-20").mkdir(parents=True)
    (root / "2026-08-20" / "shot_00.jpg").write_bytes(b"shot-a")
    (root / "2026-08-20" / "shot_01.jpg").write_bytes(b"shot-b")
    return root


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "photobooth.sqlite3"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE photos (id INTEGER PRIMARY KEY, path TEXT)")
    conn.execute("INSERT INTO photos (path) VALUES ('a.jpg')")
    conn.commit()
    conn.close()
    return path


def test_run_backup_raises_when_device_not_plugged_in(photos_root: Path, db_path: Path, monkeypatch):
    monkeypatch.setattr(service, "resolve_mount_path", lambda uuid: None)

    with pytest.raises(service.BackupDeviceUnavailable):
        service.run_backup(_config(), photos_root, db_path)


def test_run_backup_copies_all_files_on_first_run(mount_path: Path, photos_root: Path, db_path: Path):
    result = service.run_backup(_config(), photos_root, db_path)

    assert result.files_copied == 2
    assert result.files_skipped == 0
    assert result.db_backed_up is True
    dest = mount_path / service.BACKUP_DIRNAME
    assert result.destination == dest
    assert (dest / "photos" / "2026-08-20" / "shot_00.jpg").read_bytes() == b"shot-a"
    assert (dest / "photos" / "2026-08-20" / "shot_01.jpg").read_bytes() == b"shot-b"
    assert (dest / db_path.name).is_file()


def test_run_backup_second_run_skips_unchanged_files(mount_path: Path, photos_root: Path, db_path: Path):
    service.run_backup(_config(), photos_root, db_path)

    result = service.run_backup(_config(), photos_root, db_path)

    assert result.files_copied == 0
    assert result.files_skipped == 2


def test_run_backup_recopies_a_changed_file(mount_path: Path, photos_root: Path, db_path: Path):
    service.run_backup(_config(), photos_root, db_path)

    shot = photos_root / "2026-08-20" / "shot_00.jpg"
    # Bump the mtime forward so the incremental check (size+mtime) sees it
    # as changed even though the file system's mtime resolution might
    # otherwise not distinguish "just now" from the first backup.
    new_mtime = time.time() + 5
    shot.write_bytes(b"shot-a-updated")
    import os

    os.utime(shot, (new_mtime, new_mtime))

    result = service.run_backup(_config(), photos_root, db_path)

    assert result.files_copied == 1
    assert result.files_skipped == 1
    dest = mount_path / service.BACKUP_DIRNAME / "photos" / "2026-08-20" / "shot_00.jpg"
    assert dest.read_bytes() == b"shot-a-updated"


def test_run_backup_database_snapshot_is_a_valid_independent_copy(
    mount_path: Path, photos_root: Path, db_path: Path
):
    result = service.run_backup(_config(), photos_root, db_path)

    backup_db = result.destination / db_path.name
    conn = sqlite3.connect(str(backup_db))
    rows = conn.execute("SELECT path FROM photos").fetchall()
    conn.close()
    assert rows == [("a.jpg",)]

    # Changing the source afterward must not affect the already-taken
    # snapshot -- it's a real independent copy, not a shared/linked file.
    source_conn = sqlite3.connect(str(db_path))
    source_conn.execute("INSERT INTO photos (path) VALUES ('b.jpg')")
    source_conn.commit()
    source_conn.close()

    conn = sqlite3.connect(str(backup_db))
    rows = conn.execute("SELECT path FROM photos").fetchall()
    conn.close()
    assert rows == [("a.jpg",)]


def test_run_backup_missing_photos_dir_is_not_an_error(mount_path: Path, db_path: Path, tmp_path: Path):
    missing_root = tmp_path / "does-not-exist"

    result = service.run_backup(_config(), missing_root, db_path)

    assert result.files_copied == 0
    assert result.files_skipped == 0
    assert result.db_backed_up is True


def test_run_backup_missing_database_is_not_an_error(mount_path: Path, photos_root: Path, tmp_path: Path):
    missing_db = tmp_path / "does-not-exist.sqlite3"

    result = service.run_backup(_config(), photos_root, missing_db)

    assert result.db_backed_up is False


def test_run_backup_appends_one_manifest_line_per_run(mount_path: Path, photos_root: Path, db_path: Path):
    service.run_backup(_config(), photos_root, db_path)
    service.run_backup(_config(), photos_root, db_path)

    manifest = mount_path / service.BACKUP_DIRNAME / service.MANIFEST_NAME
    lines = manifest.read_text("utf-8").strip().splitlines()
    assert len(lines) == 2
    entry = json.loads(lines[0])
    assert entry["files_copied"] == 2
    assert entry["db_backed_up"] is True
    assert "timestamp" in entry
