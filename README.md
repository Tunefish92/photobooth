# Photobooth

A modern, native photobooth application for Raspberry Pi 4 (4GB). Built with
Python 3.11+ and PySide6/Qt Quick — no browser, no Electron, GPU-composited
UI that runs full-screen straight on the framebuffer.

## Features

- Single / grid / GIF / boomerang capture modes
- Camera backends: Canon DSLR (gphoto2), Raspberry Pi Camera Module
  (picamera2), USB webcam (OpenCV), and a dummy backend for development
- Live preview during countdown, animated on-screen countdown ring
- Filters (B&W, sepia, vintage, vivid) and green-screen chroma key
- Configurable m×n grid layout with custom background/overlay/logo slots
- Printing via CUPS (Canon SELPHY CP1300 out of the box), with a PDF
  debug fallback
- Email, WebDAV upload, and USB export sharing
- GPIO support for a physical trigger button, exit button, lamp, and RGB
  LED ring
- In-app, PIN-gated settings covering every option above
- English/German/Spanish/French UI
- Idle-screen slideshow of recent shots, SQLite-indexed

## Development (Windows/macOS)

```
uv sync --group dev
uv run photobooth
```

Without real camera/printer/GPIO hardware, the app automatically falls back
to the dummy camera backend and a PDF "printer" so the full flow (idle →
capture → review → share) is testable on a regular dev machine.

Run the tests:

```
uv run pytest
```

## Raspberry Pi deployment

See [`scripts/install.sh`](scripts/install.sh) for provisioning (system
packages for libcamera/picamera2, gphoto2, CUPS, plus `uv sync`) and
[`scripts/photobooth.service`](scripts/photobooth.service) for the systemd
unit that boots straight into the full-screen kiosk UI.

## Configuration

Defaults live in `src/photobooth/config/defaults.toml`. User overrides and
photo/session data are stored under the platform's standard app-data
directory (see `src/photobooth/paths.py`) and are also editable live from
the in-app Settings screen (PIN-protected, default PIN `1234` — change it
on first setup).
