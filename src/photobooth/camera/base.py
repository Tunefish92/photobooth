"""Common interface all camera backends implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self


@dataclass(slots=True)
class Frame:
    """A single preview frame, ready to hand to Qt."""

    rgb_bytes: bytes
    width: int
    height: int


@dataclass(slots=True)
class Capture:
    """A full-resolution still, exactly as produced by the camera.

    `data` is written to disk byte-for-byte -- backends must not recompress
    or otherwise transform what the camera hardware/driver returned.
    """

    data: bytes
    extension: str  # e.g. "jpg"


class CameraBackend(ABC):
    """Lifecycle: `open()` once, repeated `preview_frame()`/`capture()`, `close()` once."""

    name: str = "base"

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def has_preview(self) -> bool: ...

    def preview_frame(self) -> Frame | None:
        """Return the latest low-latency preview frame, or None if unavailable."""
        return None

    @abstractmethod
    def capture(self) -> Capture:
        """Trigger a full-resolution still capture and return the original bytes."""
        ...

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class CameraUnavailableError(RuntimeError):
    """Raised when a backend's hardware/driver dependency can't be reached."""
