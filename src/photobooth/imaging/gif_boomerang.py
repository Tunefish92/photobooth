"""Animated results for the "gif" and "boomerang" capture modes.

Both are encoded as animated GIF rather than video: it keeps the dependency
footprint small (no ffmpeg/codec needs on the Pi), the files are tiny at
photobooth burst lengths, and every share channel (email, USB, on-screen
preview) can play a GIF with zero extra tooling.
"""

from __future__ import annotations

import io

from PIL import Image


def make_gif(images: list[Image.Image], frame_duration_ms: int = 150) -> bytes:
    if not images:
        raise ValueError("Need at least one frame")
    buf = io.BytesIO()
    frames = [img.convert("RGB") for img in images]
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration_ms,
        loop=0,
    )
    return buf.getvalue()


def make_boomerang(images: list[Image.Image], frame_duration_ms: int = 80) -> bytes:
    """Plays the burst forward then back, the classic boomerang loop."""
    if not images:
        raise ValueError("Need at least one frame")
    sequence = images + images[-2:0:-1] if len(images) > 1 else images
    return make_gif(sequence, frame_duration_ms)
