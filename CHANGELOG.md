# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-08-15

First stable release. Everything below shipped since v0.1.0 (Beta), driven
largely by provisioning a real Pi 4 end-to-end for the first time.

### Raspberry Pi deployment

- **Switched the kiosk from a console/eglfs setup to a desktop-autostarted
  window.** The direct-framebuffer (`eglfs`) approach, run as a plain
  systemd service, kept losing the fight for DRM master (`EACCES` on the
  cursor plane, `EGL_BAD_MATCH` creating the surface) even after attaching
  it to a real VT/PAM session -- it just isn't reliable outside of an
  interactive login. The app now runs as an ordinary fullscreen window
  under the Pi's own Wayland desktop session (`labwc`), autostarted via an
  XDG entry (`scripts/photobooth.desktop` + `scripts/run-kiosk.sh`, which
  also replaces systemd's `Restart=always` with its own restart loop), with
  the Pi set to boot straight to Desktop with auto-login. **This means the
  Pi now needs the Desktop Raspberry Pi OS image, not Lite.**
- Added a visible Desktop shortcut alongside the (menu-hidden) autostart
  entry, so the app can be launched/relaunched by hand without a terminal.
- Fixed `install.sh` for current Raspberry Pi OS (trixie):
  - `ippusbxd` was dropped from Debian's repos (unmaintained, replaced by
    `ipp-usb`) -- swapped the package.
  - Added `swig` and `liblgpio-dev`, both required to compile the `lgpio`
    Python package's C extension; the build previously failed with
    `command 'swig' failed` and then `cannot find -llgpio`.

### UI

- Replaced the idle screen's Unicode/emoji icons (camera, grid, film,
  repeat, power) with hand-drawn vector icons. The emoji glyphs rendered as
  blank boxes on a minimal Pi desktop install with no emoji-capable font --
  the same class of problem already solved for the settings gear icon.
  Also fixed a geometry bug in the boomerang/power icons themselves (a
  Canvas arc-angle mixup put the ring's gap on the wrong side of the
  circle, rendering as a broken hook instead of a clean loop/power shape),
  and converted the Settings close button's "✕" glyph the same way.
- Settings -> Layout is now one tab per capture mode (Photo/Grid/GIF/
  Boomerang) instead of a single flat page of grid-specific fields. Photo
  and Grid still share the underlying output size/margin/background/
  overlay config; GIF and Boomerang gained new settings (shot count, frame
  duration, frame width) that were previously hardcoded and not
  configurable at all.
- **Themes actually work now.** The Settings -> General theme picker had
  no effect at all -- `main.qml` hardcoded `Theme.dark = true` at startup
  and never read the saved `app.theme`. Fixed, and expanded from the two
  Aurora (dark/light) variants to five: Aurora Dark, Aurora Light, Ocean
  Blue, Forest Green, and Prism Modern (a bold, saturated magenta/violet/
  cyan look, in contrast to the other themes' restrained pastel accents).
  Takes effect on Save, same as the language setting.

### GPIO

- Hardened `GpioConfig` against two previously-silent misconfigurations:
  pins outside the 40-pin header's usable BCM2-27 range (0/1 are reserved
  for HAT EEPROM ID) and two roles sharing the same pin (`gpiozero` raises
  `GPIOPinInUse` the instant a second device claims an already-reserved
  pin, which the broad exception handler around hardware init swallowed,
  silently disabling every GPIO feature with nothing but a log line
  explaining why). Both are now rejected at the config boundary. Also
  added button debounce (a mechanical button without it can fire multiple
  press events per physical press).

### Sharing

- Fixed email sending on SMTP servers that use implicit TLS (port 465,
  as opposed to the far more common port 587 STARTTLS): the mailer always
  used plain `SMTP` + `starttls()`, which sends a plaintext `EHLO` into a
  TLS handshake and fails on port 465. Now uses `SMTP_SSL` for that case.
- Audited USB export's Pi auto-mount assumptions (`/media/<user>/<label>`
  and `/run/media/<user>/<label>`, covering both older and newer `udisks2`
  conventions) and WebDAV's request handling -- both already correct, no
  changes needed there.

### Dev tooling

- Added `scripts/run-windows.bat` for a one-click local dev run on Windows.

### Tests

- Added coverage that didn't exist before: the email and WebDAV sharing
  backends (mocked `smtplib`/`httpx`, no live server needed), GPIO pin
  range/uniqueness validation, the theme system end-to-end (selecting and
  saving a theme actually changes the live `Theme` singleton), and a
  catalog-wide sweep confirming every `Translator.tr()` call site across
  every `.qml` file resolves in both languages (not just Settings screen
  fields, which was the only thing previously checked).

## [0.1.0] - 2026-08-12 (Beta)

First tagged release of the photobooth kiosk app.

### UI

- Modern, elegant redesign: softer light-accent palette, abstract ambient
  background, card-style Settings navigation on the right instead of
  horizontal tabs, bigger and responsive field text
- New app icon: a simple camera glyph on the app's own signature gradient
- New "Photo Modes" Settings tab -- toggle which capture modes (single/
  grid/GIF/boomerang) show up on the idle screen, with a guard against
  disabling every mode
- New Layout margin control with a live, proportionally-accurate preview
  (paper + grid, unstretched)
- New configurable delay between shots in multi-shot sessions (grid/GIF/
  boomerang), separate from the first-shot countdown
- New exit button (with confirmation dialog) on the idle screen
- All Settings input fields now share a consistent width
- Settings gear icon is now a small vector-drawn icon instead of a
  Unicode glyph, so it's centered by construction regardless of font/
  platform quirks
- UI limited to English/German, with full translation coverage

### In-app updates

- New "Update" Settings tab and a small idle-screen badge: checks GitHub
  Releases for a newer version and can check it out + re-sync dependencies
  in place
- Fixed the update check 404ing in production when every release is a
  prerelease, by using the releases list endpoint instead of
  `/releases/latest`

### Raspberry Pi provisioning

- Installs the build toolchain and Qt6/EGLFS runtime libraries PySide6
  needs
- Installs `printer-driver-gutenprint` and driverless CUPS support for the
  Canon SELPHY CP1300/CP1500
- Uses `uv sync` against the committed `uv.lock` for reproducible installs

### Robustness

- Config validation rejects zero/negative values for fields that feed
  directly into image-compositing math or Qt timer durations
- Camera backend selection catches an unrecognized backend name and
  degrades to the dummy backend instead of crashing

### Docs

- README rewritten with detailed Windows (edit/debug only) and Raspberry
  Pi (the real runtime target) setup instructions
- Screenshots of the idle screen and every Settings tab

### Tests

- 126 tests: state machine, image compositor, config validation, camera/
  printer backend factory fallback, storage, USB export, translation-
  catalog parity, the update checker, and headless QML smoke tests
