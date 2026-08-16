"""Filesystem locations for user config, photo storage, and logs.

Kept dependency-free (no `platformdirs`) since the set of platforms we
actually run on is small and fixed: Raspberry Pi OS (Linux) in production,
Windows/macOS during development.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_APP_NAME = "photobooth"


def _base_config_dir() -> Path:
    if sys.platform == "win32":
        root = os.environ.get("APPDATA")
        return Path(root) if root else Path.home() / "AppData" / "Roaming"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _base_data_dir() -> Path:
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA")
        return Path(root) if root else Path.home() / "AppData" / "Local"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def user_config_dir() -> Path:
    path = _base_config_dir() / _APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_config_file() -> Path:
    return user_config_dir() / "config.toml"


def user_data_dir() -> Path:
    path = _base_data_dir() / _APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def photos_dir(override: str = "") -> Path:
    """`override` is StorageConfig.photos_dir -- an absolute path to use
    instead of the default app-data location (e.g. a mounted external
    drive), or "" to use the default."""
    path = Path(override).expanduser() if override else user_data_dir() / "photos"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_file() -> Path:
    return user_data_dir() / "photobooth.sqlite3"


def log_file() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path / "photobooth.log"
