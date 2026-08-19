"""Guards against translation drift: since translation strings are now
hand-authored across two catalogs (en/de) with no gettext-style extraction
tooling, it's easy to add a key to one file and forget the other, or leave a
value blank. These are pure-Python/filesystem checks (no Qt/QML needed).
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path

_SUPPORTED_LANGUAGES = {"en", "de"}
_UI_DIR = Path(__file__).resolve().parent.parent / "src" / "photobooth" / "ui"
# Matches Translator.tr("literal.key") -- deliberately not string
# concatenation like Translator.tr("idle.mode." + mode), which by
# construction can only resolve to one of a small enumerated set of
# already-covered keys (see idle.mode.* in test_photo_modes_tab_and_
# all_modes_are_translated below).
_TR_CALL = re.compile(r'Translator\.tr\(\s*"([^"]+)"\s*\)')


def _load(lang: str) -> dict[str, str]:
    text = resources.files("photobooth.i18n.translations").joinpath(f"{lang}.json").read_text("utf-8")
    return json.loads(text)


def test_only_en_and_de_catalogs_exist():
    pkg = resources.files("photobooth.i18n.translations")
    names = {entry.name for entry in pkg.iterdir() if entry.name.endswith(".json")}
    assert names == {f"{lang}.json" for lang in _SUPPORTED_LANGUAGES}


def test_en_and_de_have_identical_key_sets():
    en_keys = set(_load("en"))
    de_keys = set(_load("de"))
    assert en_keys == de_keys, (
        f"translation key mismatch -- en-only: {sorted(en_keys - de_keys)}, "
        f"de-only: {sorted(de_keys - en_keys)}"
    )


def test_no_translation_values_are_blank():
    for lang in _SUPPORTED_LANGUAGES:
        catalog = _load(lang)
        blank_keys = [key for key, value in catalog.items() if not value.strip()]
        assert not blank_keys, f"{lang}.json has blank values for: {blank_keys}"


def test_every_settings_field_label_has_a_translation():
    """Every field the Settings screen renders (see SettingsScreen.qml) goes
    through Translator.tr("settings.field.*") -- this is a regression guard
    against re-introducing a hardcoded English label literal that silently
    never gets translated for German users."""
    expected_fields = {
        "language", "theme", "fullscreen", "hide_cursor", "admin_pin",
        "auto_restart", "auto_restart_hint",
        "photos_dir", "photos_dir_placeholder", "photos_dir_hint",
        "camera_backend", "rotation", "mirror_preview", "usb_index", "inter_shot_delay",
        "camera_battery",
        "enable_printing", "printer_backend", "cups_name", "print_confirmation",
        "paper_width", "paper_height",
        "email_enable", "smtp_server", "smtp_port", "smtp_user", "smtp_password",
        "recipient", "webdav_enable", "webdav_url", "webdav_user", "webdav_password",
        "gpio_enable", "trigger_pin", "exit_pin", "lamp_pin",
        "rgb_red_pin", "rgb_green_pin", "rgb_blue_pin",
        "grid_columns", "grid_rows", "output_width", "output_height", "margin",
        "margin_preview_hint", "background_path", "overlay_path",
        "backup_enable", "backup_interval", "backup_interval_off", "backup_interval_5",
        "backup_interval_10", "backup_interval_15", "backup_interval_30", "backup_interval_60",
        "backup_device_current", "backup_device_none", "backup_device_unsaved",
        "backup_scan", "backup_no_devices", "backup_now", "backup_running",
        "default_filter", "chroma_key", "chroma_key_path",
        "gif_shot_count", "gif_frame_duration", "gif_frame_width",
        "boomerang_shot_count", "boomerang_frame_duration", "boomerang_frame_width",
    }
    en = _load("en")
    for field in expected_fields:
        key = f"settings.field.{field}"
        assert key in en, f"missing translation key {key!r}"
        assert en[key].strip()


def test_photo_modes_tab_and_all_modes_are_translated():
    """The Photo Modes settings tab reuses idle.mode.* for its switch labels
    (single/grid/gif/boomerang) rather than duplicating them under
    settings.field.* -- confirm those keys, plus the tab label and the
    "at least one" hint, all exist in both catalogs."""
    en = _load("en")
    for key in (
        "settings.tab.modes",
        "settings.modes_hint",
        "idle.mode.single",
        "idle.mode.grid",
        "idle.mode.gif",
        "idle.mode.boomerang",
    ):
        assert key in en, f"missing translation key {key!r}"
        assert en[key].strip()


def test_update_feature_is_fully_translated():
    en = _load("en")
    for key in (
        "idle.update_badge",
        "settings.tab.update",
        "settings.update.current_version",
        "settings.update.latest_version",
        "settings.update.check_button",
        "settings.update.update_button",
        "settings.update.checking",
        "settings.update.applying",
        "settings.update.up_to_date",
        "settings.update.available",
        "settings.update.restart_notice",
        "settings.update.failed",
        "settings.update.not_checked_yet",
    ):
        assert key in en, f"missing translation key {key!r}"
        assert en[key].strip()


def test_every_literal_translator_tr_call_in_qml_resolves():
    """Broader net than test_every_settings_field_label_has_a_translation
    (which only covers SettingsScreen.qml's settings.field.* keys): scans
    every .qml file under src/photobooth/ui for Translator.tr("literal")
    call sites and confirms each one exists in the catalog. A key used in
    QML but never added to en.json would otherwise just silently render as
    the raw key string (see Translator.tr's fallback) instead of failing
    anything -- this is the guard against ever shipping that.
    """
    en = _load("en")
    qml_files = list(_UI_DIR.rglob("*.qml"))
    assert qml_files, f"no .qml files found under {_UI_DIR} -- test isn't finding the UI source"

    missing: list[str] = []
    for path in qml_files:
        text = path.read_text(encoding="utf-8")
        for match in _TR_CALL.finditer(text):
            key = match.group(1)
            if key not in en:
                missing.append(f"{key!r} in {path.relative_to(_UI_DIR)}")

    assert not missing, "Translator.tr() call(s) with no matching catalog key:\n" + "\n".join(missing)
