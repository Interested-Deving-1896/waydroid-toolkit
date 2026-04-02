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

## v0.2 — Polish and completeness

- [x] Complete GApps extraction logic (OpenGApps pico + MindTheGapps)
- [x] OTA image update checker against waydro.id manifest format
- [x] `wdt images download` — fetch standard images from OTA server
- [x] GUI: Qt/QML Material interface replacing GTK4 skeleton
- [x] GUI: logcat viewer page with live streaming and filter UI
- [x] GUI: native adb shell terminal (fallback when WebEngine unavailable)
- [x] GUI: OTA check/download wired into Images page
- [x] Distro detection coverage: NixOS, Gentoo, Void, Alpine
- [x] `wdt maintenance record` — screen recording via `adb shell screenrecord`
- [ ] Widevine L3 extension
- [ ] Key mapper extension (gamepad/keyboard-to-touch input)
- [ ] GUI: file manager page (push/pull with file picker)
- [ ] GUI: screen recording slot in Maintenance page
- [ ] Packaging: `.deb`, `.rpm`, AUR PKGBUILD, Flatpak manifest

## v0.3 — Advanced features

- [ ] Android TV image profile support (auto-detect ATV images, set display props)
- [ ] Extension dependency resolution (auto-install `libhoudini` before `gapps`)
- [ ] Snapshot support — ZFS/btrfs subvolume snapshots of image profiles
- [ ] Multi-user support (per-user Waydroid instances)
- [ ] D-Bus service mode — expose toolkit operations over D-Bus
- [ ] GNOME Shell extension integration (status indicator, quick-launch)

## v1.0 — Stable release

- [ ] Stable public API for `modules/` (semver guarantees)
- [ ] Full documentation site (MkDocs)
- [ ] Automated CI with matrix testing across Debian, Ubuntu, Fedora, Arch
- [ ] Integration test suite (requires live Waydroid session)
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
