"""Physical trigger button, exit button, lamp, and RGB LED ring.

A thin `gpiozero` wrapper, same pin-role model as the old app. Disabled by
default (`Gpio.enable = false`) so it's a no-op on machines without the
hardware (e.g. this dev environment). Button callbacks fire on gpiozero's
own background thread; since this is a QObject living on the main thread,
Qt automatically queues the signal emissions back to the main thread.

Wiring: all pin numbers are BCM GPIO numbering (see GpioConfig). Buttons
use gpiozero's default `pull_up=True` -- wire one leg to the GPIO pin and
the other to a GND pin on the header, no external pull resistor needed;
the button reads pressed when it pulls the pin low. The lamp and RGB LED
channels are active-high outputs (through a transistor/driver for
anything drawing more current than a GPIO pin can source directly).
gpiozero auto-selects its `lgpio`-backed pin factory on Raspberry Pi OS
(bookworm/trixie) since `lgpio` is installed alongside it -- no explicit
`Device.pin_factory` needed.
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
            # bounce_time debounces the raw contact bounce of a mechanical
            # button -- without it a single press can fire when_pressed
            # several times (e.g. double-starting a session).
            trigger_button = gpiozero.Button(self._config.trigger_pin, bounce_time=0.05)
            trigger_button.when_pressed = self.trigger_pressed.emit
            exit_button = gpiozero.Button(self._config.exit_pin, bounce_time=0.05)
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
