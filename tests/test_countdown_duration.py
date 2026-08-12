"""Unit tests for `_countdown_duration`, the pure function that picks between
the first-shot countdown and the shorter inter-shot delay for burst modes
(grid/gif/boomerang). Kept separate from `AppController` (which needs a Qt
event loop) so this stays a fast, Qt-free test.
"""

from pathlib import Path

from photobooth.bridge.app_controller import _countdown_duration
from photobooth.config.settings import Settings
from photobooth.core.session import CaptureSession


def make_settings(*, countdown_time_s=3.0, inter_shot_delay_s=1.0) -> Settings:
    settings = Settings()
    settings.flow.countdown_time_s = countdown_time_s
    settings.camera.inter_shot_delay_s = inter_shot_delay_s
    return settings


def test_no_session_uses_flow_countdown():
    settings = make_settings(countdown_time_s=5.0)
    assert _countdown_duration(None, settings) == 5.0


def test_first_shot_of_a_session_uses_flow_countdown():
    settings = make_settings(countdown_time_s=5.0, inter_shot_delay_s=1.5)
    session = CaptureSession(mode="grid", target_shot_count=4)
    assert len(session.shots) == 0
    assert _countdown_duration(session, settings) == 5.0


def test_subsequent_shots_use_the_shorter_inter_shot_delay():
    settings = make_settings(countdown_time_s=5.0, inter_shot_delay_s=1.5)
    session = CaptureSession(mode="grid", target_shot_count=4)
    session.add_shot(Path("shot_0.jpg"))
    assert _countdown_duration(session, settings) == 1.5

    session.add_shot(Path("shot_1.jpg"))
    session.add_shot(Path("shot_2.jpg"))
    assert _countdown_duration(session, settings) == 1.5


def test_single_mode_session_never_has_a_second_shot_to_delay():
    """Sanity check tying this to the real state machine flow: "single"
    mode has target_shot_count=1, so it always completes on the first shot
    and this branch is unreachable in practice for it -- still worth
    confirming the helper's behavior is well-defined regardless."""
    settings = make_settings(countdown_time_s=3.0, inter_shot_delay_s=1.0)
    session = CaptureSession(mode="single", target_shot_count=1)
    assert _countdown_duration(session, settings) == 3.0
