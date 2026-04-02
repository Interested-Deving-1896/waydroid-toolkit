# Changelog

All notable changes to waydroid-toolkit are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — unreleased

### Added

- **Widevine L3 extension** — installs Widevine DRM via vendor overlay;
  supports Android 11 and 13 zip variants.
- **Key mapper extension** — installs Key Mapper APK and configures a
  systemd user unit for the input daemon.
- **GUI file manager** — push/pull page in the Qt GUI backed by `FileBridge`.
- **Android TV image profile support** — `is_atv_profile()` detects ATV
  images via `debugfs` build.prop inspection (name heuristic fallback);
  `switch_profile()` auto-applies ATV display/input properties.
- **`MaintenanceBridge.startRecording` / `stopRecording`** — screen recording
  slots with `recording` property and `recordingSaved` signal; GUI row with
  duration spinner and stop button.
- **Packaging** — `.deb` (debhelper), `.rpm` (rpmbuild), AUR `PKGBUILD`,
  and Flatpak manifest; `pkg/build.sh` helper script.
- **Extension dependency resolver** (`modules/extensions/resolver.py`) —
  BFS dependency expansion, conflict detection, topological sort (Kahn's
  algorithm); `MissingDependencyError`, `ConflictError`, `CyclicDependencyError`.
- **`wdt extensions install`** now accepts multiple IDs and a `--dry-run`
  flag; new `wdt extensions deps` command.
- **Snapshot support** (`modules/snapshot/`) — `ZfsBackend` and
  `BtrfsBackend` with a common `SnapshotBackend` interface; auto-detection
  via `detect_backend()` / `get_backend()`; `wdt snapshot` CLI group.
- **D-Bus service mode** (`modules/dbus/`) — registers
  `io.github.waydroid_toolkit` on the session bus; exposes `GetStatus`,
  `ListProfiles`, `SwitchProfile`, `ListExtensions`, `InstallExtension`,
  `CreateSnapshot`, `ListSnapshots`, `Stop` methods and three signals;
  `wdt dbus` CLI group; D-Bus activation file and policy XML.
- **Integration test suite** — `tests/integration/` extended with
  `test_maintenance_integration.py`, `test_extensions_integration.py`,
  `test_images_integration.py`, `test_snapshot_integration.py`,
  `test_dbus_integration.py`; `integration` pytest marker; auto-skip when
  prerequisites are absent.
- **MkDocs documentation site** — `mkdocs.yml` with Material theme; full
  Getting Started, CLI reference, module reference, and development guides.
- **`py.typed` marker** — package is now typed; mypy can use inline types.

### Changed

- `wdt extensions install` signature changed from `EXTENSION_ID` (single)
  to `EXTENSION_IDS...` (one or more). Existing single-ID invocations
  continue to work.
- `MaintenanceBridge.captureScreenshot` now emits the path as a `str`
  (was `Path`).
- `pyproject.toml` version bumped to `0.2.0`.
- `pytest` markers `integration` and `slow` registered in `pyproject.toml`.
- `docs` optional dependency group added (`mkdocs`, `mkdocs-material`).

### Fixed

- `test_presenters.py` expected extension set updated to include `widevine`
  and `keymapper`.

## [0.1.0] — 2024-01-01

Initial release.

### Added

- Core Waydroid interface (`core.waydroid`): session state, config, shell.
- ADB bridge (`core.adb`): connect, shell, push/pull, logcat, screenshot.
- Extension engine: GApps, microG, Magisk, libhoudini, libndk.
- Image profile management + OTA checker (waydro.id manifest format).
- Backup/restore (compressed tar.gz).
- Performance tuning (ZRAM, CPU governor, Turbo Boost, GameMode).
- Qt/QML GUI skeleton with PySide6/PyQt6 compatibility shim.
- CLI (`wdt`) with status, install, build, gui, backend, extensions,
  images, packages, backup, performance, maintenance commands.
