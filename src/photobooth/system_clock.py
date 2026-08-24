"""Reads/sets the kiosk's system clock via systemd's `timedatectl`.

Linux only -- there's no equivalent on the Windows dev machine, where this
just raises. Setting the time works *without* a password prompt because
systemd-timedated's shipped polkit policy grants the
`org.freedesktop.timedate1.set-time`/`set-ntp` actions to any user with an
active local session (`allow_active: yes`), which is exactly what the
kiosk's auto-login desktop session is -- see
`/usr/share/polkit-1/actions/org.freedesktop.timedate1.policy`.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime

_SUBPROCESS_TIMEOUT_S = 10


class SystemClockUnavailableError(RuntimeError):
    """Raised when the system clock can't be read/set on this platform."""


def _run(command: list[str]) -> None:
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT_S
    )
    if result.returncode != 0:
        raise SystemClockUnavailableError(
            f"{' '.join(command)!r} failed (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def set_system_datetime(value: datetime) -> None:
    """Turns NTP sync off first -- `timedatectl set-time` refuses to change
    the clock while automatic sync is active -- then sets it. Leaves NTP
    off afterward: a manual correction means the guest doesn't trust (or
    doesn't have) reliable network time, and re-enabling it would silently
    overwrite what was just set the next time it syncs.
    """
    if sys.platform != "linux":
        raise SystemClockUnavailableError(
            "Setting the system clock is only supported on the Pi (Linux)"
        )
    _run(["timedatectl", "set-ntp", "false"])
    _run(["timedatectl", "set-time", value.strftime("%Y-%m-%d %H:%M:%S")])
