#!/usr/bin/env bash
# Autostart entry point launched by the desktop session (see
# scripts/photobooth.desktop). Relaunches the app whenever it exits --
# covers both crashes and the deliberate self-restart after an in-app
# update (see photobooth/updater.py) -- unless Settings -> General ->
# "Restart automatically after exit or crash" has been turned off, in
# which case the app leaves a marker file behind (see
# photobooth.paths.auto_restart_marker_file) and this loop exits instead
# of relaunching it.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.."

MARKER="${XDG_DATA_HOME:-$HOME/.local/share}/photobooth/auto_restart_disabled"

while true; do
    .venv/bin/photobooth
    if [[ -f "$MARKER" ]]; then
        echo "Auto-restart disabled in Settings -- not relaunching."
        break
    fi
    sleep 2
done
