from pathlib import Path

import pytest
from pydantic import ValidationError

from photobooth.config.settings import FlowConfig, Settings, load_settings, save_settings


def test_load_settings_without_override_returns_defaults():
    settings = load_settings(None)
    assert isinstance(settings, Settings)
    assert settings.printer.cups_printer_name == "Canon_SELPHY_CP1300"
    assert settings.layout.num_x == 2
    assert settings.camera.inter_shot_delay_s == 1.0


def test_load_settings_merges_user_override(tmp_path: Path):
    override = tmp_path / "config.toml"
    override.write_text('[printer]\nenable = false\ncups_printer_name = "Other"\n', encoding="utf-8")

    settings = load_settings(override)
    assert settings.printer.enable is False
    assert settings.printer.cups_printer_name == "Other"
    # untouched sections still come from defaults
    assert settings.layout.num_x == 2


def test_save_then_load_roundtrips(tmp_path: Path):
    path = tmp_path / "config.toml"
    settings = load_settings(None)
    settings.admin.pin = "9999"
    settings.layout.num_x = 3
    settings.camera.inter_shot_delay_s = 2.5

    save_settings(settings, path)
    reloaded = load_settings(path)

    assert reloaded.admin.pin == "9999"
    assert reloaded.layout.num_x == 3
    assert reloaded.camera.inter_shot_delay_s == 2.5


def test_layout_margin_fields_roundtrip_uniformly(tmp_path: Path):
    """The Settings UI's single "Margin (px)" field writes the same value to
    all four of inner_dist_x/y and outer_dist_x/y -- confirm that survives a
    save/load cycle without any of the four drifting apart."""
    path = tmp_path / "config.toml"
    settings = load_settings(None)
    settings.layout.inner_dist_x = 55
    settings.layout.inner_dist_y = 55
    settings.layout.outer_dist_x = 55
    settings.layout.outer_dist_y = 55

    save_settings(settings, path)
    reloaded = load_settings(path)

    assert (
        reloaded.layout.inner_dist_x
        == reloaded.layout.inner_dist_y
        == reloaded.layout.outer_dist_x
        == reloaded.layout.outer_dist_y
        == 55
    )


def test_flow_config_rejects_empty_enabled_modes():
    """The Settings UI's Photo Modes tab lets a user uncheck every mode
    switch one at a time; the UI itself blocks disabling the last one, but
    this is the authoritative guard for any other writer (a hand-edited
    config.toml, a future API, etc.) -- disabling all modes would leave the
    idle screen's mode picker empty and GPIO/start() with nothing to launch.
    """
    with pytest.raises(ValidationError, match="At least one photo mode"):
        FlowConfig(enabled_modes=[])


def test_flow_config_accepts_a_single_enabled_mode():
    config = FlowConfig(enabled_modes=["grid"])
    assert config.enabled_modes == ["grid"]


def test_load_settings_with_empty_enabled_modes_override_raises(tmp_path: Path):
    """A hand-edited config.toml that disables every mode must fail loudly
    at startup rather than silently producing an unusable idle screen."""
    override = tmp_path / "config.toml"
    override.write_text("[flow]\nenabled_modes = []\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_settings(override)
