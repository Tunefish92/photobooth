from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class PrinterBackend(ABC):
    @abstractmethod
    def print_file(self, image_path: Path) -> None: ...


class PrinterError(RuntimeError):
    pass
