#!/usr/bin/env bash
# Autostart entry point launched by the desktop session (see
# scripts/photobooth.desktop). Relaunches the app whenever it exits --
# covers both crashes and the deliberate self-restart after an in-app
# update (see photobooth/updater.py).
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.."
while true; do
    .venv/bin/photobooth
    sleep 2
done
