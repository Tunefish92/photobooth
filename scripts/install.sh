#!/usr/bin/env bash
# Provisions a Raspberry Pi OS (Bookworm) Pi 4 to run the photobooth as a
# full-screen kiosk. Run from the repo root: `sudo scripts/install.sh`
#
# What this does:
#   1. Installs system packages (libcamera/picamera2, gphoto2, CUPS, build deps)
#   2. Creates a venv with access to the apt-installed picamera2 and syncs
#      the project's Python dependencies into it via uv
#   3. Installs the systemd kiosk service
#
# What it does NOT do (needs a one-off manual step, hardware-specific):
#   - Registering the SELPHY CP1300 in CUPS (see the printed instructions
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
    python3-picamera2 --no-install-recommends \
    python3-libcamera \
    python3-venv \
    libgphoto2-dev gphoto2 \
    cups libcups2-dev \
    curl git

echo "==> Adding $TARGET_USER to hardware groups"
usermod -aG video,render,input,plugdev,lp,lpadmin "$TARGET_USER"

if ! command -v uv >/dev/null 2>&1; then
    echo "==> Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

echo "==> Creating virtualenv (with access to apt-installed picamera2)"
cd "$REPO_DIR"
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e .

echo "==> Installing systemd service"
sed "s#/opt/photobooth#${REPO_DIR}#g; s#User=pi#User=${TARGET_USER}#; s#Group=pi#Group=${TARGET_USER}#" \
    scripts/photobooth.service > /etc/systemd/system/photobooth.service
systemctl daemon-reload
systemctl enable photobooth.service

cat <<EOF

==> Done. Two manual steps remain:

1. Register the Canon SELPHY CP1300 in CUPS. Plug it in, then:
     lpinfo -v                     # find its usb:// device URI
     lpadmin -p Canon_SELPHY_CP1300 -E \\
         -v <usb-device-uri-from-above> \\
         -P ${REPO_DIR}/../photobooth_old/supplementals/Canon_SELPHY_CP1300.ppd
   (or point -P at wherever you've copied that PPD; it ships in the old
   project's supplementals/ folder.) If the printer queue name differs from
   "Canon_SELPHY_CP1300", update it in Settings -> Printer in the app.

2. Reboot, or start the kiosk now:
     sudo systemctl start photobooth.service
     journalctl -u photobooth.service -f    # to watch logs

EOF
