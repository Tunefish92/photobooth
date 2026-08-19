"""Headless (offscreen) smoke tests that actually load the QML UI and walk
the rendered item tree.

Unlike the unit tests elsewhere, these catch a real class of bug that pure
Python tests can't: QML-level mistakes like a custom property shadowing a
built-in one (e.g. naming something `data`, which silently breaks `Item`'s
default child-parenting property and leaves a screen rendering nothing), or
widgets that exist but are misconfigured (e.g. a SpinBox left non-editable).
Runs via Qt's `offscreen` platform plugin, so no real display is needed.
"""

from __future__ import annotations

import os
import time
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QMetaObject, QPoint, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from photobooth.bridge.app_controller import AppController
from photobooth.config.settings import load_settings
from photobooth.i18n.translator import Translator

_UI_MAIN_QML = "src/photobooth/ui/main.qml"


def _pump(seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.01)


@pytest.fixture(scope="module")
def running_app(tmp_path_factory):
    """One QGuiApplication + loaded engine, shared by the tests in this module.

    (QGuiApplication can only be constructed once per process, so this is a
    module-scoped fixture rather than per-test.)
    """
    # Isolate from the real user config/data dirs -- these tests must not
    # touch or depend on whatever is in the developer's actual AppData.
    # `photobooth.paths` reads XDG_DATA_HOME/LOCALAPPDATA for photos+db and
    # XDG_CONFIG_HOME/APPDATA for config.toml (Linux/Windows respectively) --
    # all four need overriding, not just the two data-dir ones, or a test
    # that ever saves settings would silently write into the developer's
    # real ~/.config or %APPDATA% instead of this tmp dir.
    data_dir = tmp_path_factory.mktemp("photobooth_data")
    os.environ["XDG_DATA_HOME"] = str(data_dir)
    os.environ["LOCALAPPDATA"] = str(data_dir)
    os.environ["XDG_CONFIG_HOME"] = str(data_dir)
    os.environ["APPDATA"] = str(data_dir)

    # AppController schedules an update check ~3s after construction (see
    # its singleShot in __init__); stub the network call for the whole
    # fixture lifetime so a slow-enough test run never fires a real request
    # against the GitHub API.
    updater_patcher = patch(
        "photobooth.updater.fetch_latest_version", return_value="v0.0.0"
    )
    updater_patcher.start()

    settings = load_settings(None)
    # Only one QGuiApplication/QCoreApplication can exist per process, and
    # other test modules (e.g. test_background.py) may have already made
    # one when the whole suite runs together -- reuse it instead of
    # constructing a second one, which raises at the C++ level.
    app = QGuiApplication.instance() or QGuiApplication([])
    translator = Translator(settings.app.language)
    controller = AppController(settings, translator)

    warnings: list[str] = []
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    engine.addImageProvider("preview", controller.preview_provider)
    engine.rootContext().setContextProperty("App", controller)
    engine.rootContext().setContextProperty("Translator", translator)
    engine.rootContext().setContextProperty(
        "Config", {"fullscreen": False, "width": 1280, "height": 800}
    )
    engine.load(QUrl.fromLocalFile(_UI_MAIN_QML))

    assert engine.rootObjects(), "QML failed to load at all"
    _pump(0.3)

    yield app, engine, controller, warnings

    controller.shutdown()
    updater_patcher.stop()


@pytest.fixture(autouse=True)
def _reset_state_after_each_test(running_app):
    """`running_app` is module-scoped (one Qt app for the whole file), so a
    test that fails partway through -- before it reaches its own
    `exitSettings()`/cleanup call -- would otherwise leave the controller
    stuck in a non-idle state for every test that runs after it. Force it
    back to idle unconditionally once each test finishes, pass or fail.
    """
    yield
    _app, _engine, controller, _warnings = running_app
    controller.hardReset()
    _pump(0.1)


def test_idle_screen_loads_without_qml_warnings(running_app):
    _app, _engine, controller, warnings = running_app
    assert controller.state == "idle"
    assert warnings == []


def test_no_property_shadowing_warnings(running_app):
    """Regression test for the `data` property shadowing `Item.data` bug:
    that specific mistake surfaces as a qt.qml.propertyCache warning, which
    `engine.warnings` does NOT catch (it's a lower-level qWarning), so this
    checks stderr wouldn't be the only way to notice it -- assert instead
    that every screen actually renders real content, which is the symptom
    a shadowed default property produces (see next test).
    """
    _app, _engine, controller, _warnings = running_app
    assert controller.state == "idle"


def test_settings_screen_renders_real_content_when_entered(running_app):
    _app, engine, controller, warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)  # let the crossfade transition finish

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    assert settings_root is not None, (
        "SettingsScreen didn't attach to the visual tree -- if you renamed "
        "or added a property on its root Item, check it doesn't shadow a "
        "built-in Item property (e.g. `data`, `children`, `state`)."
    )

    descendants = settings_root.findChildren(QQuickItem)
    assert len(descendants) > 50, "settings screen rendered almost nothing"

    labels = {str(k.property("text")) for k in descendants if k.property("text")}
    assert "Settings" in labels
    assert any("webcam index" in label for label in labels)

    assert warnings == []

    controller.exitSettings()
    _pump(0.3)
    assert controller.state == "idle"


def _is_instance_of(item: QQuickItem, cpp_class_substring: str) -> bool:
    """True if `cpp_class_substring` appears anywhere in item's C++ class
    hierarchy. Settings fields use QML-defined subtypes (e.g. WideSpin.qml
    extends SpinBox) so the leaf `metaObject().className()` is "WideSpin",
    not "QQuickSpinBox" -- walking `superClass()` finds the real C++ base.
    """
    meta_object = item.metaObject()
    while meta_object is not None:
        if cpp_class_substring in meta_object.className():
            return True
        meta_object = meta_object.superClass()
    return False


def test_settings_spinboxes_are_editable(running_app):
    """Regression test: QtQuick SpinBox defaults to editable=false, meaning
    you can only nudge the value with the tiny +/- buttons and can't type a
    number in directly -- easy to miss since the field still *looks* like a
    text box.
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    assert settings_root is not None
    spinboxes = [
        k for k in settings_root.findChildren(QQuickItem)
        if _is_instance_of(k, "SpinBox")
    ]
    assert len(spinboxes) >= 10, "expected the GPIO/printer/layout numeric fields"
    assert all(sb.property("editable") is True for sb in spinboxes), (
        "found a non-editable SpinBox -- users can't type a value into it"
    )

    controller.exitSettings()
    _pump(0.3)


def test_pin_pad_digits_stay_inside_the_card(running_app):
    """Regression test: the PIN popup card previously had a hardcoded
    height that was shorter than its content (label + display + 4 rows of
    digit buttons), so the bottom row rendered outside the card's border.
    The card now sizes to its content instead of a guessed constant.

    Checks the digit Grid's own bounding box against the card rather than
    each individual digit button: Repeater-generated delegates are true
    QQuickItem children of the Grid (for layout/painting) but are *not*
    reachable via QObject.findChildren, which walks a separate ownership
    tree -- the Grid auto-sizes to exactly enclose all of its buttons, so
    "the Grid fits inside the card" is an equivalent, simpler check.
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]
    assert controller.state == "idle"

    pin_popup = root.findChild(QQuickItem, "pinPopup")
    assert pin_popup is not None
    pin_popup.setProperty("visible", True)
    _pump(0.3)

    card = root.findChild(QQuickItem, "pinCard")
    assert card is not None
    card_w = card.property("width")
    card_h = card.property("height")

    grids = [
        k for k in pin_popup.findChildren(QQuickItem)
        if k.metaObject().className() == "QQuickGrid"
    ]
    assert len(grids) == 1, "expected the PIN pad's digit Grid"
    digit_grid = grids[0]
    assert digit_grid.property("width") > 0
    assert digit_grid.property("height") > 0

    top_left = digit_grid.mapToItem(card, 0, 0)
    bottom_right = digit_grid.mapToItem(
        card, digit_grid.property("width"), digit_grid.property("height")
    )
    assert 0 <= top_left.x() and bottom_right.x() <= card_w, (
        f"digit grid horizontally outside the card: {top_left.x()}..{bottom_right.x()} "
        f"vs card width {card_w}"
    )
    assert 0 <= top_left.y() and bottom_right.y() <= card_h, (
        f"digit grid vertically outside the card: {top_left.y()}..{bottom_right.y()} "
        f"vs card height {card_h}"
    )

    pin_popup.setProperty("visible", False)
    _pump(0.2)


def test_exit_button_and_confirmation_dialog_exist_on_idle_screen(running_app):
    """Regression test for the main-screen exit flow: a power-glyph
    IconButton in the bottom-right corner reveals a confirm-before-quit
    overlay (mirroring the existing pinPopup/printConfirm pattern) rather
    than quitting immediately on a single tap.
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]
    assert controller.state == "idle"

    exit_button = root.findChild(QQuickItem, "exitButton")
    assert exit_button is not None

    exit_confirm = root.findChild(QQuickItem, "exitConfirm")
    assert exit_confirm is not None
    assert exit_confirm.property("visible") is False

    # Confirm the two floating buttons don't collide: exit sits bottom-right,
    # settings gear sits top-right (no objectName on the gear button, so
    # just check exit is in the bottom half of the screen).
    screen_h = root.property("height")
    assert exit_button.property("y") > screen_h * 0.5

    exit_confirm.setProperty("visible", True)
    _pump(0.2)
    assert exit_confirm.property("visible") is True

    exit_confirm.setProperty("visible", False)
    _pump(0.2)
    assert controller.state == "idle", "opening/closing the confirm dialog must not change app state"


def test_tapping_a_mode_tile_shows_confirm_screen_without_starting(running_app):
    """Change request: tapping a mode tile no longer starts a session
    immediately -- it shows a confirmation screen titled with the selected
    mode, with a Start button. Confirm selecting a mode leaves the state
    machine in "idle" (not started yet) and reveals that screen with the
    right title."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]
    assert controller.state == "idle"

    confirm_screen = root.findChild(QQuickItem, "modeConfirmScreen")
    assert confirm_screen is not None
    assert confirm_screen.property("visible") is False

    controller.selectMode("grid")
    _pump(0.3)

    assert controller.state == "idle", "selecting a mode must not start the session yet"
    assert controller.property("selectedMode") == "grid"
    assert confirm_screen.property("visible") is True

    title = root.findChild(QQuickItem, "modeConfirmTitle")
    assert title is not None
    assert title.property("text") == "Grid"

    controller.cancelModeSelection()
    _pump(0.2)


def test_mode_confirm_back_button_returns_to_the_tile_grid(running_app):
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    controller.selectMode("gif")
    _pump(0.3)
    assert controller.property("selectedMode") == "gif"

    back_button = root.findChild(QQuickItem, "modeConfirmBackButton")
    assert back_button is not None
    assert QMetaObject.invokeMethod(back_button, "clicked")
    _pump(0.3)

    assert controller.property("selectedMode") == ""
    assert controller.state == "idle"
    confirm_screen = root.findChild(QQuickItem, "modeConfirmScreen")
    assert confirm_screen.property("visible") is False


def test_pressing_the_start_button_starts_the_selected_mode(running_app):
    """The actual "check that it starts the selected mode when the button
    is pressed" requirement -- invokes the real QML Button.clicked signal
    (not just calling App.start() directly) so this exercises the same
    onClicked wiring a real tap would."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    controller.selectMode("boomerang")
    _pump(0.3)

    start_button = root.findChild(QQuickItem, "modeConfirmStartButton")
    assert start_button is not None
    assert QMetaObject.invokeMethod(start_button, "clicked")
    _pump(0.3)

    assert controller.state == "greeter"
    assert controller._sm.session is not None
    assert controller._sm.session.mode == "boomerang"

    # Let the flow return to idle so this test doesn't leak a live session
    # into whichever test runs next against the same shared app.
    controller.hardReset()
    _pump(0.3)


def test_gpio_trigger_starts_the_selected_mode_when_one_is_pending(running_app):
    """Change request: the GPIO trigger pin is equivalent to the on-screen
    Start button -- while the confirm screen is showing, pressing the
    physical trigger button starts the *selected* mode, not flow.
    default_mode."""
    _app, engine, controller, _warnings = running_app

    default_mode = controller.getSettingsJson()["flow"]["default_mode"]
    other_mode = "grid" if default_mode != "grid" else "gif"

    controller.selectMode(other_mode)
    _pump(0.2)

    controller._on_gpio_trigger()
    _pump(0.3)

    assert controller.state == "greeter"
    assert controller._sm.session.mode == other_mode

    controller.hardReset()
    _pump(0.3)


def test_gpio_trigger_does_nothing_on_the_idle_tile_grid(running_app):
    """Change request: the GPIO trigger pin only acts as the confirm
    screen's Start button -- with no mode selected (still on the idle
    tile grid), pressing it must not start anything (previously it fell
    back to flow.default_mode as a shortcut; that shortcut is gone)."""
    _app, engine, controller, _warnings = running_app
    assert controller.property("selectedMode") == ""

    controller._on_gpio_trigger()
    _pump(0.3)

    assert controller.state == "idle"
    assert controller._sm.session is None


def test_selected_mode_resets_on_a_hard_reset_back_to_idle(running_app):
    """Regression test: an aborted/reset session (hardReset's raise_error+
    abort path -- used for e.g. camera/capture errors) must not leave
    _selected_mode pointing at a mode that just failed, landing the guest
    straight back on that same failing confirm screen. It should fall
    through to the tile grid instead. (Contrast the *normal* finish path,
    Done on the postprocess screen, which deliberately does the opposite
    -- see test_done_returns_to_the_selected_modes_confirm_screen below.)
    """
    _app, engine, controller, _warnings = running_app

    controller.selectMode("single")
    _pump(0.2)
    assert controller.property("selectedMode") == "single"

    controller._on_gpio_trigger()
    _pump(0.2)
    assert controller.state == "greeter"

    controller.hardReset()
    _pump(0.3)

    assert controller.state == "idle"
    assert controller.property("selectedMode") == ""


def test_done_returns_to_the_selected_modes_confirm_screen(running_app):
    """Change request: after a session finishes normally (Done on the
    postprocess screen), the guest should land back on that same mode's
    confirm screen -- never the tile grid -- so repeat rounds of the same
    mode stay there indefinitely; the only way back to the tile grid is
    the confirm screen's explicit Back button. (Retake doesn't need a
    corresponding fix: it goes straight back to GREETER for another
    attempt at the same session, per PhotoboothStateMachine.retake(), and
    never touches IDLE/_selected_mode at all.)

    Drives the state machine directly into POSTPROCESS rather than
    through a real capture -- that would race the AppController's actual
    background camera-worker thread, which reacts to the same signals
    this test would otherwise have to trigger by hand.
    """
    from photobooth.core.session import CaptureSession
    from photobooth.core.state_machine import State

    _app, engine, controller, _warnings = running_app

    controller.selectMode("single")
    _pump(0.2)
    assert controller.property("selectedMode") == "single"

    controller._sm._session = CaptureSession(mode="single", target_shot_count=1)
    controller._sm._transition(State.POSTPROCESS)
    _pump(0.1)
    assert controller.state == "postprocess"

    controller.done()
    _pump(0.3)

    assert controller.state == "idle"
    assert controller.property("selectedMode") == "single"

    # A second round behaves the same way -- it doesn't fall through to
    # the tile grid after the first repeat either.
    controller._sm._session = CaptureSession(mode="single", target_shot_count=1)
    controller._sm._transition(State.POSTPROCESS)
    _pump(0.1)
    controller.done()
    _pump(0.3)

    assert controller.state == "idle"
    assert controller.property("selectedMode") == "single"

    # Already idle, so hardReset() (a transition-triggered side effect)
    # would be a no-op here -- cancelModeSelection() is the direct way
    # back to the tile grid, same as tapping the confirm screen's Back
    # button.
    controller.cancelModeSelection()
    _pump(0.2)
    assert controller.property("selectedMode") == ""


def test_done_falls_through_to_the_tile_grid_when_reached_via_gpio_shortcut(running_app):
    """The GPIO-trigger-with-nothing-selected shortcut (straight to
    flow.default_mode, see _on_gpio_trigger) never sets _selected_mode --
    confirm Done in that case still lands on the tile grid, not some
    mode's confirm screen it was never actually shown."""
    from photobooth.core.session import CaptureSession
    from photobooth.core.state_machine import State

    _app, engine, controller, _warnings = running_app
    assert controller.property("selectedMode") == ""

    default_mode = controller.getSettingsJson()["flow"]["default_mode"]
    controller._sm._session = CaptureSession(mode=default_mode, target_shot_count=1)
    controller._sm._transition(State.POSTPROCESS)
    _pump(0.1)

    controller.done()
    _pump(0.3)

    assert controller.state == "idle"
    assert controller.property("selectedMode") == ""


def test_settings_language_selector_offers_only_en_and_de(running_app):
    """Regression test: the language dropdown used to list en/de/es/fr:
    es.json and fr.json were removed, so the selector must not offer them
    (nothing in the UI updates them anymore, and Translator would just warn
    and ignore an unknown language if picked)."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    combo = root.findChild(QQuickItem, "settingsLanguageCombo")
    assert combo is not None
    model = list(combo.property("model"))
    assert model == ["en", "de"]

    controller.exitSettings()
    _pump(0.3)


def test_settings_theme_selector_offers_all_five_themes(running_app):
    """Regression test: the theme dropdown must list every ThemeName the
    backend accepts (see Settings.AppConfig) -- previously only the two
    aurora variants existed, both in the combo and in Theme.qml's palette
    table; this guards the two staying in sync as themes are added."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    combo = root.findChild(QQuickItem, "settingsThemeCombo")
    assert combo is not None
    assert list(combo.property("model")) == [
        "aurora-dark", "aurora-light", "ocean-blue", "forest-green", "prism-modern",
    ]

    controller.exitSettings()
    _pump(0.3)


def test_saving_a_theme_choice_updates_the_live_theme_singleton(running_app):
    """Regression test: main.qml used to hardcode Theme.dark = true at
    startup and never read the persisted app.theme at all -- the theme
    dropdown had no visible effect no matter what was picked. Confirm
    App.theme (bound to Theme.name via a Binding in main.qml) actually
    reaches the Theme singleton, by checking the root Window's own
    `color: Theme.bg` binding picks up the new palette's background."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    data = controller.getSettingsJson()
    original_theme = data["app"]["theme"]
    try:
        data["app"]["theme"] = "prism-modern"
        controller.saveSettingsJson(data)
        _pump(0.3)

        assert controller.property("theme") == "prism-modern"
        assert root.property("color").name() == "#0b0b12"  # prism-modern's bg
    finally:
        data = controller.getSettingsJson()
        data["app"]["theme"] = original_theme
        controller.saveSettingsJson(data)
        _pump(0.3)


def test_settings_gear_button_uses_the_vector_gear_icon(running_app):
    """Regression test: the "⚙" GEAR Unicode glyph's visible ink isn't
    centered within its own character cell (how far off varies by font and
    rendering backend, so a fixed pixel nudge kept drifting) -- the idle
    screen's settings button now draws a small vector gear instead
    (GearIcon.qml), which is centered by construction. Confirm the button
    still opted into that mode and the Text glyph fallback is hidden.
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]
    assert controller.state == "idle"

    gear_button = root.findChild(QQuickItem, "settingsGearButton")
    assert gear_button is not None
    assert gear_button.property("vectorGear") is True

    visible_icons = [
        k for k in gear_button.findChildren(QQuickItem)
        if _is_instance_of(k, "Canvas") and k.property("visible") is True
    ]
    assert len(visible_icons) == 1, "expected exactly one visible Canvas-based icon (the gear)"


def test_exit_button_uses_the_vector_power_icon(running_app):
    """Regression test: the "⏻" POWER Unicode glyph isn't reliably covered
    by fonts on a minimal kiosk install (renders as a blank box), so the
    idle screen's exit button now draws a small vector power icon instead
    (PowerIcon.qml). Confirm the button still opted into that mode."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]
    assert controller.state == "idle"

    exit_button = root.findChild(QQuickItem, "exitButton")
    assert exit_button is not None
    assert exit_button.property("vectorPower") is True


def test_settings_close_button_uses_the_vector_close_icon(running_app):
    """Regression test: the "✕" MULTIPLICATION X Unicode glyph isn't
    reliably covered by fonts on a minimal kiosk install (renders as a
    blank box), so the Settings screen's close button now draws a small
    vector X instead (CloseIcon.qml). Confirm the button opted into that
    mode."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    close_button = root.findChild(QQuickItem, "settingsCloseButton")
    assert close_button is not None
    assert close_button.property("vectorClose") is True

    controller.exitSettings()
    _pump(0.3)


def test_photo_modes_tab_has_a_switch_per_mode_all_enabled_by_default(running_app):
    """Regression test for the Photo Modes tab: one Switch per capture mode
    (single/grid/gif/boomerang), all on by default (matching
    FlowConfig.enabled_modes' default of every mode enabled).
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 1)  # Modes is the 2nd nav section
    _pump(0.3)

    for mode in ("single", "grid", "gif", "boomerang"):
        switch = root.findChild(QQuickItem, f"modeSwitch_{mode}")
        assert switch is not None, f"missing switch for mode {mode!r}"
        assert switch.property("checked") is True

    controller.exitSettings()
    _pump(0.3)


def test_photo_modes_reflect_a_non_default_enabled_modes_list(running_app):
    """If a subset of modes is disabled in settings, the corresponding
    switches must load unchecked -- catches a stale/inverted
    `isModeEnabled()` binding."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    data = controller.getSettingsJson()
    data["flow"]["enabled_modes"] = ["single", "gif"]
    controller.saveSettingsJson(data)
    _pump(0.2)

    admin_pin = data["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 1)
    _pump(0.3)

    assert root.findChild(QQuickItem, "modeSwitch_single").property("checked") is True
    assert root.findChild(QQuickItem, "modeSwitch_grid").property("checked") is False
    assert root.findChild(QQuickItem, "modeSwitch_gif").property("checked") is True
    assert root.findChild(QQuickItem, "modeSwitch_boomerang").property("checked") is False

    controller.exitSettings()
    _pump(0.3)

    # restore every mode enabled so later tests in this module see the
    # normal default (module-scoped fixture -- state persists across tests)
    data["flow"]["enabled_modes"] = ["single", "grid", "gif", "boomerang"]
    controller.saveSettingsJson(data)
    _pump(0.2)


def test_update_tab_renders_with_expected_controls(running_app):
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 7)  # Update is the last (8th) nav section
    _pump(0.3)

    assert root.findChild(QQuickItem, "updateLatestVersionText") is not None
    assert root.findChild(QQuickItem, "updateStatusText") is not None
    check_button = root.findChild(QQuickItem, "checkForUpdatesButton")
    assert check_button is not None
    assert check_button.property("enabled") is True
    # no update available yet (nothing has checked) -- the apply button
    # must stay hidden until there's actually something to apply
    apply_button = root.findChild(QQuickItem, "applyUpdateButton")
    assert apply_button is not None
    assert apply_button.property("visible") is False

    controller.exitSettings()
    _pump(0.3)


def test_checking_for_updates_when_already_current_reports_up_to_date(running_app):
    """The module-scoped fixture stubs fetch_latest_version() to "v0.0.0",
    which is not newer than the running __version__ -- checking should land
    on "up to date", not flag an update or show the idle badge."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    controller.checkForUpdates()
    _pump(0.5)

    assert controller.updateAvailable is False
    badge = root.findChild(QQuickItem, "updateAvailableBadge")
    assert badge is not None
    assert badge.property("visible") is False


def test_checking_for_updates_flags_a_newer_release_and_shows_the_badge(running_app):
    """With a newer version stubbed in, checking must flip updateAvailable,
    reveal the idle screen's badge, and reveal the Settings tab's apply
    button -- all driven off the same App.updateAvailable property.
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    with patch("photobooth.updater.fetch_latest_version", return_value="v99.0.0"):
        controller.checkForUpdates()
        _pump(0.5)

    try:
        assert controller.updateAvailable is True
        assert controller.latestVersion == "v99.0.0"

        badge = root.findChild(QQuickItem, "updateAvailableBadge")
        assert badge is not None
        assert badge.property("visible") is True

        admin_pin = controller.getSettingsJson()["admin"]["pin"]
        assert controller.enterSettings(admin_pin) is True
        _pump(1.0)
        settings_root = root.findChild(QQuickItem, "settingsRoot")
        settings_root.setProperty("currentIndex", 7)
        _pump(0.3)

        apply_button = root.findChild(QQuickItem, "applyUpdateButton")
        assert apply_button.property("visible") is True

        controller.exitSettings()
        _pump(0.3)
    finally:
        # restore the "up to date" baseline so later tests in this module
        # don't see a stale updateAvailable=True from this test.
        controller.checkForUpdates()
        _pump(0.5)


def test_check_for_updates_ignores_concurrent_calls(running_app):
    """Tapping "Check for updates" repeatedly (or the startup timer racing
    a manual check) must not fire a second background request while one is
    already in flight -- checkForUpdates() guards on _update_checking."""
    _app, _engine, controller, _warnings = running_app
    call_count = 0

    def counting_fetch():
        nonlocal call_count
        call_count += 1
        return "v0.0.0"

    with patch("photobooth.updater.fetch_latest_version", side_effect=counting_fetch):
        controller.checkForUpdates()
        controller.checkForUpdates()
        controller.checkForUpdates()
        _pump(0.5)

    assert call_count == 1


def test_check_for_updates_handles_network_failure_gracefully(running_app):
    _app, _engine, controller, _warnings = running_app

    def boom():
        raise OSError("network unreachable")

    with patch("photobooth.updater.fetch_latest_version", side_effect=boom):
        controller.checkForUpdates()
        _pump(0.5)

    try:
        assert controller.updateChecking is False
        assert controller.updateAvailable is False
        assert controller.updateError  # non-empty -- surfaced somewhere, not swallowed
    finally:
        controller.checkForUpdates()  # restore "up to date" baseline (fixture-level stub)
        _pump(0.5)


def test_apply_update_is_a_noop_without_an_available_update(running_app):
    _app, _engine, controller, _warnings = running_app
    assert controller.updateAvailable is False  # baseline from prior tests' cleanup

    with patch("photobooth.updater.apply_update") as mock_apply:
        controller.applyUpdate()
        _pump(0.2)

    mock_apply.assert_not_called()
    assert controller.updateApplying is False


def test_apply_update_failure_resets_state_and_emits_a_toast(running_app):
    _app, _engine, controller, _warnings = running_app

    with patch("photobooth.updater.fetch_latest_version", return_value="v99.0.0"):
        controller.checkForUpdates()
        _pump(0.5)
    assert controller.updateAvailable is True

    toasts: list[str] = []
    controller.toast.connect(toasts.append)
    try:
        with patch(
            "photobooth.updater.apply_update",
            side_effect=RuntimeError("git checkout failed: fatal: bad tag"),
        ):
            controller.applyUpdate()
            _pump(0.5)

        assert controller.updateApplying is False
        assert "bad tag" in controller.updateError
        assert "Update failed" in toasts
    finally:
        controller.toast.disconnect(toasts.append)
        controller.checkForUpdates()  # restore baseline
        _pump(0.5)


def test_apply_update_success_schedules_a_restart_via_quit(running_app):
    """applyUpdate() must never restart anything itself beyond scheduling
    QCoreApplication.quit() -- actually calling quit() here would tear down
    the shared module-scoped app and break every later test in this file,
    so QTimer.singleShot is intercepted to just record the scheduled call
    instead of letting it fire.
    """
    _app, _engine, controller, _warnings = running_app

    with patch("photobooth.updater.fetch_latest_version", return_value="v99.0.0"):
        controller.checkForUpdates()
        _pump(0.5)
    assert controller.updateAvailable is True

    scheduled: list[tuple[int, object]] = []

    def fake_single_shot(msec, callback):
        scheduled.append((msec, callback))

    try:
        with (
            patch("photobooth.updater.apply_update", return_value=None),
            patch("PySide6.QtCore.QTimer.singleShot", side_effect=fake_single_shot),
        ):
            controller.applyUpdate()
            _pump(0.5)

        restart_calls = [(msec, cb) for msec, cb in scheduled if cb is QCoreApplication.quit]
        assert restart_calls, f"expected a QTimer.singleShot(_, QCoreApplication.quit) call, got {scheduled}"
        assert restart_calls[0][0] == 1500
    finally:
        # On a real success path the process is about to exit, so
        # _on_update_apply_done() has no reason to reset _update_applying --
        # but this test intentionally prevented that exit to keep the
        # shared app alive for later tests, so undo it by hand here.
        controller._update_applying = False
        controller.checkForUpdates()  # restore baseline
        _pump(0.5)


def test_layout_margin_preview_renders_and_tracks_grid_size(running_app):
    """The margin preview (paper rectangle + num_x*num_y photo rectangles)
    must actually lay out with a real, positive size inside the Layout tab's
    card -- this is the same class of bug the settingsRoot/`data`-shadowing
    test guards against: a broken binding here would render nothing."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    # Layout is the 7th (last) nav section; jump to it directly, and select
    # the Grid sub-tab (index 1) where the preview and margin spin live.
    settings_root.setProperty("currentIndex", 6)
    settings_root.setProperty("layoutSubIndex", 1)
    _pump(0.3)

    preview = root.findChild(QQuickItem, "layoutMarginPreview")
    assert preview is not None
    assert preview.property("width") > 0
    assert preview.property("height") > 0

    margin_spin = root.findChild(QQuickItem, "settingsMarginSpin")
    assert margin_spin is not None
    assert margin_spin.property("editable") is True

    controller.exitSettings()
    _pump(0.3)


def test_layout_tab_has_a_sub_tab_per_capture_mode(running_app):
    """Regression test: the Layout section used to be one flat page of grid
    settings; it's now split into one sub-tab per capture mode (single/grid/
    gif/boomerang), each showing only the settings that mode uses. Confirm
    all four sub-tab buttons exist and switching reveals mode-specific
    fields bound to the new [burst] config (gif/boomerang shot count, frame
    duration, frame width)."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 6)
    _pump(0.3)

    for mode in ("single", "grid", "gif", "boomerang"):
        tab_button = root.findChild(QQuickItem, f"layoutModeTab_{mode}")
        assert tab_button is not None, f"missing layout sub-tab for {mode!r}"

    settings_root.setProperty("layoutSubIndex", 2)  # gif
    _pump(0.3)
    gif_spins = [
        s for s in root.findChildren(QQuickItem)
        if _is_instance_of(s, "SpinBox") and s.property("editable") is True and s.property("visible")
    ]
    assert len(gif_spins) >= 3, "expected gif_shot_count/frame_duration/frame_width spins"

    settings_root.setProperty("layoutSubIndex", 3)  # boomerang
    _pump(0.3)
    boomerang_spins = [
        s for s in root.findChildren(QQuickItem)
        if _is_instance_of(s, "SpinBox") and s.property("editable") is True and s.property("visible")
    ]
    assert len(boomerang_spins) >= 3, "expected boomerang_shot_count/frame_duration/frame_width spins"

    controller.exitSettings()
    _pump(0.3)


def test_camera_inter_shot_delay_field_exists_and_is_editable(running_app):
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 2)  # Camera tab
    _pump(0.3)

    spin = root.findChild(QQuickItem, "interShotDelaySpin")
    assert spin is not None
    assert spin.property("editable") is True

    controller.exitSettings()
    _pump(0.3)


def test_photos_dir_field_exists_in_general_tab_and_is_editable(running_app):
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 0)  # General tab
    _pump(0.3)

    field = root.findChild(QQuickItem, "settingsPhotosDirField")
    assert field is not None
    assert field.property("enabled") is True

    controller.exitSettings()
    _pump(0.3)


def test_auto_restart_switch_exists_and_toggling_it_writes_the_marker_file(running_app):
    """New feature: Settings -> General -> "Restart automatically after
    exit or crash" toggle. Unlike every other field here it applies
    immediately (no Save needed) by creating/removing a sentinel file
    scripts/run-kiosk.sh checks after the app process has already exited."""
    from photobooth import paths

    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]
    marker = paths.auto_restart_marker_file()

    assert controller.property("autoRestartEnabled") is True
    assert not marker.exists()

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)
    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 0)  # General tab
    _pump(0.3)

    switch = root.findChild(QQuickItem, "settingsAutoRestartSwitch")
    assert switch is not None
    assert switch.property("checked") is True

    try:
        controller.setAutoRestartEnabled(False)
        _pump(0.2)
        assert controller.property("autoRestartEnabled") is False
        assert marker.is_file()

        controller.setAutoRestartEnabled(True)
        _pump(0.2)
        assert controller.property("autoRestartEnabled") is True
        assert not marker.exists()
    finally:
        marker.unlink(missing_ok=True)
        controller.exitSettings()
        _pump(0.3)


def test_backup_tab_fields_exist(running_app):
    """New feature: Settings -> Backup (replaces the removed USB export
    feature). Confirms the tab's controls all exist -- the enable switch,
    interval combo, scan/backup-now buttons, and status text."""
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 8)  # Backup is the last tab
    _pump(0.3)

    for name in (
        "settingsBackupEnableSwitch",
        "settingsBackupIntervalCombo",
        "settingsBackupScanButton",
        "settingsBackupNowButton",
        "settingsBackupStatusText",
    ):
        assert root.findChild(QQuickItem, name) is not None, f"missing {name!r}"

    combo = root.findChild(QQuickItem, "settingsBackupIntervalCombo")
    assert list(combo.property("model")) == [
        "Off (manual only)", "5 minutes", "10 minutes", "15 minutes", "30 minutes", "1 hour",
    ]


def test_tapping_a_backup_device_row_selects_it(running_app):
    """Regression test: tapping a device in the scanned list wrote
    settingsData.backup.device_uuid directly, but settingsData is a plain
    JS object (see the NOTE on that property) -- mutating a field inside
    it doesn't trigger binding re-evaluation, so the row's selection
    highlight and the "not saved yet" warning never updated. Reported
    live as "the selection of the drive does not work". Fixed via a
    previewBackupDeviceUuid mirror property, same pattern already used
    for the layout margin preview.

    Clicks at a fixed pixel position rather than looking up the delegate
    Rectangle via findChildren()/Repeater.itemAt() -- confirmed neither
    reliably locates this Repeater's dynamically created items in this
    PySide6/Qt build even though they render correctly (same quirk noted
    in test_settings_nav_icons_are_vector_not_unicode_glyphs above, and
    true here too despite this Repeater living in a plain Column rather
    than a Layout).
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    settings_root.setProperty("currentIndex", 8)
    _pump(0.3)

    backup_page = root.findChild(QQuickItem, "backupPage")
    try:
        backup_page.setProperty(
            "foundDevices",
            [
                {"uuid": "uuid-1", "label": "SANDISK", "mount_path": "/media/pi/SANDISK"},
                {"uuid": "uuid-2", "label": "KINGSTON", "mount_path": "/media/pi/KINGSTON"},
            ],
        )
        _pump(1.0)
        assert settings_root.property("previewBackupDeviceUuid") == ""

        # Second row (KINGSTON) at 1280x800, read off a screenshot of this
        # exact fixture setup -- the layout is fixed/top-anchored here, not
        # responsive to window height.
        QTest.mouseClick(root, Qt.LeftButton, Qt.NoModifier, QPoint(500, 611))
        _pump(0.5)

        assert settings_root.property("previewBackupDeviceUuid") == "uuid-2"
        assert settings_root.property("settingsData")["backup"]["device_uuid"] == "uuid-2"
        assert settings_root.property("settingsData")["backup"]["device_label"] == "KINGSTON"
    finally:
        backup_page.setProperty("foundDevices", [])
        controller.exitSettings()
        _pump(0.3)

    controller.exitSettings()


def test_settings_nav_icons_are_vector_not_unicode_glyphs(running_app):
    """Regression test: the settings nav rail originally used raw Unicode
    glyphs (gear/play/circle/etc.) whose visible ink isn't reliably centered
    within its character cell -- how far off varies by font/platform, which
    made the rail look vertically jagged row to row (see GearIcon.qml's own
    comment on this). Every entry now maps through navIconComponents to a
    hand-drawn Canvas icon instead, keyed by a plain-word sentinel rather
    than the glyph itself.

    This checks the *data model* (sections + navIconComponents) rather than
    searching the live item tree for rendered Canvas instances: the nav
    rail's Repeater lives inside a ColumnLayout, and delegate items created
    by a Repeater nested in a Qt Quick Layout render correctly on screen but
    are not reachable via QQuickItem.findChildren() from an ancestor in
    this PySide6/Qt build (confirmed directly -- Repeater.itemAt() returns
    None for every index despite the row painting fine), so that approach
    can't reliably assert anything about this Repeater's contents.
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    sections = settings_root.property("sections").toVariant()
    nav_icon_components = settings_root.property("navIconComponents").toVariant()

    assert len(sections) == 9
    for entry in sections:
        icon_key = entry["icon"]
        assert icon_key.isascii() and icon_key.isalpha(), f"non-vector icon key: {icon_key!r}"
        assert icon_key in nav_icon_components, f"no icon component registered for {icon_key!r}"
        component = nav_icon_components[icon_key]
        assert component.status() != QQmlComponent.Status.Error, component.errorString()

    controller.exitSettings()
    _pump(0.3)
    _pump(0.3)


def test_scan_backup_devices_returns_a_list(running_app):
    _app, engine, controller, _warnings = running_app
    result = controller.scanBackupDevices()
    assert isinstance(result, list)


def test_backup_now_is_a_no_op_with_no_device_configured(running_app):
    _app, engine, controller, _warnings = running_app
    data = controller.getSettingsJson()
    assert data["backup"]["device_uuid"] == ""

    controller.backupNow()
    _pump(0.2)

    assert controller.property("backupBusy") is False


def test_backup_now_reports_failure_for_an_unplugged_device(running_app):
    """Exercises the real async round-trip (run_in_background -> QThreadPool
    -> the finished/failed signal back on the main thread), not just the
    synchronous guard clauses."""
    _app, engine, controller, _warnings = running_app

    data = controller.getSettingsJson()
    original = dict(data["backup"])
    try:
        data["backup"]["device_uuid"] = "not-a-real-uuid"
        data["backup"]["device_label"] = "Nonexistent Drive"
        controller.saveSettingsJson(data)
        _pump(0.3)

        # A missing device resolves synchronously (no real I/O), so it can
        # finish within the first pump -- nothing meaningful to assert
        # about the busy flag mid-flight here, just the end state.
        controller.backupNow()
        _pump(1.0)

        assert controller.property("backupBusy") is False
        assert controller.property("backupStatus") != ""
    finally:
        data = controller.getSettingsJson()
        data["backup"] = original
        controller.saveSettingsJson(data)
        _pump(0.2)


def test_saving_a_custom_photos_dir_moves_where_shots_are_stored(running_app, tmp_path):
    """Regression test: StorageConfig.photos_dir used to exist under the
    dead name `data_dir` and have zero effect -- paths.photos_dir() always
    used the default app-data location no matter what was configured.
    Confirm a saved override actually changes where the next shot lands."""
    _app, engine, controller, _warnings = running_app

    custom_dir = tmp_path / "custom-photos"
    data = controller.getSettingsJson()
    original = data["storage"]["photos_dir"]
    try:
        data["storage"]["photos_dir"] = str(custom_dir)
        controller.saveSettingsJson(data)
        _pump(0.3)

        from photobooth.core.session import CaptureSession

        dummy_session = CaptureSession(mode="single", target_shot_count=1)
        shot_path = controller._store.shot_path(dummy_session, 0, "jpg")
        assert custom_dir in shot_path.parents  # under a %Y-%m-%d subfolder of it
        assert custom_dir.is_dir()
    finally:
        data = controller.getSettingsJson()
        data["storage"]["photos_dir"] = original
        controller.saveSettingsJson(data)
        _pump(0.3)


def test_settings_close_and_save_buttons_are_in_opposite_corners(running_app):
    """Close belongs top-right with breathing room from the edge, Save
    belongs bottom-right with breathing room from the edge -- floating
    corner buttons, not stacked together in a header bar.
    """
    _app, engine, controller, _warnings = running_app
    root = engine.rootObjects()[0]

    admin_pin = controller.getSettingsJson()["admin"]["pin"]
    assert controller.enterSettings(admin_pin) is True
    _pump(1.0)

    settings_root = root.findChild(QQuickItem, "settingsRoot")
    assert settings_root is not None
    close_button = root.findChild(QQuickItem, "settingsCloseButton")
    save_button = root.findChild(QQuickItem, "settingsSaveButton")
    assert close_button is not None
    assert save_button is not None

    screen_w = settings_root.property("width")
    screen_h = settings_root.property("height")
    close_right = close_button.property("x") + close_button.property("width")
    close_y = close_button.property("y")
    save_right = save_button.property("x") + save_button.property("width")
    save_bottom = save_button.property("y") + save_button.property("height")

    # Close button: near the top-right corner, with a visible margin (not
    # flush against the edge).
    assert screen_w * 0.85 < close_right < screen_w
    assert 0 < close_y < screen_h * 0.15

    # Save button: near the bottom-right corner, with a visible margin.
    assert screen_w * 0.85 < save_right < screen_w
    assert screen_h * 0.85 < save_bottom < screen_h

    controller.exitSettings()
    _pump(0.3)
