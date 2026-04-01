# WayDroid Toolkit — Roadmap

## v0.1 — Foundation (current)

- [x] Core runtime interface (`core.waydroid`, `core.adb`, `core.privilege`)
- [x] Extension engine with plugin base class and registry
- [x] Bundled extensions: GApps, microG, Magisk, libhoudini, libndk
- [x] Image profile manager with per-profile data isolation
- [x] Backup and restore
- [x] F-Droid repo management and APK install
- [x] Performance tuning (ZRAM, CPU governor, GameMode)
- [x] Maintenance tools (display, screenshot, logcat, file transfer, debloat)
- [x] Full CLI (`wdt`) with all subcommands
- [x] GTK4/Adwaita GUI skeleton with all seven pages
- [x] Unit test suite (52 tests)

## v0.2 — Polish and completeness

- [ ] Complete GApps extraction logic (currently stubs the unzip step)
- [ ] Widevine L3 extension (from `waydroid-androidtv-builds`)
- [ ] Key mapper for gamepad/keyboard-to-touch input (from `waydroid-helper`)
- [ ] OTA image update checker against `Amstel-DEV/ota` manifest format
- [ ] `wdt images download` — fetch standard/ATV images from OTA server
- [ ] GUI: logcat viewer page with live streaming and filter UI
- [ ] GUI: file manager page (push/pull with drag-and-drop)
- [ ] Distro detection coverage: NixOS, Gentoo, Void
- [ ] Integration test suite (requires live Waydroid)
- [ ] Packaging: `.deb`, `.rpm`, AUR PKGBUILD, Flatpak manifest

## v0.3 — Advanced features

- [ ] Android TV image profile support (auto-detect ATV images, set correct display props)
- [ ] Multi-user support (per-user Waydroid instances)
- [ ] Extension dependency resolution (auto-install `libhoudini` before `gapps` if needed)
- [ ] Snapshot support — ZFS/btrfs subvolume snapshots of image profiles
- [ ] `wdt maintenance record` — screen recording with audio via `adb shell screenrecord`
- [ ] D-Bus service mode — expose toolkit operations over D-Bus for desktop integration
- [ ] GNOME Shell extension integration (status indicator, quick-launch)

## v1.0 — Stable release

- [ ] Stable public API for `modules/` (semver guarantees)
- [ ] Full documentation site
- [ ] Automated CI with matrix testing across Debian, Ubuntu, Fedora, Arch
- [ ] Signed releases on PyPI and distribution packages
- [ ] Migration guide from `casualsnek/waydroid_script` and `waydroid-helper`

---

## Upstream Relationship

WayDroid Toolkit does not intend to replace any upstream project. The goal is to provide a single entry point for users who currently need to combine multiple tools. Where upstream projects are actively maintained, WayDroid Toolkit defers to them:

- **`waydroid/waydroid`** — core runtime, never forked
- **`casualsnek/waydroid_script`** — extension asset URLs and overlay layout are compatible; users can migrate incrementally
- **`waydroid-helper/waydroid-helper`** — GTK4 GUI users can switch; the key mapper feature will be ported in v0.2
- **`waydroid/waydroid-package-manager`** — F-Droid repo format is compatible

Contributions that improve upstream projects directly are preferred over duplicating logic here.
