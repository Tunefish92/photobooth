"""Decides where session photos live on disk and writes them there."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from photobooth.config.settings import StorageConfig
from photobooth.core.session import CaptureSession


class SessionStore:
    def __init__(self, photos_root: Path, config: StorageConfig) -> None:
        self._root = photos_root
        self._config = config

    def _day_dir(self) -> Path:
        sub = datetime.now().strftime(self._config.basedir)
        path = self._root / sub
        path.mkdir(parents=True, exist_ok=True)
        return path

    def shot_path(self, session: CaptureSession, index: int, extension: str) -> Path:
        name = f"{self._config.basename}_{session.id}_{index:02d}.{extension}"
        return self._day_dir() / name

    def result_path(self, session: CaptureSession, extension: str = "jpg") -> Path:
        name = f"{self._config.basename}_{session.id}.{extension}"
        return self._day_dir() / name

    def write(self, path: Path, data: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    @property
    def keep_individual_shots(self) -> bool:
        return self._config.keep_pictures
