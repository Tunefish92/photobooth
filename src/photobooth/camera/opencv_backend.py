"""USB/UVC webcam backend via OpenCV. Cross-platform (works for dev on Windows too)."""

from __future__ import annotations

import io
import sys

from PIL import Image

from photobooth.camera.base import CameraBackend, CameraUnavailableError, Capture, Frame

# Ask for a high resolution at open time; OpenCV/the driver clamps to whatever
# the device actually supports, so this is a "give me your best" request, not
# a guarantee -- the negotiated size is read back afterwards.
_REQUESTED_WIDTH = 3840
_REQUESTED_HEIGHT = 2160


class OpenCVBackend(CameraBackend):
    name = "opencv"

    def __init__(self, device_index: int = 0) -> None:
        self._device_index = device_index
        self._cap = None
        self._cv2 = None

    def open(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise CameraUnavailableError("opencv-python is not installed") from exc

        api = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self._device_index, api)
        if not cap.isOpened():
            raise CameraUnavailableError(f"No webcam found at index {self._device_index}")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, _REQUESTED_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, _REQUESTED_HEIGHT)

        self._cv2 = cv2
        self._cap = cap

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def has_preview(self) -> bool:
        return True

    def _read_rgb(self):
        assert self._cap is not None and self._cv2 is not None
        ok, frame_bgr = self._cap.read()
        if not ok:
            return None
        return self._cv2.cvtColor(frame_bgr, self._cv2.COLOR_BGR2RGB)

    def preview_frame(self) -> Frame | None:
        rgb = self._read_rgb()
        if rgb is None:
            return None
        height, width = rgb.shape[:2]
        return Frame(rgb_bytes=rgb.tobytes(), width=width, height=height)

    def capture(self) -> Capture:
        rgb = self._read_rgb()
        if rgb is None:
            raise CameraUnavailableError("Failed to read a frame from the webcam")
        image = Image.fromarray(rgb)
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=95)
        return Capture(data=buf.getvalue(), extension="jpg")
