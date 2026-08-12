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

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem

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
    app = QGuiApplication([])
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

    gear_icons = [
        k for k in gear_button.findChildren(QQuickItem)
        if _is_instance_of(k, "Canvas")
    ]
    assert len(gear_icons) == 1, "expected exactly one Canvas-based GearIcon"
    assert gear_icons[0].property("visible") is True


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
    # Layout is the 7th (last) nav section; jump to it directly.
    settings_root.setProperty("currentIndex", 6)
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
