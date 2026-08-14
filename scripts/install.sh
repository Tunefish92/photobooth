#!/usr/bin/env bash
# Provisions a Raspberry Pi OS (Bookworm, 64-bit) Pi 4 to run the photobooth
# as a full-screen kiosk. Run from the repo root: `sudo scripts/install.sh`
#
# What this does:
#   1. Installs system packages: libcamera/picamera2, gphoto2, CUPS (+ the
#      gutenprint driver and driverless-IPP support for the Canon SELPHY
#      CP1300/CP1500), the Qt6/EGLFS runtime libraries the PySide6 wheel
#      needs at runtime, and the build toolchain the gphoto2/pycups/lgpio
#      Python packages need to compile their C extensions.
#   2. Creates a venv with access to the apt-installed picamera2 and syncs
#      the project's Python dependencies into it via `uv sync` (uses
#      uv.lock, so versions match what's actually been tested).
#   3. Installs the systemd kiosk service.
#
# What it does NOT do (needs a one-off manual step, hardware-specific):
#   - Registering the SELPHY printer in CUPS (see the printed instructions
#     at the end) -- the exact USB device URI varies per unit.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo scripts/install.sh" >&2
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${SUDO_USER:-pi}"

echo "==> Installing system packages"
apt-get update
apt-get install -y \
    python3-picamera2 \
    python3-libcamera \
    python3-venv \
    libgphoto2-dev gphoto2 \
    cups cups-client libcups2-dev \
    printer-driver-gutenprint \
    ipp-usb \
    build-essential python3-dev pkg-config swig \
    libegl1 libgles2 libgbm1 libinput10 \
    libxkbcommon0 fontconfig libfontconfig1 libdbus-1-3 \
    curl git

echo "==> Adding $TARGET_USER to hardware groups"
usermod -aG video,render,input,plugdev,lp,lpadmin "$TARGET_USER"

if ! command -v uv >/dev/null 2>&1; then
    echo "==> Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        echo "uv installed but not on PATH; looked in \$HOME/.local/bin and \$HOME/.cargo/bin" >&2
        exit 1
    fi
fi

echo "==> Creating virtualenv (with access to apt-installed picamera2)"
cd "$REPO_DIR"
python3 -m venv --system-site-packages .venv

echo "==> Syncing Python dependencies (uv sync, pinned by uv.lock)"
export UV_PROJECT_ENVIRONMENT="$REPO_DIR/.venv"
uv sync --no-dev

echo "==> Installing systemd service"
sed "s#/opt/photobooth#${REPO_DIR}#g; s#User=pi#User=${TARGET_USER}#; s#Group=pi#Group=${TARGET_USER}#" \
    scripts/photobooth.service > /etc/systemd/system/photobooth.service
systemctl daemon-reload
systemctl enable photobooth.service

cat <<EOF

==> Done. Two manual steps remain:

1. Register the Canon SELPHY printer (CP1300/CP1500) in CUPS. Plug it in,
   then check whether CUPS already sees it as a driverless IPP-over-USB
   device (ipp-usb, installed above, handles this for printers that
   support it -- most CP1300/CP1500 units do):
     lpinfo -v
   If a line like "ipp://..." or "dnssd://..." shows up for the printer,
   just add it with CUPS' own "everywhere" driver, no PPD needed:
     lpadmin -p Canon_SELPHY -E -v <that-uri-from-above> -m everywhere
   Otherwise, use the gutenprint driver installed above -- list its
   built-in Canon SELPHY models and pick the closest match:
     lpinfo -m | grep -i selphy
     lpadmin -p Canon_SELPHY -E -v <usb-device-uri-from-lpinfo--v> \\
         -m <model-string-from-lpinfo--m>
   Either way, if the queue name isn't "Canon_SELPHY", update it in
   Settings -> Printer in the app (cups_printer_name).

2. Reboot, or start the kiosk now:
     sudo systemctl start photobooth.service
     journalctl -u photobooth.service -f    # to watch logs

EOF
