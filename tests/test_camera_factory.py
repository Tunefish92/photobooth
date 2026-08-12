"""Camera backend selection must never leave the app without a usable
backend -- a missing library, absent hardware, or even an unrecognized
backend name should all degrade to the dummy backend rather than crash
capture entirely.
"""

from photobooth.camera.dummy_backend import DummyBackend
from photobooth.camera.factory import create_camera_backend


def test_dummy_backend_is_always_available():
    backend = create_camera_backend("dummy")
    assert isinstance(backend, DummyBackend)


def test_unavailable_hardware_backend_falls_back_to_dummy():
    """On this dev machine gphoto2/picamera2 aren't installed and no real
    hardware is attached, so requesting them explicitly must fall back
    rather than raise -- exercises the real ImportError/CameraUnavailableError
    path without needing to mock anything."""
    backend = create_camera_backend("gphoto2")
    assert isinstance(backend, DummyBackend)


def test_auto_falls_back_to_dummy_when_nothing_else_available():
    backend = create_camera_backend("auto")
    assert isinstance(backend, DummyBackend)


def test_unknown_backend_name_falls_back_to_dummy_instead_of_raising():
    """CameraBackendName is a pydantic Literal in normal use, so this
    shouldn't be reachable through Settings -- but create_camera_backend
    itself takes a plain str, and a ValueError from an unrecognized name
    must still degrade gracefully rather than crash the whole app."""
    backend = create_camera_backend("not-a-real-backend")  # type: ignore[arg-type]
    assert isinstance(backend, DummyBackend)
