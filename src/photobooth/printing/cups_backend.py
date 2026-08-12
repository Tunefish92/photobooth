"""Prints via CUPS -- targets a Canon SELPHY CP1300 by default.

The Pi-side setup installs the printer in CUPS using the bundled
`supplementals/Canon_SELPHY_CP1300.ppd` (carried over from the old project);
this backend just submits jobs to whatever CUPS queue name is configured.
"""

from __future__ import annotations

import logging
from pathlib import Path

from photobooth.config.settings import PrinterConfig
from photobooth.printing.base import PrinterBackend, PrinterError

logger = logging.getLogger(__name__)


class CupsPrinterBackend(PrinterBackend):
    def __init__(self, config: PrinterConfig) -> None:
        try:
            import cups
        except ImportError as exc:
            raise PrinterError("pycups is not available (Linux/CUPS only)") from exc

        self._cups = cups
        self._config = config
        self._conn = cups.Connection()

    def print_file(self, image_path: Path) -> None:
        printers = self._conn.getPrinters()
        name = self._config.cups_printer_name
        if name not in printers:
            raise PrinterError(f"CUPS printer {name!r} not found (known: {list(printers)})")

        options = {
            "fit-to-page": "True",
            "media": f"Custom.{self._config.paper_width_mm}x{self._config.paper_height_mm}mm",
        }
        job_id = self._conn.printFile(name, str(image_path), "Photobooth", options)
        logger.info("Submitted print job %s to %s", job_id, name)
