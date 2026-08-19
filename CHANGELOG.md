# Changelog

All notable changes to this project are documented in this file.

## [1.2.0] - 2026-08-19

### UI

- The review screen ("Retake"/"Looks great!") now shows a live seconds
  counter above the buttons, counting down to when it auto-advances to
  the postprocess screen -- that timeout previously fired with no visible
  warning at all.

### Camera

- New "Camera battery" row in Settings -> Camera, where available.
  `gphoto2` exposes a battery-level PTP config widget on most Canon/Nikon
  DSLR/mirrorless bodies; the row only appears once a level is actually
  known, so webcams, the Pi camera module, and gphoto2-supported cameras
  that don't expose battery status (or are on AC power) just don't show
  it, rather than displaying a bogus value.

## [1.1.2] - 2026-08-19

### Fixed

- Removed the postprocess screen's hidden auto-return-to-idle timeout.
  Staying on "What would you like to do?" for longer than 60 seconds
  silently finished the session and dropped the guest back on the tile
  grid -- there was no UI to even see this setting existed, let alone
  disable it. The only way off this screen now is an explicit action
  (Print, Email, Upload, or Done), same as every other screen.

### UI

- Idle screen subtitle changed from "Touch anywhere to start" to "Select
  mode below" -- more accurate, since tapping the background does
  nothing; only the mode tiles are interactive.

### Translations

- Audited every user-facing string in the app for translation coverage.
  No gaps found: every `Translator.tr()` call site across every `.qml`
  file already resolves in both English and German (enforced by an
  existing catalog-wide test), and no hardcoded natural-language text
  bypasses the translator anywhere in the UI.

## [1.1.1] - 2026-08-19

### Fixed

- **Background actions (Print, Email, WebDAV upload, Backup) could silently
  hang or crash the app.** `run_in_background()` started its task on the
  Qt thread pool but kept no Python reference to it afterward -- it could
  be garbage-collected while the worker thread was still running or about
  to deliver its result, either silently dropping the completion signal
  (busy indicator stuck forever, no confirmation toast) or crashing on a
  use-after-free from the worker thread. Reported live as: hit Yes on the
  print confirmation, the app closes. Now holds a reference for the
  task's whole lifetime, released only once its result has actually been
  delivered.
- Settings -> Backup: tapping a device in the scanned list didn't visibly
  select it. The tap correctly staged the choice, but wrote it into a
  field of a plain JS object that QML doesn't watch for changes, so
  neither the row's highlight nor the "not saved yet" warning ever
  updated -- looked like the click did nothing. Fixed with the same
  reactive-mirror pattern already used for the layout margin preview.
- Postprocess screen ("What would you like to do?"): the action buttons
  (Print/Email/Upload/Done) are now one row, all the same size, centered
  as a group -- Done used to sit stacked below the others at a different
  width, both left-aligned.

## [1.1.0] - 2026-08-18

### UI

- Replaced the remaining settings nav-rail Unicode glyphs (gear, play,
  circle, printer, arrow, power, grid, repeat symbols) with hand-drawn
  vector icons -- the same class of fix already applied to the idle screen
  and the gear/exit/close icons in v1.0.0. Font glyph ink isn't reliably
  centered within its own character cell, and how far off varies by symbol
  and font, which made the nav rail look vertically jagged row to row.
  Added three new icons (Photo Modes, Printer, Sharing) and reused existing
  ones (General, Camera, Layout, Update, GPIO) where they already fit.

### Backup (new)

- New Settings -> Backup tab, replacing per-photo USB export
  ("Save to USB" on the postprocess screen, `UsbExportConfig`): copies
  every photo folder under the configured photo directory plus a
  consistent SQLite snapshot (via `sqlite3`'s own backup API, not a raw
  file copy -- the database can be open and being written to by the
  running app) onto a selected removable drive.
  - **Incremental**: a file already on the drive with a matching size and
    an as-new-or-newer mtime is left alone, so repeat backups (especially
    the scheduled automatic ones) only copy what's actually new.
  - **A kind of versioning**: each run appends one line to a JSON-lines
    manifest on the drive (timestamp, files copied/skipped, bytes) --
    lightweight backup history without the complexity, or FAT32/exFAT
    incompatibility (most USB sticks are formatted one of those, and
    neither supports hardlinks), of true per-run snapshots.
  - **The device is remembered by filesystem UUID, not mount path** --
    Raspberry Pi OS mounts removable drives under `/media/<user>/<label>`,
    a path that changes with the label or which USB port it's in. Picking
    a drive in Settings resolves and stores its UUID (via
    `/dev/disk/by-uuid`); backups later re-resolve wherever that UUID is
    *currently* mounted, so a replug or reboot doesn't lose track of which
    physical drive was chosen.
  - **Manual or scheduled**: a "Backup now" button, plus an optional
    auto-backup interval (5/10/15/30 minutes or 1 hour) run by its own
    timer independent of whatever the kiosk is doing.

### Tests

- Added coverage for the backup module: device UUID resolution surviving a
  simulated replug, incremental copy skip/recopy behavior, the SQLite
  snapshot being a real independent copy, and the full async round-trip
  through `backupNow()`.

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
  - Fixed the in-app updater failing with `'uv' executable not found on
    PATH, ~/.local/bin, or ~/.cargo/bin`: the whole script runs under
    `sudo`, so `uv` was getting installed into *root's* home
    (`/root/.local/bin`) and `.venv` was created root-owned, even though
    both the app and its updater run as the target user afterwards and
    look in *that* user's home. `uv`'s install, the venv creation, and
    the initial `uv sync` now all run as the target user via `sudo -u`;
    a leftover root-owned `.venv` from an earlier run of the old script
    is detected and recreated automatically.

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
- New "Photo directory" field in Settings -> General: an absolute path
  (e.g. a mounted USB drive) to store photos under instead of the default
  app-data location. This repurposes `StorageConfig`'s old `data_dir`
  field, which existed but was never actually read anywhere.
- New "Restart automatically after exit or crash" toggle in Settings ->
  General. `scripts/run-kiosk.sh`'s restart loop couldn't previously be
  turned off -- exiting via the on-screen Exit button just relaunched the
  kiosk again a couple seconds later, with no way to actually leave it
  closed. Unlike every other setting on this screen it applies
  immediately (no Save needed): it leaves/removes a sentinel file the
  wrapper script checks after the app process has already exited, so it
  takes effect from the next exit onward rather than the current session.
- Tapping a mode tile on the idle screen no longer starts a session
  immediately -- it opens a confirmation screen titled with the selected
  mode (with that mode's icon) and a Start button, with a Back button to
  return to the tile grid. The physical GPIO trigger button is equivalent
  to that Start button while the confirmation screen is showing; from the
  idle tile grid (no mode selected yet) it does nothing (see GPIO below --
  this replaced an earlier "shortcut straight to `flow.default_mode`"
  behavior, which turned out not to be wanted).
- Finishing a session normally (Done on the postprocess screen) now
  returns to that same mode's confirmation screen instead of the tile
  grid -- one tap for another round of the same mode, the common case at
  a live event. An aborted/errored session still falls through to the
  tile grid, and Retake was never affected (it goes straight back to the
  countdown for another attempt at the same session, never touching the
  idle screen at all).

### GPIO

- **Fixed GPIO not working at all** on a fresh `install.sh` provision:
  the target user was never added to the `gpio` group, which Raspberry
  Pi OS's udev rules require for `/dev/gpiomem` access -- `gpiozero`
  silently failed to initialize (a broad exception handler around
  hardware init just logs and continues), so every GPIO feature (trigger
  button, exit button, lamp, RGB LED) did nothing, with no visible error
  anywhere in the UI.

- The GPIO trigger button no longer has a "no mode selected" fallback to
  `flow.default_mode` -- it now only acts as the confirmation screen's
  Start button, and does nothing at all from the idle tile grid.

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
- Audited WebDAV's request handling -- already correct, no changes
  needed.

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
