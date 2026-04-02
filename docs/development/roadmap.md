# Roadmap

See [ROADMAP.md](https://github.com/waydroid-toolkit/waydroid-toolkit/blob/main/docs/ROADMAP.md)
in the repository for the full roadmap with completion status.

## v0.1 — Foundation (complete)

- Core Waydroid interface (session state, config, shell)
- ADB bridge (connect, shell, push/pull, logcat, screenshot)
- Extension engine (GApps, microG, Magisk, libhoudini, libndk)
- Image profile management + OTA checker
- Backup/restore
- Performance tuning
- Qt/QML GUI skeleton

## v0.2 — Feature complete (complete)

- Widevine L3 extension
- Key mapper extension
- GUI file manager (push/pull)
- Android TV image profile support
- `MaintenanceBridge` screen recording slot + GUI
- Packaging: .deb, .rpm, AUR PKGBUILD, Flatpak
- Extension dependency resolution
- Snapshot support (ZFS/btrfs)
- D-Bus service mode
- Integration test suite
- Documentation site (MkDocs)

## v0.3 — Stable release (planned)

- Stable public API + PyPI release
- GitHub Actions CI (unit tests, lint, type check)
- Signed packages
- Wayland-native screenshot/record (no ADB dependency)
