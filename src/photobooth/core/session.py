"""A single photobooth capture session (one "trip" through the booth)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from photobooth.config.settings import CaptureMode, FilterName

# Shot counts for the "burst" modes; "grid" instead derives its count from
# the configured layout.num_x * layout.num_y (whatever grid shape is set up).
FIXED_SHOT_COUNTS: dict[str, int] = {
    "single": 1,
    "gif": 6,
    "boomerang": 12,
}


@dataclass(slots=True)
class CaptureSession:
    mode: CaptureMode
    target_shot_count: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: datetime = field(default_factory=datetime.now)
    filter_name: FilterName = "none"
    shots: list[Path] = field(default_factory=list)
    result_path: Path | None = None

    @property
    def shots_remaining(self) -> int:
        return max(0, self.target_shot_count - len(self.shots))

    @property
    def is_complete(self) -> bool:
        return len(self.shots) >= self.target_shot_count

    def add_shot(self, path: Path) -> None:
        self.shots.append(path)

    def reset_shots(self) -> None:
        self.shots.clear()
        self.result_path = None


def shot_count_for_mode(mode: CaptureMode, num_x: int, num_y: int) -> int:
    if mode == "grid":
        return max(1, num_x * num_y)
    return FIXED_SHOT_COUNTS[mode]
