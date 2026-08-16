"""Detects removable USB storage and resolves a stable filesystem UUID for
each one, so a backup device chosen in Settings survives a replug or a
reboot even though its mount path is label-derived (Raspberry Pi OS mounts
under /media/<user>/<label>, so the path itself changes with the label,
the USB port, or whatever else got plugged in first) and would otherwise
be a fragile thing to remember.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

# Module-level so tests can monkeypatch them by name rather than needing a
# real /proc, /dev, /media on whatever machine runs the suite.
_MEDIA_ROOTS = (Path("/media"), Path("/run/media"))
_PROC_MOUNTS = Path("/proc/mounts")
_BY_UUID_DIR = Path("/dev/disk/by-uuid")


@dataclass(slots=True, frozen=True)
class RemovableDevice:
    uuid: str
    label: str
    mount_path: Path


def _read_proc_mounts() -> dict[str, str]:
    """{mount_point: device_node} from /proc/mounts."""
    try:
        text = _PROC_MOUNTS.read_text("utf-8")
    except OSError:
        return {}
    entries: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            entries[parts[1]] = parts[0]
    return entries


def _uuid_for_device_node(device_node: str) -> str:
    """Reverse-looks-up /dev/disk/by-uuid/* symlinks to find the one
    pointing at `device_node` (e.g. "/dev/sda1")."""
    if not _BY_UUID_DIR.is_dir():
        return ""
    try:
        target = Path(device_node).resolve()
    except OSError:
        return ""
    for entry in _BY_UUID_DIR.iterdir():
        try:
            if entry.resolve() == target:
                return entry.name
        except OSError:
            continue
    return ""


def find_removable_devices() -> list[RemovableDevice]:
    """Currently-mounted removable drives with a resolvable UUID.
    Raspberry Pi OS auto-mounts USB storage under /media/<user>/<label>
    (or /run/media on some setups); a mount with no UUID (e.g. something
    that isn't a real partition) is skipped, since a backup device has to
    be re-identifiable later. Linux-only, like the rest of this app's
    hardware integrations -- returns [] elsewhere rather than failing.
    """
    if not sys.platform.startswith("linux"):
        return []

    mount_points: list[Path] = []
    for base in _MEDIA_ROOTS:
        if not base.is_dir():
            continue
        for user_dir in base.iterdir():
            if user_dir.is_dir():
                mount_points.extend(p for p in user_dir.iterdir() if p.is_dir())

    device_nodes = _read_proc_mounts()
    devices: list[RemovableDevice] = []
    for mount_path in mount_points:
        device_node = device_nodes.get(str(mount_path))
        if not device_node:
            continue
        uuid = _uuid_for_device_node(device_node)
        if not uuid:
            continue
        devices.append(RemovableDevice(uuid=uuid, label=mount_path.name, mount_path=mount_path))
    return devices


def resolve_mount_path(uuid: str) -> Path | None:
    """Where the device with this UUID is currently mounted, or None if
    it isn't plugged in (or mounted) right now."""
    if not uuid:
        return None
    for device in find_removable_devices():
        if device.uuid == uuid:
            return device.mount_path
    return None
