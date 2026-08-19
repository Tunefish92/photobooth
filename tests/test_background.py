"""Regression coverage for photobooth.bridge.background.run_in_background.

A prior version let the in-flight _Task (and its signals QObject) fall out
of scope the instant run_in_background() returned, with nothing else
holding a Python reference to it while the QThreadPool worker ran -- it
could be garbage-collected before the finished/failed signal was delivered,
silently dropping on_success/on_error (observed live as: print "Yes" ->
postprocessBusy stuck True forever, no toast, and on a bad day a crash from
the worker thread touching a half-deleted QObject). These tests drive the
real QThreadPool + signal round trip end to end, not a mock.
"""

from __future__ import annotations

import gc
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from photobooth.bridge.background import run_in_background  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


def _pump(seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


def test_on_success_fires_even_after_a_gc_pass_before_the_task_finishes(qapp):
    results: list[object] = []
    run_in_background(lambda: (time.sleep(0.1), "ok")[1], on_success=results.append)

    # Force a collection while the worker thread is still running, to
    # catch exactly the premature-GC bug this module guards against --
    # nothing but run_in_background()'s own bookkeeping should be keeping
    # the task alive at this point.
    gc.collect()
    _pump(2.0)

    assert results == ["ok"]


def test_on_error_fires_for_a_raising_background_function(qapp):
    def boom():
        raise ValueError("simulated failure")

    results: list[str] = []
    run_in_background(boom, on_error=results.append)
    _pump(2.0)

    assert results == ["simulated failure"]


def test_many_concurrent_tasks_each_deliver_their_own_result(qapp):
    results: dict[int, int] = {}
    for i in range(20):
        run_in_background(lambda n=i: n * n, on_success=lambda r, n=i: results.__setitem__(n, r))
    _pump(3.0)

    assert results == {i: i * i for i in range(20)}
