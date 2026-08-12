from pathlib import Path

import pytest

from photobooth.core.session import CaptureSession
from photobooth.core.state_machine import InvalidTransition, PhotoboothStateMachine, State


def make_session(mode="single", count=1):
    return CaptureSession(mode=mode, target_shot_count=count)


def capture_one_shot(sm: PhotoboothStateMachine) -> None:
    """Mirrors what AppController._on_capture_ready does: add the shot, then advance."""
    sm.capture_now()
    sm.session.add_shot(Path(f"shot_{len(sm.session.shots)}.jpg"))
    sm.shot_captured()


def test_happy_path_single_shot():
    sm = PhotoboothStateMachine()
    assert sm.state == State.IDLE

    sm.trigger(make_session(count=1))
    assert sm.state == State.GREETER

    sm.start_countdown()
    assert sm.state == State.COUNTDOWN

    capture_one_shot(sm)
    assert sm.state == State.PROCESSING  # single shot -> session complete immediately

    sm.assembled()
    assert sm.state == State.REVIEW

    sm.confirm()
    assert sm.state == State.POSTPROCESS

    sm.finish()
    assert sm.state == State.IDLE
    assert sm.session is None


def test_multi_shot_loops_back_to_countdown():
    sm = PhotoboothStateMachine()
    sm.trigger(make_session(mode="grid", count=2))
    sm.start_countdown()
    capture_one_shot(sm)
    assert sm.state == State.COUNTDOWN  # one more shot needed

    capture_one_shot(sm)
    assert sm.state == State.PROCESSING


def test_retake_resets_shots_and_returns_to_greeter():
    sm = PhotoboothStateMachine()
    sm.trigger(make_session(count=1))
    sm.start_countdown()
    capture_one_shot(sm)
    sm.assembled()
    assert sm.state == State.REVIEW
    assert len(sm.session.shots) == 1

    sm.retake()
    assert sm.state == State.GREETER
    assert len(sm.session.shots) == 0  # retake clears prior shots


def test_invalid_transition_raises():
    sm = PhotoboothStateMachine()
    with pytest.raises(InvalidTransition):
        sm.start_countdown()  # can't skip GREETER


def test_error_retry_returns_to_previous_state():
    sm = PhotoboothStateMachine()
    sm.trigger(make_session(count=1))
    sm.start_countdown()
    assert sm.state == State.COUNTDOWN

    sm.raise_error("camera exploded")
    assert sm.state == State.ERROR
    assert sm.error_message == "camera exploded"

    sm.retry()
    assert sm.state == State.COUNTDOWN


def test_error_abort_returns_to_idle_and_clears_session():
    sm = PhotoboothStateMachine()
    sm.trigger(make_session(count=1))
    sm.raise_error("boom")
    sm.abort()
    assert sm.state == State.IDLE
    assert sm.session is None


def test_listener_receives_every_transition():
    seen = []
    sm = PhotoboothStateMachine(on_change=seen.append)
    sm.trigger(make_session(count=1))
    sm.start_countdown()
    assert seen == [State.GREETER, State.COUNTDOWN]
