"""Raspberry Pi Camera Module backend via picamera2/libcamera.

Linux/RPi only -- `picamera2` is normally installed as a system package
(`apt install python3-picamera2`) since it links against libcamera, so the
venv needs `--system-site-packages` on the Pi (see scripts/install.sh).
"""

from __future__ import annotations

import io

import numpy as np

from photobooth.camera.base import CameraBackend, CameraUnavailableError, Capture, Frame

_PREVIEW_SIZE = (1024, 768)


class Picamera2Backend(CameraBackend):
    name = "picamera2"

    def __init__(self) -> None:
        self._cam = None
        self._still_config = None

    def open(self) -> None:
        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise CameraUnavailableError("picamera2 is not installed (Raspberry Pi only)") from exc

        try:
            cam = Picamera2()
            preview_config = cam.create_preview_configuration(
                main={"size": _PREVIEW_SIZE, "format": "RGB888"}
            )
            still_config = cam.create_still_configuration()
            cam.configure(preview_config)
            cam.start()
        except Exception as exc:  # picamera2 raises plain RuntimeError/IndexError if no sensor
            raise CameraUnavailableError(f"No Pi camera detected: {exc}") from exc

        self._cam = cam
        self._still_config = still_config

    def close(self) -> None:
        if self._cam is not None:
            self._cam.stop()
            self._cam.close()
            self._cam = None

    @property
    def has_preview(self) -> bool:
        return True

    def preview_frame(self) -> Frame | None:
        assert self._cam is not None
        # NOTE (verify on hardware): picamera2's "RGB888" format name is
        # documented as true R,G,B channel order for capture_array(); if a
        # real Pi Camera Module shows a blue/red-swapped preview, swap this
        # to array[:, :, ::-1] and file that as a one-line fix.
        array = self._cam.capture_array("main")
        array = np.ascontiguousarray(array[:, :, :3])
        height, width = array.shape[:2]
        return Frame(rgb_bytes=array.tobytes(), width=width, height=height)

    def capture(self) -> Capture:
        assert self._cam is not None and self._still_config is not None
        buf = io.BytesIO()
        self._cam.switch_mode_and_capture_file(self._still_config, buf, format="jpeg")
        return Capture(data=buf.getvalue(), extension="jpg")
