"""Fire a blocking call (SMTP, WebDAV upload, USB copy, CUPS submit, ...) on
the shared Qt thread pool and marshal the result back to the caller's thread
via signals, so the UI thread never stalls on network/disk I/O.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _TaskSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class _Task(QRunnable):
    def __init__(self, fn: Callable[..., Any], args: tuple, kwargs: dict) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.signals = _TaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, not swallowed
            self.signals.failed.emit(str(exc))
        else:
            self.signals.finished.emit(result)


def run_in_background(
    fn: Callable[..., Any],
    *args: Any,
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[str], None] | None = None,
    **kwargs: Any,
) -> None:
    task = _Task(fn, args, kwargs)
    if on_success is not None:
        task.signals.finished.connect(on_success)
    if on_error is not None:
        task.signals.failed.connect(on_error)
    QThreadPool.globalInstance().start(task)
