import pytest
from PIL import Image

from photobooth.config.settings import LayoutConfig
from photobooth.imaging.compositor import compose_grid, compute_layout


def make_layout(**overrides):
    fields = {
        "num_x": 2,
        "num_y": 2,
        "size_x": 1000,
        "size_y": 1000,
        "inner_dist_x": 10,
        "inner_dist_y": 10,
        "outer_dist_x": 20,
        "outer_dist_y": 20,
    }
    fields.update(overrides)
    return LayoutConfig(**fields)


def test_compute_layout_fills_all_slots_without_skip():
    layout = compute_layout((400, 400), make_layout())
    assert len(layout.offsets) == 4
    assert layout.output_size == (1000, 1000)
    # thumbnails must fit within the canvas
    for _, (x, y) in layout.offsets:
        assert 0 <= x <= layout.output_size[0] - layout.thumb_size[0]
        assert 0 <= y <= layout.output_size[1] - layout.thumb_size[1]


def test_compute_layout_respects_skip():
    layout = compute_layout((400, 400), make_layout(skip=[1]))
    assert len(layout.offsets) == 3
    assert all(idx != 0 for idx, _ in layout.offsets)


def test_compose_grid_produces_requested_output_size():
    images = [Image.new("RGB", (400, 400), color) for color in ["red", "green", "blue", "yellow"]]
    composed = compose_grid(images, make_layout())
    assert composed.size == (1000, 1000)


def test_compose_grid_single_image_1x1():
    layout = make_layout(num_x=1, num_y=1)
    images = [Image.new("RGB", (400, 600), "red")]
    composed = compose_grid(images, layout)
    assert composed.size == (1000, 1000)


def test_compose_grid_requires_at_least_one_image():
    with pytest.raises(ValueError):
        compose_grid([], make_layout())


def test_compute_layout_zero_margin_fills_edge_to_edge():
    """Settings UI now exposes a single "Margin (px)" field driving both
    inner_dist and outer_dist uniformly -- 0 is a valid, reachable value and
    should give a tightly packed grid with no gaps, not break the math."""
    layout = compute_layout((400, 400), make_layout(inner_dist_x=0, inner_dist_y=0, outer_dist_x=0, outer_dist_y=0))
    assert len(layout.offsets) == 4
    xs = sorted({x for _, (x, _y) in layout.offsets})
    assert xs[0] == 0  # first column flush against the canvas edge


def test_compute_layout_symmetric_margin_produces_symmetric_gaps():
    """The UI's "Margin (px)" field sets inner_dist == outer_dist; the
    resulting grid should be symmetric left/right and top/bottom.

    Uses inner=outer=20 against a 1000px canvas specifically because it
    divides evenly (no leftover pixel from the gap's integer rounding) --
    see `test_compute_layout_zero_margin_fills_edge_to_edge` for a case that
    doesn't need exact divisibility.
    """
    layout = compute_layout((400, 400), make_layout(inner_dist_x=20, inner_dist_y=20, outer_dist_x=20, outer_dist_y=20))
    xs = sorted({x for _, (x, _y) in layout.offsets})
    right_edge = layout.output_size[0] - (xs[-1] + layout.thumb_size[0])
    assert xs[0] == right_edge  # left margin == right margin


def test_compute_layout_raises_when_margin_leaves_no_room_for_photos():
    """A margin large enough (relative to output size) that the resize
    factor goes non-positive must fail with a clear error instead of PIL
    raising an opaque "width and height must be > 0" deep inside resize()."""
    with pytest.raises(ValueError, match="no room for photos"):
        compute_layout((400, 400), make_layout(size_x=200, size_y=200, inner_dist_x=70, inner_dist_y=70, outer_dist_x=70, outer_dist_y=70))


def test_compose_grid_missing_background_path_falls_back_to_white_canvas(tmp_path):
    """A configured background path that doesn't exist on disk (e.g. the
    file was moved/deleted after being set) must not crash the whole
    postprocess step -- silently fall back to a blank white canvas."""
    images = [Image.new("RGB", (400, 400), color) for color in ["red", "green", "blue", "yellow"]]
    missing_bg = tmp_path / "does-not-exist.png"

    composed = compose_grid(images, make_layout(), background=missing_bg)

    assert composed.size == (1000, 1000)
    corner = composed.getpixel((1, 1))
    assert corner == (255, 255, 255)


def test_compose_grid_missing_overlay_path_is_skipped(tmp_path):
    images = [Image.new("RGB", (400, 400), color) for color in ["red", "green", "blue", "yellow"]]
    missing_overlay = tmp_path / "does-not-exist.png"

    composed = compose_grid(images, make_layout(), overlay=missing_overlay)

    assert composed.size == (1000, 1000)
    assert composed.mode == "RGB"


def test_compose_grid_uses_real_background_image(tmp_path):
    bg_path = tmp_path / "bg.png"
    Image.new("RGB", (50, 50), (10, 20, 30)).save(bg_path)
    images = [Image.new("RGB", (400, 400), "red")]
    layout = make_layout(num_x=1, num_y=1)

    composed = compose_grid(images, layout, background=bg_path)

    # a corner far from the (centered) thumbnail should still show the
    # background color, scaled up to the output size
    assert composed.getpixel((1, 1)) == (10, 20, 30)
