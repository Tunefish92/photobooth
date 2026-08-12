"""Physical trigger button, exit button, lamp, and RGB LED ring.

A thin `gpiozero` wrapper, same pin-role model as the old app. Disabled by
default (`Gpio.enable = false`) so it's a no-op on machines without the
hardware (e.g. this dev environment). Button callbacks fire on gpiozero's
own background thread; since this is a QObject living on the main thread,
Qt automatically queues the signal emissions back to the main thread.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from photobooth.config.settings import GpioConfig

logger = logging.getLogger(__name__)


class GpioController(QObject):
    trigger_pressed = Signal()
    exit_pressed = Signal()

    def __init__(self, config: GpioConfig) -> None:
        super().__init__()
        self._config = config
        self._enabled = False
        self._lamp = None
        self._rgb = None

        if config.enable:
            self._init_hardware()

    def _init_hardware(self) -> None:
        try:
            import gpiozero
        except ImportError:
            logger.warning("Gpio.enable=true but gpiozero is not available; GPIO disabled")
            return

        try:
            trigger_button = gpiozero.Button(self._config.trigger_pin)
            trigger_button.when_pressed = self.trigger_pressed.emit
            exit_button = gpiozero.Button(self._config.exit_pin)
            exit_button.when_pressed = self.exit_pressed.emit
            self._lamp = gpiozero.LED(self._config.lamp_pin)
            self._rgb = gpiozero.RGBLED(
                self._config.chan_r_pin, self._config.chan_g_pin, self._config.chan_b_pin
            )
            self._buttons = [trigger_button, exit_button]
            self._enabled = True
            logger.info("GPIO enabled")
        except Exception:
            logger.exception("Failed to initialize GPIO hardware; continuing without it")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def lamp_on(self) -> None:
        if self._lamp is not None:
            self._lamp.on()

    def lamp_off(self) -> None:
        if self._lamp is not None:
            self._lamp.off()

    def rgb_color(self, r: float, g: float, b: float) -> None:
        if self._rgb is not None:
            self._rgb.color = (r, g, b)

    def rgb_off(self) -> None:
        if self._rgb is not None:
            self._rgb.off()

    def teardown(self) -> None:
        if self._lamp is not None:
            self._lamp.off()
        if self._rgb is not None:
            self._rgb.off()
