"""system_clock.set_system_datetime() -- Linux/timedatectl only, mocked
here rather than needing a real Pi (same approach as test_updater.py's
subprocess mocking).
"""

from __future__ import annotations

import subprocess
from datetime import datetime

import pytest

from photobooth import system_clock


def test_set_system_datetime_raises_on_non_linux(monkeypatch):
    monkeypatch.setattr(system_clock.sys, "platform", "win32")
    with pytest.raises(system_clock.SystemClockUnavailableError, match="Linux"):
        system_clock.set_system_datetime(datetime(2026, 8, 24, 12, 0, 0))


def test_set_system_datetime_disables_ntp_then_sets_the_clock(monkeypatch):
    monkeypatch.setattr(system_clock.sys, "platform", "linux")
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, timeout):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    system_clock.set_system_datetime(datetime(2026, 8, 24, 12, 34, 56))

    assert calls == [
        ["timedatectl", "set-ntp", "false"],
        ["timedatectl", "set-time", "2026-08-24 12:34:56"],
    ]


def test_set_system_datetime_raises_with_stderr_on_failure(monkeypatch):
    monkeypatch.setattr(system_clock.sys, "platform", "linux")

    def fake_run(command, capture_output, text, timeout):
        if command[1] == "set-time":
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="Automatic time synchronization is enabled")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(system_clock.SystemClockUnavailableError, match="Automatic time synchronization"):
        system_clock.set_system_datetime(datetime(2026, 8, 24, 12, 0, 0))
