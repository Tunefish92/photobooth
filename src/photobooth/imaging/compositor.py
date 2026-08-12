"""Assembles captured shots into the final m-by-n grid picture.

Reimplements the layout math from the old app's `PictureDimensions`: a single
resize factor is computed so all thumbnails share size, are evenly spaced by
`inner_dist`, and are inset from the canvas edge by `outer_dist`. Slots listed
in `skip` (1-indexed, row-major) are left empty -- handy for compositing a
logo directly into the background image at that slot.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from photobooth.config.settings import LayoutConfig


@dataclass(slots=True)
class GridLayout:
    num_x: int
    num_y: int
    output_size: tuple[int, int]
    thumb_size: tuple[int, int]
    # (slot_index, (x, y)) for every slot that isn't skipped, in row-major order
    offsets: list[tuple[int, tuple[int, int]]]


def compute_layout(capture_size: tuple[int, int], config: LayoutConfig) -> GridLayout:
    num = (config.num_x, config.num_y)
    output_size = (config.size_x, config.size_y)
    inner = (config.inner_dist_x, config.inner_dist_y)
    outer = (config.outer_dist_x, config.outer_dist_y)
    skip = set(config.skip)

    border = tuple(outer[i] - inner[i] for i in range(2))
    inner_size = tuple(output_size[i] - 2 * border[i] for i in range(2))

    def resize_factor(i: int) -> float:
        return (inner_size[i] - (num[i] + 1) * inner[i]) / (num[i] * capture_size[i])

    factor = min(resize_factor(0), resize_factor(1))
    if factor <= 0:
        raise ValueError(
            "Layout margins leave no room for photos: increase size_x/size_y "
            "or decrease the margin"
        )
    thumb_size = (int(capture_size[0] * factor), int(capture_size[1] * factor))

    def thumb_gap(i: int) -> int:
        return (inner_size[i] - num[i] * thumb_size[i]) // (num[i] + 1)

    gap = (thumb_gap(0), thumb_gap(1))

    offsets: list[tuple[int, tuple[int, int]]] = []
    for idx in range(num[0] * num[1]):
        if idx + 1 in skip:
            continue
        pos = (idx % num[0], idx // num[0])
        xy = tuple(
            border[j] + (pos[j] + 1) * gap[j] + pos[j] * thumb_size[j] for j in range(2)
        )
        offsets.append((idx, xy))

    return GridLayout(
        num_x=num[0], num_y=num[1], output_size=output_size, thumb_size=thumb_size,
        offsets=offsets,
    )


def compose_grid(
    images: list[Image.Image],
    config: LayoutConfig,
    background: Path | None = None,
    overlay: Path | None = None,
) -> Image.Image:
    if not images:
        raise ValueError("Need at least one image to compose")

    layout = compute_layout(images[0].size, config)

    if background and background.is_file():
        canvas = Image.open(background).convert("RGB").resize(layout.output_size)
    else:
        canvas = Image.new("RGB", layout.output_size, (255, 255, 255))

    for image, (_, xy) in zip(images, layout.offsets, strict=False):
        thumb = image.resize(layout.thumb_size, Image.LANCZOS)
        canvas.paste(thumb, xy)

    if overlay and overlay.is_file():
        overlay_img = Image.open(overlay).convert("RGBA").resize(layout.output_size)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay_img).convert("RGB")

    return canvas
