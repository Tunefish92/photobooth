"""Green-screen background replacement."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def apply_chroma_key(
    image: Image.Image,
    background: Image.Image,
    key_color_rgb: tuple[int, int, int],
    tolerance: int = 40,
    softness: int = 15,
) -> Image.Image:
    """Replace pixels near `key_color_rgb` with the matching region of `background`."""
    fg = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    bg = cv2.cvtColor(
        np.asarray(background.convert("RGB").resize(image.size)), cv2.COLOR_RGB2BGR
    )

    key_bgr = np.uint8([[list(reversed(key_color_rgb))]])
    key_hsv = cv2.cvtColor(key_bgr, cv2.COLOR_BGR2HSV)[0, 0]

    fg_hsv = cv2.cvtColor(fg, cv2.COLOR_BGR2HSV)
    lower = np.array(
        [max(int(key_hsv[0]) - tolerance, 0), 60, 40], dtype=np.uint8
    )
    upper = np.array(
        [min(int(key_hsv[0]) + tolerance, 179), 255, 255], dtype=np.uint8
    )
    mask = cv2.inRange(fg_hsv, lower, upper)

    if softness > 0:
        k = softness | 1  # odd kernel size
        mask = cv2.GaussianBlur(mask, (k, k), 0)

    alpha = (mask.astype(np.float32) / 255.0)[..., None]
    composite = fg.astype(np.float32) * (1 - alpha) + bg.astype(np.float32) * alpha
    composite = cv2.cvtColor(composite.astype(np.uint8), cv2.COLOR_BGR2RGB)
    return Image.fromarray(composite)
