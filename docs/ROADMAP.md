# WayDroid Toolkit — Roadmap

## v0.1 — Foundation ✅

- [x] Core runtime interface (`core.waydroid`, `core.adb`, `core.privilege`)
- [x] Extension engine with plugin base class and registry
- [x] Bundled extensions: GApps, microG, Magisk, libhoudini, libndk
- [x] Image profile manager with per-profile data isolation
- [x] Backup and restore
- [x] F-Droid repo management and APK install
- [x] Performance tuning (ZRAM, CPU governor, GameMode)
- [x] Maintenance tools (display, screenshot, logcat, file transfer, debloat)
- [x] Full CLI (`wdt`) with all subcommands
- [x] Unit test suite (519 tests)

## v0.2 — Feature complete ✅

- [x] Widevine L3 extension (vendor overlay, Android 11 + 13 variants)
- [x] Key mapper extension (APK install + systemd user unit)
- [x] GUI: file manager page (push/pull via `FileBridge`)
- [x] Android TV image profile support (`debugfs` detection, auto-apply
      display/input props on `switch_profile()`, `wdt images atv` commands)
- [x] `MaintenanceBridge` screen recording (`startRecording` / `stopRecording`
      slots, `recording` property, `recordingSaved` signal, GUI row)
- [x] Packaging: `.deb`, `.rpm`, AUR `PKGBUILD`, Flatpak manifest, `pkg/build.sh`
- [x] Extension dependency resolution (BFS expand, conflict detection,
      Kahn topological sort; `wdt extensions install` multi-ID + `--dry-run`;
      `wdt extensions deps`)
- [x] Snapshot support — `ZfsBackend`, `BtrfsBackend`, `SnapshotBackend` ABC,
      `detect_backend()` / `get_backend()`; `wdt snapshot` CLI group
- [x] D-Bus service mode (`io.github.waydroid_toolkit`; 8 methods, 3 signals;
      activation file + policy XML; `wdt dbus` CLI group)
- [x] Integration test suite (5 new files; `integration` marker; auto-skip
      when Waydroid / ADB / backend absent)
- [x] MkDocs documentation site (Material theme; 20 pages covering Getting
      Started, CLI reference, module reference, development guides)
- [x] Stable public API + PyPI release prep (`py.typed`, `__all__` audit,
      `CHANGELOG.md`, version 0.2.0, wheel 134 KiB)

## v0.3 — Stable release (planned)

- [ ] GitHub Actions CI extended: unit tests, lint, type-check on every
      push/PR; coverage for `wdt dbus`, `wdt snapshot`; integration test
      reporting
- [ ] Signed packages (GPG-signed `.deb` / `.rpm`, AUR `.sig`)
- [ ] Flatpak release on Flathub (real SHA256 sums, Flathub review)
- [ ] Wayland-native screenshot / screen record (no ADB dependency)
- [ ] `wdt dbus serve` systemd user unit template
- [ ] PyPI publish workflow (Trusted Publisher, GitHub release trigger)
- [ ] Signed releases on PyPI and distribution packages
- [ ] Migration guide from `casualsnek/waydroid_script` and `waydroid-helper`

---

## Upstream Relationship

WayDroid Toolkit does not intend to replace any upstream project. The goal is to
provide a single entry point for users who currently need to combine multiple tools.
Where upstream projects are actively maintained, WayDroid Toolkit defers to them:

- **`waydroid/waydroid`** — core runtime, never forked
- **`casualsnek/waydroid_script`** — extension asset URLs and overlay layout are
  compatible; users can migrate incrementally
- **`waydroid-helper/waydroid-helper`** — GTK4 GUI users can switch; the key mapper
  feature will be ported in v0.2
- **`waydroid/waydroid-package-manager`** — F-Droid repo format is compatible

Contributions that improve upstream projects directly are preferred over duplicating
logic here.
