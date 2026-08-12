from __future__ import annotations

import logging
from pathlib import Path

from photobooth.config.settings import PrinterConfig
from photobooth.printing.base import PrinterBackend, PrinterError
from photobooth.printing.pdf_backend import PdfPrinterBackend

logger = logging.getLogger(__name__)


def create_printer_backend(config: PrinterConfig, pdf_output_dir: Path) -> PrinterBackend:
    if config.backend == "cups":
        try:
            from photobooth.printing.cups_backend import CupsPrinterBackend

            return CupsPrinterBackend(config)
        except PrinterError as exc:
            logger.warning("CUPS unavailable (%s); falling back to PDF backend", exc)
    return PdfPrinterBackend(pdf_output_dir)
