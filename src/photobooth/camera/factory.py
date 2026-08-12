"""Picks a camera backend from config, with graceful fallback to Dummy.

Real backends (gphoto2/picamera2/opencv) are imported lazily so this module
works even before those files exist yet / on platforms missing their native
deps (e.g. developing the UI on Windows) -- any import or hardware-probe
failure just falls through to the next candidate.
"""

from __future__ import annotations

import logging

from photobooth.camera.base import CameraBackend, CameraUnavailableError
from photobooth.camera.dummy_backend import DummyBackend
from photobooth.config.settings import CameraBackendName

logger = logging.getLogger(__name__)

_AUTO_PROBE_ORDER: tuple[CameraBackendName, ...] = ("gphoto2", "picamera2", "opencv")


def _build(name: CameraBackendName, opencv_device_index: int) -> CameraBackend:
    if name == "gphoto2":
        from photobooth.camera.gphoto2_backend import Gphoto2Backend

        return Gphoto2Backend()
    if name == "picamera2":
        from photobooth.camera.picamera2_backend import Picamera2Backend

        return Picamera2Backend()
    if name == "opencv":
        from photobooth.camera.opencv_backend import OpenCVBackend

        return OpenCVBackend(device_index=opencv_device_index)
    if name == "dummy":
        return DummyBackend()
    raise ValueError(f"Unknown camera backend {name!r}")


def create_camera_backend(
    backend: CameraBackendName, opencv_device_index: int = 0
) -> CameraBackend:
    if backend != "auto":
        try:
            candidate = _build(backend, opencv_device_index)
            candidate.open()
            return candidate
        except (ImportError, CameraUnavailableError, OSError, ValueError) as exc:
            # ValueError covers an unrecognized backend name -- normally
            # impossible since CameraBackendName is a pydantic Literal, but
            # this is the last line of defense before camera init, so an
            # unexpected value here should degrade to the dummy backend
            # rather than take the whole app down.
            logger.warning("Camera backend %r unavailable (%s); falling back to dummy", backend, exc)
            return DummyBackend()

    for name in _AUTO_PROBE_ORDER:
        try:
            candidate = _build(name, opencv_device_index)
            candidate.open()
            logger.info("Auto-selected camera backend: %s", name)
            return candidate
        except (ImportError, CameraUnavailableError, OSError, ValueError) as exc:
            logger.debug("Camera backend %r not available (%s)", name, exc)

    logger.info("No hardware camera detected; using dummy backend")
    return DummyBackend()
