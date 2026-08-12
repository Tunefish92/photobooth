"""Synthetic camera backend used for development off the Pi and in tests."""

from __future__ import annotations

import io
import time
from datetime import datetime

from PIL import Image, ImageDraw

from photobooth.camera.base import CameraBackend, Capture, Frame

_PREVIEW_SIZE = (960, 640)
_CAPTURE_SIZE = (3888, 2592)  # matches the EOS 1000D's native JPEG resolution


def _colorwheel(t: float) -> tuple[int, int, int]:
    import colorsys

    r, g, b = colorsys.hsv_to_rgb((t % 6.0) / 6.0, 0.55, 0.95)
    return int(r * 255), int(g * 255), int(b * 255)


class DummyBackend(CameraBackend):
    name = "dummy"

    def __init__(self) -> None:
        self._open = False
        self._start = time.monotonic()

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    @property
    def has_preview(self) -> bool:
        return True

    def _render(self, size: tuple[int, int], caption: str) -> Image.Image:
        color = _colorwheel(time.monotonic() - self._start)
        img = Image.new("RGB", size, color)
        draw = ImageDraw.Draw(img)
        text = f"{caption}\n{datetime.now():%H:%M:%S}"
        draw.text((size[0] * 0.05, size[1] * 0.45), text, fill=(255, 255, 255))
        return img

    def preview_frame(self) -> Frame | None:
        img = self._render(_PREVIEW_SIZE, "DUMMY CAMERA")
        return Frame(rgb_bytes=img.tobytes(), width=img.width, height=img.height)

    def capture(self) -> Capture:
        img = self._render(_CAPTURE_SIZE, "DUMMY CAPTURE")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return Capture(data=buf.getvalue(), extension="jpg")
