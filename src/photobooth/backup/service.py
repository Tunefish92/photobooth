"""Copies the whole photo library and a consistent database snapshot onto
a selected backup device.

Incremental: a file already present on the device with the same size and
an mtime at least as new as the source is left alone, so repeated (and
automatic, scheduled) backups only ever copy what's actually new since
the drive was last plugged in -- important on a Pi's SD card/USB
throughput and because the whole library gets no smaller over an event.
Each run appends one line to a JSON-lines manifest on the device, a
lightweight "backup history" (timestamp + counts) without the complexity
(or FAT32/exFAT incompatibility -- most USB sticks are formatted one of
those, and neither supports hardlinks) of true per-run snapshotting.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from photobooth.backup.devices import resolve_mount_path
from photobooth.config.settings import BackupConfig

BACKUP_DIRNAME = "photobooth-backup"
MANIFEST_NAME = "backup_log.jsonl"


class BackupDeviceUnavailable(RuntimeError):
    """The configured backup device (by UUID) isn't currently plugged in
    (or isn't mounted yet -- give it a moment after inserting it)."""


@dataclass(slots=True, frozen=True)
class BackupResult:
    destination: Path
    files_copied: int
    files_skipped: int
    bytes_copied: int
    db_backed_up: bool


def _file_unchanged(src: Path, dest: Path) -> bool:
    if not dest.exists():
        return False
    src_stat = src.stat()
    dest_stat = dest.stat()
    # int()-truncated mtime comparison: FAT32 stores timestamps in 2s
    # granularity, so a straight float comparison against a Linux
    # ext4/btrfs source mtime can spuriously call an identical file
    # "changed" forever.
    return src_stat.st_size == dest_stat.st_size and int(src_stat.st_mtime) <= int(dest_stat.st_mtime)


def _copy_tree_incremental(src_root: Path, dest_root: Path) -> tuple[int, int, int]:
    copied = skipped = total_bytes = 0
    for src_file in src_root.rglob("*"):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(src_root)
        dest_file = dest_root / rel
        if _file_unchanged(src_file, dest_file):
            skipped += 1
            continue
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)
        copied += 1
        total_bytes += src_file.stat().st_size
    return copied, skipped, total_bytes


def _backup_database(db_path: Path, dest_path: Path) -> bool:
    """Uses sqlite3's own backup API rather than a plain file copy -- the
    source may be open and being written to by the running app, and a raw
    copy of a live SQLite file can land mid-write and come out corrupt."""
    if not db_path.is_file():
        return False
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(str(db_path))
    try:
        dest = sqlite3.connect(str(dest_path))
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()
    return True


def run_backup(config: BackupConfig, photos_root: Path, db_path: Path) -> BackupResult:
    mount_path = resolve_mount_path(config.device_uuid)
    if mount_path is None:
        raise BackupDeviceUnavailable(
            f"Backup device {config.device_label or config.device_uuid!r} is not plugged in"
        )

    destination = mount_path / BACKUP_DIRNAME
    destination.mkdir(parents=True, exist_ok=True)

    copied = skipped = total_bytes = 0
    if photos_root.is_dir():
        copied, skipped, total_bytes = _copy_tree_incremental(photos_root, destination / "photos")

    db_backed_up = _backup_database(db_path, destination / db_path.name)

    manifest_entry = {
        "timestamp": time.time(),
        "files_copied": copied,
        "files_skipped": skipped,
        "bytes_copied": total_bytes,
        "db_backed_up": db_backed_up,
    }
    with (destination / MANIFEST_NAME).open("a", encoding="utf-8") as f:
        f.write(json.dumps(manifest_entry) + "\n")

    return BackupResult(
        destination=destination,
        files_copied=copied,
        files_skipped=skipped,
        bytes_copied=total_bytes,
        db_backed_up=db_backed_up,
    )
