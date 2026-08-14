#!/usr/bin/env bash
# Provisions a Raspberry Pi OS (64-bit, Desktop) Pi 4 to run the photobooth
# as a full-screen kiosk app. Run from the repo root: `sudo scripts/install.sh`
#
# What this does:
#   1. Installs system packages: libcamera/picamera2, gphoto2, CUPS (+ the
#      gutenprint driver and driverless-IPP support for the Canon SELPHY
#      CP1300/CP1500), the Qt6/EGL/Wayland runtime libraries the PySide6
#      wheel needs at runtime, and the build toolchain the
#      gphoto2/pycups/lgpio Python packages need to compile their C
#      extensions.
#   2. Creates a venv with access to the apt-installed picamera2 and syncs
#      the project's Python dependencies into it via `uv sync` (uses
#      uv.lock, so versions match what's actually been tested).
#   3. Installs a desktop autostart entry (scripts/photobooth.desktop) that
#      launches the app -- as a normal fullscreen window under the
#      desktop's own Wayland compositor -- once the desktop session starts,
#      and sets the Pi to boot straight to Desktop with auto-login.
#
# This requires the Desktop Raspberry Pi OS image, not Lite -- the app
# relies on the desktop's compositor (labwc) to own the display, sidestepping
# the DRM/KMS permission wrangling a direct-framebuffer (eglfs) kiosk needs.
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
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

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
    build-essential python3-dev pkg-config swig liblgpio-dev \
    libegl1 libgles2 libgbm1 \
    libwayland-client0 libwayland-cursor0 libwayland-egl1 \
    libxkbcommon0 fontconfig libfontconfig1 libdbus-1-3 \
    curl git

echo "==> Adding $TARGET_USER to hardware groups"
usermod -aG video,render,plugdev,lp,lpadmin "$TARGET_USER"

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

echo "==> Installing desktop autostart entry"
chmod +x "$REPO_DIR/scripts/run-kiosk.sh"
AUTOSTART_DIR="$TARGET_HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
sed "s#/opt/photobooth#${REPO_DIR}#g" scripts/photobooth.desktop > "$AUTOSTART_DIR/photobooth.desktop"
chown "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.config" "$AUTOSTART_DIR" "$AUTOSTART_DIR/photobooth.desktop"

echo "==> Removing the old console-kiosk systemd service, if present"
systemctl disable --now photobooth.service 2>/dev/null || true
rm -f /etc/systemd/system/photobooth.service
systemctl unmask getty@tty1.service 2>/dev/null || true
systemctl daemon-reload

echo "==> Setting boot behaviour to Desktop with auto-login"
if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_boot_behaviour B4 || \
        echo "raspi-config couldn't set Desktop Autologin -- if this Pi is on the Lite image, install the desktop packages first (e.g. 'sudo apt install raspberrypi-ui-mods lightdm'), then set it via 'sudo raspi-config' -> System Options -> Boot / Auto Login -> Desktop Autologin." >&2
else
    echo "raspi-config not found -- set Boot Options -> Desktop Autologin manually." >&2
fi

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

2. Reboot -- the Pi comes up straight to the desktop and the app
   autostarts fullscreen on top of it:
     sudo reboot
   To try it now without rebooting (from a terminal in the desktop
   session, not over SSH -- it needs the desktop's Wayland display):
     scripts/run-kiosk.sh

EOF
