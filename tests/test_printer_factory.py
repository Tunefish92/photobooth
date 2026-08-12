from pathlib import Path

from photobooth.config.settings import PrinterConfig
from photobooth.printing.factory import create_printer_backend
from photobooth.printing.pdf_backend import PdfPrinterBackend


def test_pdf_backend_selected_explicitly(tmp_path: Path):
    backend = create_printer_backend(PrinterConfig(backend="pdf"), tmp_path)
    assert isinstance(backend, PdfPrinterBackend)


def test_cups_backend_falls_back_to_pdf_when_pycups_unavailable(tmp_path: Path):
    """pycups isn't installed on this dev machine, so requesting the cups
    backend must fall back to the PDF backend rather than raise -- exercises
    the real ImportError path (see CupsPrinterBackend.__init__) without
    mocking."""
    backend = create_printer_backend(PrinterConfig(backend="cups"), tmp_path)
    assert isinstance(backend, PdfPrinterBackend)


def test_pdf_backend_writes_a_pdf_file(tmp_path: Path):
    from PIL import Image

    src = tmp_path / "photo.jpg"
    Image.new("RGB", (100, 100), "red").save(src)

    backend = PdfPrinterBackend(tmp_path / "out")
    backend.print_file(src)

    assert (tmp_path / "out" / "photo.pdf").is_file()
