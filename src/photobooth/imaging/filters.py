"""Lightweight, dependency-cheap photo filters applied before compositing."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from photobooth.config.settings import FilterName

_SEPIA_MATRIX = np.array(
    [
        [0.393, 0.769, 0.189],
        [0.349, 0.686, 0.168],
        [0.272, 0.534, 0.131],
    ]
)


def _none(img: Image.Image) -> Image.Image:
    return img


def _bw(img: Image.Image) -> Image.Image:
    return ImageOps.grayscale(img).convert("RGB")


def _sepia(img: Image.Image) -> Image.Image:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    toned = arr @ _SEPIA_MATRIX.T
    return Image.fromarray(np.clip(toned, 0, 255).astype(np.uint8))


def _vintage(img: Image.Image) -> Image.Image:
    faded = ImageEnhance.Color(img).enhance(0.7)
    faded = ImageEnhance.Contrast(faded).enhance(0.85)
    faded = ImageEnhance.Brightness(faded).enhance(1.05)
    arr = np.asarray(faded.convert("RGB"), dtype=np.float32)
    arr[..., 0] = np.clip(arr[..., 0] * 1.08, 0, 255)  # warm the shadows/highlights slightly
    arr[..., 2] = np.clip(arr[..., 2] * 0.92, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def _vivid(img: Image.Image) -> Image.Image:
    vivid = ImageEnhance.Color(img).enhance(1.45)
    vivid = ImageEnhance.Contrast(vivid).enhance(1.15)
    return ImageEnhance.Sharpness(vivid).enhance(1.2)


_FILTERS: dict[FilterName, Callable[[Image.Image], Image.Image]] = {
    "none": _none,
    "bw": _bw,
    "sepia": _sepia,
    "vintage": _vintage,
    "vivid": _vivid,
}


def apply_filter(img: Image.Image, name: FilterName) -> Image.Image:
    return _FILTERS[name](img)
