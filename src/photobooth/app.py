"""Builds the QGuiApplication + QML engine and wires the Python bridge in."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QCursor, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from photobooth import paths
from photobooth.bridge.app_controller import AppController
from photobooth.config.settings import load_settings
from photobooth.i18n.translator import Translator

logger = logging.getLogger(__name__)

_UI_DIR = Path(__file__).parent / "ui"
_CURSOR_IDLE_MS = 3000


class _CursorAutoHider(QObject):
    """Keeps the cursor hidden for the clean touch-kiosk look, but reveals it
    the instant a real mouse moves and re-hides it after a few seconds idle.

    Without this, `hide_cursor` makes the app effectively unusable with a
    mouse (clicks still work, but there's no visible pointer to aim with) --
    this way touch-only kiosks stay cursor-free while a mouse (dev machines,
    or one plugged into the kiosk for troubleshooting) just works.
    """

    def __init__(self, app: QGuiApplication) -> None:
        super().__init__(app)
        self._app = app
        self._hidden = False
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(_CURSOR_IDLE_MS)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._hide)
        app.installEventFilter(self)
        self._hide()

    def _hide(self) -> None:
        if not self._hidden:
            self._app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
            self._hidden = True

    def _reveal(self) -> None:
        if self._hidden:
            self._app.restoreOverrideCursor()
            self._hidden = False
        self._idle_timer.start()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseMove:
            self._reveal()
        return False


def run() -> int:
    settings = load_settings(paths.user_config_file())

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Photobooth")
    app.setOrganizationName("Photobooth")
    app.setWindowIcon(QIcon(str(_UI_DIR / "icon.png")))

    translator = Translator(settings.app.language)
    controller = AppController(settings, translator)

    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda errors: [logger.error("QML: %s", e.toString()) for e in errors])
    engine.addImageProvider("preview", controller.preview_provider)
    engine.rootContext().setContextProperty("App", controller)
    engine.rootContext().setContextProperty("Translator", translator)
    engine.rootContext().setContextProperty(
        "Config", {"fullscreen": settings.app.fullscreen, "width": settings.app.width, "height": settings.app.height}
    )
    engine.quit.connect(app.quit)

    engine.load(QUrl.fromLocalFile(str(_UI_DIR / "main.qml")))
    if not engine.rootObjects():
        logger.error("Failed to load QML UI")
        return 1

    if settings.app.hide_cursor and settings.app.fullscreen:
        _CursorAutoHider(app)  # parented to app, so it lives for the app's lifetime

    app.aboutToQuit.connect(controller.shutdown)

    return app.exec()
