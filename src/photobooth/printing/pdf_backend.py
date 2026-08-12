"""Debug/no-printer fallback: renders the print job to a PDF file instead."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class PdfPrinterBackend:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def print_file(self, image_path: Path) -> None:
        out = self._output_dir / f"{image_path.stem}.pdf"
        Image.open(image_path).convert("RGB").save(out, "PDF")
        logger.info("Wrote debug print PDF to %s", out)
