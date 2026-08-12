"""Runs the camera backend on a dedicated QThread.

DSLR capture (gphoto2) can take a second or more, and even preview polling
should never risk a dropped frame stalling the UI thread -- so all backend
I/O happens here, and results cross back to the GUI thread purely via
queued Qt signals.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage

from photobooth.camera.base import CameraBackend

logger = logging.getLogger(__name__)

_PREVIEW_INTERVAL_MS = 66  # ~15 fps, plenty smooth for a countdown preview


class CameraWorker(QObject):
    frame_ready = Signal(QImage)
    capture_ready = Signal(bytes, str)
    capture_failed = Signal(str)
    ready = Signal(bool)  # True if a real camera was found, False if dummy fallback

    def __init__(self, backend_factory: Callable[[], CameraBackend]) -> None:
        super().__init__()
        self._backend_factory = backend_factory
        self._backend: CameraBackend | None = None
        self._timer: QTimer | None = None

    @Slot()
    def start(self) -> None:
        self._backend = self._backend_factory()
        self.ready.emit(self._backend.name != "dummy")
        self._timer = QTimer()
        self._timer.setInterval(_PREVIEW_INTERVAL_MS)
        self._timer.timeout.connect(self._emit_preview)
        if self._backend.has_preview:
            self._timer.start()

    @Slot()
    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        if self._backend is not None:
            self._backend.close()

    def _emit_preview(self) -> None:
        assert self._backend is not None
        try:
            frame = self._backend.preview_frame()
        except Exception:
            logger.exception("Preview frame failed")
            return
        if frame is None:
            return
        image = QImage(
            frame.rgb_bytes, frame.width, frame.height, QImage.Format.Format_RGB888
        ).copy()
        self.frame_ready.emit(image)

    @Slot()
    def do_capture(self) -> None:
        assert self._backend is not None
        was_running = self._timer is not None and self._timer.isActive()
        if self._timer is not None:
            self._timer.stop()
        try:
            capture = self._backend.capture()
            self.capture_ready.emit(capture.data, capture.extension)
        except Exception as exc:
            logger.exception("Capture failed")
            self.capture_failed.emit(str(exc))
        finally:
            if was_running and self._timer is not None:
                self._timer.start()
