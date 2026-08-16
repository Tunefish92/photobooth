"""photos_dir()'s override parameter (StorageConfig.photos_dir) lets a
custom absolute path -- e.g. a mounted USB drive -- replace the default
app-data location."""

from __future__ import annotations

from pathlib import Path

from photobooth import paths


def test_photos_dir_without_override_uses_default_location():
    default = paths.user_data_dir() / "photos"
    assert paths.photos_dir("") == default
    assert default.is_dir()


def test_photos_dir_with_override_uses_that_path(tmp_path: Path):
    custom = tmp_path / "external-drive" / "booth-photos"
    assert not custom.exists()

    result = paths.photos_dir(str(custom))

    assert result == custom
    assert custom.is_dir()  # created if it didn't exist


def test_photos_dir_override_expands_user_home(monkeypatch, tmp_path: Path):
    # expanduser() resolves "~" via $HOME/$USERPROFILE, not Path.home()
    # directly, so both need setting for this to work cross-platform.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    result = paths.photos_dir("~/booth-photos")

    assert result == tmp_path / "booth-photos"
    assert result.is_dir()
