"""Typed, validated application settings.

Defaults ship in `defaults.toml` next to this module. A user override file
(see `photobooth.paths.user_config_file`) is deep-merged on top when present,
and the Settings admin screen writes back to that same file.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any, Literal

import tomlkit
from pydantic import BaseModel, Field, field_validator, model_validator

CameraBackendName = Literal["auto", "gphoto2", "picamera2", "opencv", "dummy"]
PrinterBackendName = Literal["cups", "pdf"]
CaptureMode = Literal["single", "grid", "gif", "boomerang"]
FilterName = Literal["none", "bw", "sepia", "vintage", "vivid"]
ThemeName = Literal["aurora-dark", "aurora-light", "ocean-blue", "forest-green", "prism-modern"]


class AppConfig(BaseModel):
    fullscreen: bool = True
    width: int = 1280
    height: int = 800
    hide_cursor: bool = True
    theme: ThemeName = "aurora-dark"
    language: str = "en"


class CameraConfig(BaseModel):
    backend: CameraBackendName = "auto"
    rotation: Literal[0, 90, 180, 270] = 0
    mirror_preview: bool = True
    opencv_device_index: int = 0
    # Delay before each shot after the first one in a multi-shot session
    # (grid/gif/boomerang); the first shot always uses flow.countdown_time_s.
    inter_shot_delay_s: float = Field(default=1.0, ge=0)


class GpioConfig(BaseModel):
    # BCM numbering, 2-27: the range actually broken out on the 40-pin
    # header. GPIO0/1 are excluded even though they're physically present
    # (as ID_SD/ID_SC) -- they're reserved for HAT EEPROM identification at
    # boot and shouldn't be repurposed for general I/O.
    enable: bool = False
    exit_pin: int = Field(default=24, ge=2, le=27)
    trigger_pin: int = Field(default=23, ge=2, le=27)
    lamp_pin: int = Field(default=4, ge=2, le=27)
    chan_r_pin: int = Field(default=27, ge=2, le=27)
    chan_g_pin: int = Field(default=22, ge=2, le=27)
    chan_b_pin: int = Field(default=17, ge=2, le=27)

    @model_validator(mode="after")
    def _pins_must_be_distinct(self) -> "GpioConfig":
        # gpiozero raises GPIOPinInUse the moment a second role tries to
        # claim an already-reserved pin -- caught by the broad except in
        # GpioController._init_hardware() and logged, but that leaves every
        # GPIO feature (trigger, exit, lamp, RGB) silently dead with no
        # indication in the UI of why. Catch the misconfiguration here
        # instead, at the config boundary, with a message that actually
        # says what's wrong.
        pins = {
            "exit_pin": self.exit_pin,
            "trigger_pin": self.trigger_pin,
            "lamp_pin": self.lamp_pin,
            "chan_r_pin": self.chan_r_pin,
            "chan_g_pin": self.chan_g_pin,
            "chan_b_pin": self.chan_b_pin,
        }
        seen: dict[int, str] = {}
        for name, pin in pins.items():
            if pin in seen:
                raise ValueError(f"{name} and {seen[pin]} can't both use GPIO{pin}")
            seen[pin] = name
        return self


class PrinterConfig(BaseModel):
    enable: bool = True
    backend: PrinterBackendName = "cups"
    cups_printer_name: str = "Canon_SELPHY_CP1300"
    confirmation: bool = True
    paper_width_mm: int = Field(default=148, gt=0)
    paper_height_mm: int = Field(default=100, gt=0)


class FlowConfig(BaseModel):
    show_preview: bool = True
    greeter_time_s: float = Field(default=3, ge=0)
    countdown_time_s: float = Field(default=3, ge=0)
    display_time_s: float = Field(default=6, ge=0)
    postprocess_time_s: float = Field(default=60, ge=0)
    default_mode: CaptureMode = "single"
    enabled_modes: list[CaptureMode] = Field(
        default_factory=lambda: ["single", "grid", "gif", "boomerang"]
    )

    @field_validator("enabled_modes")
    @classmethod
    def _at_least_one_mode_enabled(cls, value: list[CaptureMode]) -> list[CaptureMode]:
        # The idle screen's mode picker has nothing to show (and GPIO/API
        # start() calls have nothing valid to fall back to) if every mode is
        # disabled -- the Settings UI also guards against unchecking the
        # last one, but this is the authoritative check for any writer.
        if not value:
            raise ValueError("At least one photo mode must stay enabled")
        return value


class LayoutConfig(BaseModel):
    num_x: int = Field(default=2, gt=0)
    num_y: int = Field(default=2, gt=0)
    size_x: int = Field(default=3496, gt=0)
    size_y: int = Field(default=2362, gt=0)
    inner_dist_x: int = Field(default=20, ge=0)
    inner_dist_y: int = Field(default=20, ge=0)
    outer_dist_x: int = Field(default=40, ge=0)
    outer_dist_y: int = Field(default=40, ge=0)
    skip: list[int] = Field(default_factory=list)
    background: str = ""
    overlay: str = ""


class BurstConfig(BaseModel):
    """Shot count and output size for the animated ("gif"/"boomerang")
    modes -- the equivalent of LayoutConfig's num_x/num_y/size_x/size_y for
    the modes that don't go through the grid compositor."""

    gif_shot_count: int = Field(default=6, gt=0)
    gif_frame_duration_ms: int = Field(default=150, gt=0)
    gif_frame_max_width_px: int = Field(default=900, gt=0)
    boomerang_shot_count: int = Field(default=12, gt=0)
    boomerang_frame_duration_ms: int = Field(default=80, gt=0)
    boomerang_frame_max_width_px: int = Field(default=900, gt=0)


class EffectsConfig(BaseModel):
    enabled_filters: list[FilterName] = Field(
        default_factory=lambda: ["none", "bw", "sepia", "vintage", "vivid"]
    )
    default_filter: FilterName = "none"
    chroma_key_enabled: bool = False
    chroma_key_color: tuple[int, int, int] = (0, 177, 64)
    chroma_key_background: str = ""


class StorageConfig(BaseModel):
    basedir: str = "%Y-%m-%d"
    basename: str = "photobooth"
    keep_pictures: bool = True
    # Absolute path to store photos under, e.g. a mounted external drive.
    # Empty (the default) uses the platform's standard app-data location
    # (see photobooth.paths.photos_dir).
    photos_dir: str = ""


class MailerConfig(BaseModel):
    enable: bool = False
    sender: str = "photobooth@example.com"
    recipient: str = "photobooth@example.com"
    subject: str = "Your photobooth picture"
    message: str = "Sent by the photobooth"
    server: str = "localhost"
    port: int = 587
    use_auth: bool = True
    user: str = ""
    password: str = ""
    use_tls: bool = True


class WebdavConfig(BaseModel):
    enable: bool = False
    url: str = "https://example.com/remote.php/webdav/Photobooth/"
    use_auth: bool = True
    user: str = ""
    password: str = ""


class UsbExportConfig(BaseModel):
    enable: bool = True
    auto_detect: bool = True


class AdminConfig(BaseModel):
    pin: str = "1234"


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    gpio: GpioConfig = Field(default_factory=GpioConfig)
    printer: PrinterConfig = Field(default_factory=PrinterConfig)
    flow: FlowConfig = Field(default_factory=FlowConfig)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    burst: BurstConfig = Field(default_factory=BurstConfig)
    effects: EffectsConfig = Field(default_factory=EffectsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    mailer: MailerConfig = Field(default_factory=MailerConfig)
    webdav: WebdavConfig = Field(default_factory=WebdavConfig)
    usb_export: UsbExportConfig = Field(default_factory=UsbExportConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_defaults_dict() -> dict[str, Any]:
    text = resources.files("photobooth.config").joinpath("defaults.toml").read_text("utf-8")
    return tomlkit.parse(text).unwrap()


def load_settings(user_config_path: Path | None = None) -> Settings:
    data = _load_defaults_dict()

    if user_config_path is not None and user_config_path.is_file():
        override_text = user_config_path.read_text("utf-8")
        override = tomlkit.parse(override_text).unwrap()
        data = _deep_merge(data, override)

    return Settings.model_validate(data)


def save_settings(settings: Settings, user_config_path: Path) -> None:
    user_config_path.parent.mkdir(parents=True, exist_ok=True)
    doc = tomlkit.document()
    for section, value in settings.model_dump(mode="json").items():
        table = tomlkit.table()
        for k, v in value.items():
            table[k] = v
        doc[section] = table
    user_config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
