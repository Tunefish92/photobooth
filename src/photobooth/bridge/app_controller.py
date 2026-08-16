"""The single ViewModel exposed to QML.

Owns the state machine, the camera thread, and every subsystem (storage,
imaging, printing, sharing, GPIO). All flow timing (greeter/countdown/review/
postprocess) lives here as a handful of QTimers driven by the state machine's
transitions -- see `_on_state_changed` for the "on entering state X, do Y"
table.
"""

from __future__ import annotations

import io
import logging
import math
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Property, QCoreApplication, QObject, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QImage

from photobooth import __version__, paths, updater
from photobooth.bridge.background import run_in_background
from photobooth.bridge.camera_worker import CameraWorker
from photobooth.bridge.preview_provider import PreviewImageProvider
from photobooth.camera import create_camera_backend
from photobooth.config.settings import Settings, save_settings
from photobooth.core.session import CaptureSession, shot_count_for_mode
from photobooth.core.state_machine import PhotoboothStateMachine, State
from photobooth.hardware.gpio import GpioController
from photobooth.i18n.translator import Translator
from photobooth.imaging import (
    apply_chroma_key,
    apply_filter,
    compose_grid,
    make_boomerang,
    make_gif,
)
from photobooth.printing import create_printer_backend
from photobooth.sharing import export_to_first_available, send_email, upload_file
from photobooth.storage import PhotoDatabase, SessionStore

logger = logging.getLogger(__name__)

def _optional_path(value: str) -> Path | None:
    return Path(value) if value else None


def _countdown_duration(session: CaptureSession | None, settings: Settings) -> float:
    """Seconds to count down before the next shot.

    The first shot of a session uses the full pre-shot countdown
    (`flow.countdown_time_s`); subsequent shots in a multi-shot session
    (grid/gif/boomerang) use the shorter, separately configurable
    `camera.inter_shot_delay_s` instead, so bursts don't drag.
    """
    if session is not None and session.shots:
        return settings.camera.inter_shot_delay_s
    return settings.flow.countdown_time_s


def _shrink(image: Image.Image, max_width: int) -> Image.Image:
    if image.width <= max_width:
        return image
    ratio = max_width / image.width
    return image.resize((max_width, int(image.height * ratio)), Image.LANCZOS)


class AppController(QObject):
    stateChanged = Signal()
    countdownChanged = Signal()
    shotsChanged = Signal()
    resultChanged = Signal()
    errorChanged = Signal()
    cameraReadyChanged = Signal()
    previewFrameIdChanged = Signal()
    slideshowChanged = Signal()
    postprocessBusyChanged = Signal()
    configChanged = Signal()
    updateInfoChanged = Signal()
    selectedModeChanged = Signal()
    toast = Signal(str)

    _request_capture = Signal()
    _request_camera_stop = Signal()

    def __init__(self, settings: Settings, translator: Translator, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.translator = translator

        self._preview_provider = PreviewImageProvider()
        self._preview_frame_id = 0
        self._camera_ready = False
        # Mode tapped on the idle screen, awaiting confirmation on the
        # "start this mode?" screen -- "" means still showing the tile
        # grid. Reset to "" on every fresh arrival at IDLE (see
        # _on_state_changed) so a completed/aborted session never leaves
        # the confirm screen stuck open.
        self._selected_mode = ""

        self._db = PhotoDatabase(paths.database_file())
        self._store = SessionStore(paths.photos_dir(settings.storage.photos_dir), settings.storage)
        self._printer = create_printer_backend(
            settings.printer, paths.user_data_dir() / "print_debug"
        )
        self._gpio = GpioController(settings.gpio)
        self._gpio.trigger_pressed.connect(self._on_gpio_trigger)
        self._gpio.exit_pressed.connect(self.hardReset)

        self._result_url = ""
        self._error_message = ""
        self._countdown_value = 0
        self._countdown_remaining = 0.0
        self._countdown_total = 0.0
        self._postprocess_busy = False
        self._slideshow: list[str] = []
        self._idle_hue = 0.0

        self._update_checking = False
        self._update_applying = False
        self._update_available = False
        self._latest_version = ""
        self._update_error = ""

        self._greeter_timer = self._make_timer(single_shot=True)
        self._greeter_timer.timeout.connect(self._sm_start_countdown)
        self._countdown_timer = self._make_timer(interval_ms=50)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)
        self._review_timer = self._make_timer(single_shot=True)
        self._review_timer.timeout.connect(self._sm_confirm)
        self._postprocess_timer = self._make_timer(single_shot=True)
        self._postprocess_timer.timeout.connect(self._sm_finish)
        self._idle_light_timer = self._make_timer(interval_ms=100)
        self._idle_light_timer.timeout.connect(self._tick_idle_light)
        self._scoped_timers = (
            self._greeter_timer,
            self._countdown_timer,
            self._review_timer,
            self._postprocess_timer,
            self._idle_light_timer,
        )

        self._sm = PhotoboothStateMachine(on_change=self._on_state_changed)

        self._camera_thread = QThread(self)
        self._camera_worker = CameraWorker(self._build_camera_backend)
        self._camera_worker.moveToThread(self._camera_thread)
        self._camera_thread.started.connect(self._camera_worker.start)
        self._camera_worker.frame_ready.connect(self._on_frame_ready)
        self._camera_worker.capture_ready.connect(self._on_capture_ready)
        self._camera_worker.capture_failed.connect(self._on_capture_failed)
        self._camera_worker.ready.connect(self._on_camera_ready)
        self._request_capture.connect(self._camera_worker.do_capture)
        self._request_camera_stop.connect(self._camera_worker.stop)
        self._camera_thread.start()

        self._on_state_changed(self._sm.state)  # prime initial UI state

        # Check for an update shortly after startup (delayed so it never
        # competes with initial UI rendering/camera warmup) so the idle
        # screen's badge can already be showing by the time a guest walks up.
        QTimer.singleShot(3000, self.checkForUpdates)

    # -- setup helpers ---------------------------------------------------
    def _make_timer(self, *, interval_ms: int = 0, single_shot: bool = False) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(single_shot)
        if interval_ms:
            timer.setInterval(interval_ms)
        return timer

    def _build_camera_backend(self):
        return create_camera_backend(
            self._settings.camera.backend, self._settings.camera.opencv_device_index
        )

    @property
    def preview_provider(self) -> PreviewImageProvider:
        return self._preview_provider

    def shutdown(self) -> None:
        self._request_camera_stop.emit()
        self._camera_thread.quit()
        self._camera_thread.wait(2000)
        self._gpio.teardown()
        self._db.close()

    # -- state machine glue -----------------------------------------------
    def _sm_start_countdown(self) -> None:
        self._sm.start_countdown()

    def _sm_confirm(self) -> None:
        self._sm.confirm()

    def _sm_finish(self) -> None:
        self._sm.finish()

    def _on_state_changed(self, state: State) -> None:
        for timer in self._scoped_timers:
            timer.stop()

        self.stateChanged.emit()

        if state is State.GREETER:
            self._greeter_timer.start(int(self._settings.flow.greeter_time_s * 1000))
            self._gpio.lamp_off()
        elif state is State.COUNTDOWN:
            self._countdown_total = _countdown_duration(self._sm.session, self._settings)
            self._countdown_remaining = self._countdown_total
            self._countdown_value = math.ceil(self._countdown_remaining)
            self.countdownChanged.emit()
            self._countdown_timer.start()
            self._gpio.lamp_on()
        elif state is State.CAPTURE:
            self._gpio.rgb_color(1, 1, 0.9)
            self._request_capture.emit()
        elif state is State.PROCESSING:
            self._gpio.rgb_off()
            self._run_processing()
        elif state is State.REVIEW:
            self._review_timer.start(int(self._settings.flow.display_time_s * 1000))
        elif state is State.POSTPROCESS:
            self._postprocess_timer.start(int(self._settings.flow.postprocess_time_s * 1000))
        elif state is State.IDLE:
            self._gpio.lamp_off()
            self._idle_light_timer.start()
            self._refresh_slideshow()
            if self._selected_mode:
                self._selected_mode = ""
                self.selectedModeChanged.emit()
        elif state is State.ERROR:
            self._error_message = self._sm.error_message
            self._gpio.rgb_off()
            self._gpio.lamp_off()
            self.errorChanged.emit()

    def _tick_idle_light(self) -> None:
        import colorsys

        self._idle_hue = (self._idle_hue + 1 / 360) % 1.0
        r, g, b = colorsys.hsv_to_rgb(self._idle_hue, 1.0, 1.0)
        self._gpio.rgb_color(r, g, b)

    def _on_countdown_tick(self) -> None:
        self._countdown_remaining -= 0.05
        value = max(0, math.ceil(self._countdown_remaining))
        if value != self._countdown_value:
            self._countdown_value = value
            self.countdownChanged.emit()
        if self._countdown_remaining <= 0:
            self._countdown_timer.stop()
            self._sm.capture_now()

    # -- camera signals -----------------------------------------------------
    def _on_frame_ready(self, image: QImage) -> None:
        self._preview_provider.set_image(image)
        self._preview_frame_id += 1
        self.previewFrameIdChanged.emit()

    def _on_camera_ready(self, is_real: bool) -> None:
        self._camera_ready = is_real
        self.cameraReadyChanged.emit()

    def _on_capture_ready(self, data: bytes, extension: str) -> None:
        session = self._sm.session
        if session is None:
            return
        index = len(session.shots)
        path = self._store.shot_path(session, index, extension)
        self._store.write(path, data)
        session.add_shot(path)
        self._db.record_photo(session.id, path, "shot")
        self.shotsChanged.emit()
        self._sm.shot_captured()

    def _on_capture_failed(self, message: str) -> None:
        self._sm.raise_error(f"Capture failed: {message}")

    def _on_gpio_trigger(self) -> None:
        # On the "start this mode?" confirmation screen, the physical
        # trigger button acts as that screen's Start button (the selected
        # mode); otherwise it's a shortcut straight to the default mode.
        mode = self._selected_mode or self._settings.flow.default_mode
        self.start(mode, self._settings.effects.default_filter)

    # -- processing -----------------------------------------------------------
    def _run_processing(self) -> None:
        session = self._sm.session
        assert session is not None
        try:
            images = [
                apply_filter(Image.open(p).convert("RGB"), session.filter_name)
                for p in session.shots
            ]

            effects = self._settings.effects
            if effects.chroma_key_enabled and effects.chroma_key_background:
                bg_path = Path(effects.chroma_key_background)
                if bg_path.is_file():
                    bg_image = Image.open(bg_path)
                    images = [
                        apply_chroma_key(img, bg_image, tuple(effects.chroma_key_color))
                        for img in images
                    ]

            if session.mode in ("gif", "boomerang"):
                burst = self._settings.burst
                if session.mode == "boomerang":
                    frames = [_shrink(img, burst.boomerang_frame_max_width_px) for img in images]
                    data = make_boomerang(frames, burst.boomerang_frame_duration_ms)
                else:
                    frames = [_shrink(img, burst.gif_frame_max_width_px) for img in images]
                    data = make_gif(frames, burst.gif_frame_duration_ms)
                extension = "gif"
            else:
                layout = self._settings.layout
                if session.mode == "single":
                    # "single" is always a 1x1 frame regardless of the configured
                    # grid shape -- otherwise it'd composite one photo into a
                    # num_x*num_y grid and leave the rest of the canvas blank.
                    layout = layout.model_copy(update={"num_x": 1, "num_y": 1, "skip": []})
                composed = compose_grid(
                    images,
                    layout,
                    background=_optional_path(layout.background),
                    overlay=_optional_path(layout.overlay),
                )
                buf = io.BytesIO()
                composed.save(buf, format="JPEG", quality=95)
                data = buf.getvalue()
                extension = "jpg"

            result_path = self._store.result_path(session, extension)
            self._store.write(result_path, data)
            session.result_path = result_path
            self._db.record_session(session)
            self._db.record_photo(session.id, result_path, "result")

            if not self._store.keep_individual_shots:
                for shot in session.shots:
                    shot.unlink(missing_ok=True)

            self._result_url = QUrl.fromLocalFile(str(result_path)).toString()
            self.resultChanged.emit()
            self._sm.assembled()
        except Exception:
            logger.exception("Failed to assemble result")
            self._sm.raise_error("Failed to assemble your picture")

    def _refresh_slideshow(self) -> None:
        self._slideshow = [
            QUrl.fromLocalFile(str(p)).toString() for p in self._db.recent_results(limit=20)
        ]
        self.slideshowChanged.emit()

    # -- postprocess actions -----------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        self._postprocess_busy = busy
        self.postprocessBusyChanged.emit()

    def _on_action_done(self, message_key: str) -> None:
        self._set_busy(False)
        self.toast.emit(self.translator.tr(message_key))

    def _on_action_failed(self, message: str) -> None:
        logger.warning("Postprocess action failed: %s", message)
        self._set_busy(False)
        self.toast.emit(self.translator.tr("postprocess.action_failed"))

    @Slot()
    def requestPrint(self) -> None:
        session = self._sm.session
        if self._postprocess_busy or session is None or session.result_path is None:
            return
        self._set_busy(True)
        run_in_background(
            self._printer.print_file,
            session.result_path,
            on_success=lambda _: self._on_action_done("postprocess.print_ok"),
            on_error=self._on_action_failed,
        )

    @Slot()
    def requestEmail(self) -> None:
        session = self._sm.session
        if self._postprocess_busy or session is None or session.result_path is None:
            return
        self._set_busy(True)
        run_in_background(
            send_email,
            self._settings.mailer,
            session.result_path,
            on_success=lambda _: self._on_action_done("postprocess.email_ok"),
            on_error=self._on_action_failed,
        )

    @Slot()
    def requestWebdavUpload(self) -> None:
        session = self._sm.session
        if self._postprocess_busy or session is None or session.result_path is None:
            return
        self._set_busy(True)
        run_in_background(
            upload_file,
            self._settings.webdav,
            session.result_path,
            on_success=lambda _: self._on_action_done("postprocess.upload_ok"),
            on_error=self._on_action_failed,
        )

    @Slot()
    def requestUsbExport(self) -> None:
        session = self._sm.session
        if self._postprocess_busy or session is None:
            return
        self._set_busy(True)
        run_in_background(
            export_to_first_available,
            session,
            on_success=self._on_usb_export_done,
            on_error=self._on_action_failed,
        )

    def _on_usb_export_done(self, result: Path | None) -> None:
        key = "postprocess.usb_ok" if result is not None else "postprocess.usb_missing"
        self._on_action_done(key)

    # -- update check/apply, invoked from QML --------------------------------
    @Slot()
    def checkForUpdates(self) -> None:
        if self._update_checking or self._update_applying:
            return
        self._update_checking = True
        self._update_error = ""
        self.updateInfoChanged.emit()
        run_in_background(
            updater.fetch_latest_version,
            on_success=self._on_update_check_done,
            on_error=self._on_update_check_failed,
        )

    def _on_update_check_done(self, latest_version: str) -> None:
        self._update_checking = False
        self._latest_version = latest_version
        self._update_available = updater.is_newer(latest_version, __version__)
        self.updateInfoChanged.emit()

    def _on_update_check_failed(self, message: str) -> None:
        logger.warning("Update check failed: %s", message)
        self._update_checking = False
        self._update_error = message
        self.updateInfoChanged.emit()

    @Slot()
    def applyUpdate(self) -> None:
        if self._update_applying or not self._update_available or not self._latest_version:
            return
        self._update_applying = True
        self._update_error = ""
        self.updateInfoChanged.emit()
        run_in_background(
            updater.apply_update,
            self._latest_version,
            on_success=self._on_update_apply_done,
            on_error=self._on_update_apply_failed,
        )

    def _on_update_apply_done(self, _result: None) -> None:
        self.toast.emit(self.translator.tr("settings.update.restart_notice"))
        # Give the toast a moment to actually render before the process
        # exits; the autostart wrapper's restart loop (see run-kiosk.sh) brings
        # the app back up running the code we just checked out.
        QTimer.singleShot(1500, QCoreApplication.quit)

    def _on_update_apply_failed(self, message: str) -> None:
        logger.warning("Update apply failed: %s", message)
        self._update_applying = False
        self._update_error = message
        self.updateInfoChanged.emit()
        self.toast.emit(self.translator.tr("settings.update.failed"))

    # -- flow control, invoked from QML ------------------------------------
    @Slot(str)
    def selectMode(self, mode: str) -> None:
        """Idle-screen tile tapped: show the "start this mode?" screen
        rather than starting immediately. Ignored for a mode that isn't
        actually enabled (defensive; the idle screen only offers enabled
        ones) so a stale/tampered call can't select something with no
        tile."""
        if self._sm.state != State.IDLE or mode not in self._settings.flow.enabled_modes:
            return
        self._selected_mode = mode
        self.selectedModeChanged.emit()

    @Slot()
    def cancelModeSelection(self) -> None:
        if not self._selected_mode:
            return
        self._selected_mode = ""
        self.selectedModeChanged.emit()

    @Slot(str, str)
    def start(self, mode: str, filter_name: str = "none") -> None:
        if self._sm.state != State.IDLE:
            return
        layout = self._settings.layout
        burst = self._settings.burst
        count = shot_count_for_mode(
            mode, layout.num_x, layout.num_y, burst.gif_shot_count, burst.boomerang_shot_count
        )
        session = CaptureSession(mode=mode, target_shot_count=count, filter_name=filter_name)
        self._sm.trigger(session)

    @Slot()
    def retake(self) -> None:
        if self._sm.state == State.REVIEW:
            self._sm.retake()

    @Slot()
    def confirmReview(self) -> None:
        if self._sm.state == State.REVIEW:
            self._sm.confirm()

    @Slot()
    def done(self) -> None:
        if self._sm.state != State.POSTPROCESS:
            return
        # _selected_mode is untouched for the whole GREETER..POSTPROCESS
        # run (only the IDLE entry below clears it), so it's still the
        # mode this session just used.
        mode = self._selected_mode
        self._sm.finish()
        # finish()'s IDLE transition just cleared _selected_mode (see
        # _on_state_changed) -- reselect it so the guest lands back on
        # that mode's confirm screen, not the tile grid. One tap away
        # from another round of the same mode, the common case at a live
        # event where one mode runs for the whole session. A mode
        # reached via the GPIO shortcut with nothing selected (mode ==
        # "") correctly falls through to the tile grid instead.
        if mode:
            self._selected_mode = mode
            self.selectedModeChanged.emit()

    @Slot()
    def retryError(self) -> None:
        if self._sm.state == State.ERROR:
            self._sm.retry()

    @Slot()
    def abortError(self) -> None:
        if self._sm.state == State.ERROR:
            self._sm.abort()

    @Slot()
    def hardReset(self) -> None:
        """Force the state machine back to IDLE from wherever it is. Not
        part of the normal user-facing flow -- nothing in the UI calls
        this -- it's a guaranteed escape hatch the test suite uses to
        reset shared app state between tests, so every state needs a real
        path back to IDLE here, not just the ones a human would hit
        (GREETER/COUNTDOWN/CAPTURE/PROCESSING/REVIEW have no direct exit
        of their own, so those go through the same raise_error+abort
        detour ERROR recovery already uses)."""
        state = self._sm.state
        if state == State.IDLE:
            return
        if state == State.SETTINGS:
            self._sm.exit_settings()
        elif state == State.POSTPROCESS:
            self._sm.finish()
        elif state == State.ERROR:
            self._sm.abort()
        else:
            self._sm.raise_error("hardReset")
            self._sm.abort()

    @Slot(str, result=bool)
    def enterSettings(self, pin: str) -> bool:
        if self._sm.state != State.IDLE or pin != self._settings.admin.pin:
            return False
        self._sm.enter_settings()
        return True

    @Slot()
    def exitSettings(self) -> None:
        if self._sm.state == State.SETTINGS:
            self._sm.exit_settings()

    @Slot(result="QVariant")
    def getSettingsJson(self):
        return self._settings.model_dump(mode="json")

    @Slot("QVariant")
    def saveSettingsJson(self, data) -> None:
        try:
            new_settings = Settings.model_validate(data)
        except Exception:
            logger.exception("Rejected invalid settings payload")
            self.toast.emit(self.translator.tr("postprocess.action_failed"))
            return
        self._settings = new_settings
        save_settings(new_settings, paths.user_config_file())
        self.translator.setLanguage(new_settings.app.language)
        # Cheap to rebuild, so these take effect immediately; camera backend,
        # GPIO, and window mode are flagged "restart required" in the UI since
        # re-initializing them live is riskier (open hardware handles, etc.)
        self._store = SessionStore(paths.photos_dir(new_settings.storage.photos_dir), new_settings.storage)
        self._printer = create_printer_backend(
            new_settings.printer, paths.user_data_dir() / "print_debug"
        )
        self.configChanged.emit()
        self.toast.emit(self.translator.tr("settings.saved"))

    # -- properties ---------------------------------------------------------
    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._sm.state.value

    @Property(int, notify=countdownChanged)
    def countdownValue(self) -> int:
        return self._countdown_value

    @Property(float, notify=countdownChanged)
    def countdownProgress(self) -> float:
        total = max(self._countdown_total, 0.001)
        return max(0.0, min(1.0, self._countdown_remaining / total))

    @Property(int, notify=shotsChanged)
    def shotsTaken(self) -> int:
        session = self._sm.session
        return len(session.shots) if session else 0

    @Property(int, notify=shotsChanged)
    def shotsTotal(self) -> int:
        session = self._sm.session
        return session.target_shot_count if session else 0

    @Property(str, notify=resultChanged)
    def resultImageUrl(self) -> str:
        return self._result_url

    @Property(str, notify=errorChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(bool, notify=cameraReadyChanged)
    def cameraReady(self) -> bool:
        return self._camera_ready

    @Property(int, notify=previewFrameIdChanged)
    def previewFrameId(self) -> int:
        return self._preview_frame_id

    @Property(list, notify=slideshowChanged)
    def slideshowImages(self) -> list[str]:
        return self._slideshow

    @Property(bool, notify=postprocessBusyChanged)
    def postprocessBusy(self) -> bool:
        return self._postprocess_busy

    @Property(list, notify=configChanged)
    def enabledModes(self) -> list[str]:
        return list(self._settings.flow.enabled_modes)

    @Property(str, notify=selectedModeChanged)
    def selectedMode(self) -> str:
        return self._selected_mode

    @Property(list, notify=configChanged)
    def enabledFilters(self) -> list[str]:
        return list(self._settings.effects.enabled_filters)

    @Property(str, notify=configChanged)
    def defaultFilter(self) -> str:
        return self._settings.effects.default_filter

    @Property(str, notify=configChanged)
    def theme(self) -> str:
        return self._settings.app.theme

    @Property(bool, notify=configChanged)
    def printerEnabled(self) -> bool:
        return self._settings.printer.enable

    @Property(bool, notify=configChanged)
    def mailerEnabled(self) -> bool:
        return self._settings.mailer.enable

    @Property(bool, notify=configChanged)
    def webdavEnabled(self) -> bool:
        return self._settings.webdav.enable

    @Property(bool, notify=configChanged)
    def usbExportEnabled(self) -> bool:
        return self._settings.usb_export.enable

    @Property(bool, notify=configChanged)
    def printConfirmation(self) -> bool:
        return self._settings.printer.confirmation

    @Property(str, constant=True)
    def currentVersion(self) -> str:
        return __version__

    @Property(str, notify=updateInfoChanged)
    def latestVersion(self) -> str:
        return self._latest_version

    @Property(bool, notify=updateInfoChanged)
    def updateAvailable(self) -> bool:
        return self._update_available

    @Property(bool, notify=updateInfoChanged)
    def updateChecking(self) -> bool:
        return self._update_checking

    @Property(bool, notify=updateInfoChanged)
    def updateApplying(self) -> bool:
        return self._update_applying

    @Property(str, notify=updateInfoChanged)
    def updateError(self) -> str:
        return self._update_error
