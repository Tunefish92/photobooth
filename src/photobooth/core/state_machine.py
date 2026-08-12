"""Pure-Python finite state machine driving the photobooth flow.

Deliberately Qt-free so it stays trivially unit-testable; `bridge.app_controller`
wraps it and re-emits transitions as Qt signals for QML.

Flow: IDLE -> GREETER -> COUNTDOWN <-> CAPTURE (looped per shot) -> PROCESSING
-> REVIEW -> POSTPROCESS -> IDLE, with SETTINGS reachable from IDLE and ERROR
reachable (and recoverable) from anywhere.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import StrEnum

from photobooth.core.session import CaptureSession

logger = logging.getLogger(__name__)


class State(StrEnum):
    IDLE = "idle"
    GREETER = "greeter"
    COUNTDOWN = "countdown"
    CAPTURE = "capture"
    PROCESSING = "processing"
    REVIEW = "review"
    POSTPROCESS = "postprocess"
    SETTINGS = "settings"
    ERROR = "error"


class InvalidTransition(RuntimeError):
    pass


class PhotoboothStateMachine:
    def __init__(self, on_change: Callable[[State], None] | None = None) -> None:
        self._state = State.IDLE
        self._previous_state = State.IDLE
        self._session: CaptureSession | None = None
        self._error_message = ""
        self._listeners: list[Callable[[State], None]] = []
        if on_change is not None:
            self._listeners.append(on_change)

    @property
    def state(self) -> State:
        return self._state

    @property
    def session(self) -> CaptureSession | None:
        return self._session

    @property
    def error_message(self) -> str:
        return self._error_message

    def add_listener(self, listener: Callable[[State], None]) -> None:
        self._listeners.append(listener)

    def _transition(self, new_state: State) -> None:
        logger.debug("state: %s -> %s", self._state, new_state)
        self._previous_state = self._state
        self._state = new_state
        for listener in self._listeners:
            listener(new_state)

    def _require(self, *allowed: State) -> None:
        if self._state not in allowed:
            raise InvalidTransition(f"Cannot do this in state {self._state} (need {allowed})")

    # -- IDLE ---------------------------------------------------------
    def trigger(self, session: CaptureSession) -> None:
        """Guest tapped/pressed start: begin a new session."""
        self._require(State.IDLE)
        self._session = session
        self._transition(State.GREETER)

    def enter_settings(self) -> None:
        self._require(State.IDLE)
        self._transition(State.SETTINGS)

    def exit_settings(self) -> None:
        self._require(State.SETTINGS)
        self._transition(State.IDLE)

    # -- GREETER --------------------------------------------------------
    def start_countdown(self) -> None:
        self._require(State.GREETER)
        self._transition(State.COUNTDOWN)

    # -- COUNTDOWN / CAPTURE loop ---------------------------------------
    def capture_now(self) -> None:
        self._require(State.COUNTDOWN)
        self._transition(State.CAPTURE)

    def shot_captured(self) -> None:
        self._require(State.CAPTURE)
        assert self._session is not None
        if self._session.is_complete:
            self._transition(State.PROCESSING)
        else:
            self._transition(State.COUNTDOWN)

    # -- PROCESSING -------------------------------------------------------
    def assembled(self) -> None:
        self._require(State.PROCESSING)
        self._transition(State.REVIEW)

    # -- REVIEW -----------------------------------------------------------
    def retake(self) -> None:
        self._require(State.REVIEW)
        assert self._session is not None
        self._session.reset_shots()
        self._transition(State.GREETER)

    def confirm(self) -> None:
        self._require(State.REVIEW)
        self._transition(State.POSTPROCESS)

    # -- POSTPROCESS --------------------------------------------------------
    def finish(self) -> None:
        self._require(State.POSTPROCESS)
        self._session = None
        self._transition(State.IDLE)

    # -- ERROR handling -----------------------------------------------------
    def raise_error(self, message: str) -> None:
        self._error_message = message
        if self._state is State.ERROR:
            for listener in self._listeners:
                listener(self._state)
            return
        self._transition(State.ERROR)

    def retry(self) -> None:
        self._require(State.ERROR)
        self._transition(self._previous_state)

    def abort(self) -> None:
        self._require(State.ERROR)
        self._session = None
        self._transition(State.IDLE)
