"""Gphoto2Backend.battery_level() parsing, in isolation from the real
python-gphoto2 package (Linux-only, not installed on this dev machine) --
constructs the backend directly and stubs just the two attributes
battery_level() touches (`_camera`, `_gp`), rather than mocking sys.modules.
"""

from __future__ import annotations

from photobooth.camera.gphoto2_backend import Gphoto2Backend


class _FakeGPhoto2Error(Exception):
    pass


class _FakeGPModule:
    GPhoto2Error = _FakeGPhoto2Error


class _FakeWidget:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_value(self) -> str:
        return self._value


class _FakeConfig:
    def __init__(self, widgets: dict[str, _FakeWidget]) -> None:
        self._widgets = widgets

    def get_child_by_name(self, name: str) -> _FakeWidget:
        if name not in self._widgets:
            raise _FakeGPhoto2Error(f"no such config widget: {name!r}")
        return self._widgets[name]


class _FakeCamera:
    def __init__(self, config: _FakeConfig) -> None:
        self._config = config

    def get_config(self) -> _FakeConfig:
        return self._config


def _backend_with_widgets(widgets: dict[str, _FakeWidget]) -> Gphoto2Backend:
    backend = Gphoto2Backend()
    backend._gp = _FakeGPModule()
    backend._camera = _FakeCamera(_FakeConfig(widgets))
    return backend


def test_battery_level_parses_a_plain_number():
    backend = _backend_with_widgets({"batterylevel": _FakeWidget("75")})
    assert backend.battery_level() == 75


def test_battery_level_parses_a_percent_suffixed_value():
    backend = _backend_with_widgets({"batterylevel": _FakeWidget("42%")})
    assert backend.battery_level() == 42


def test_battery_level_is_none_for_a_non_numeric_state():
    """Some cameras report a state like "Powered" instead of a percentage
    when running on an AC adapter rather than the battery."""
    backend = _backend_with_widgets({"batterylevel": _FakeWidget("Powered")})
    assert backend.battery_level() is None


def test_battery_level_is_none_when_the_camera_exposes_no_such_widget():
    """Not every gphoto2-supported model/vendor exposes battery status via
    PTP -- must degrade to "unknown", not raise."""
    backend = _backend_with_widgets({})
    assert backend.battery_level() is None
