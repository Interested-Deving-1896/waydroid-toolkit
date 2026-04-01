# WayDroid Toolkit

Unified management suite for [Waydroid](https://github.com/waydroid/waydroid) — a container-based Android runtime for Linux.

WayDroid Toolkit consolidates the fragmented ecosystem of Waydroid helper scripts, GUI managers, extension installers, and maintenance tools into a single project with a consistent CLI and GTK4 GUI.

## Features

| Module | What it does |
|---|---|
| **Installer** | Installs Waydroid on Debian, Ubuntu, Fedora, Arch, openSUSE and runs `waydroid init` |
| **Extensions** | Installs GApps, microG, Magisk, libhoudini, libndk into the overlay filesystem |
| **Images** | Manages multiple system/vendor image profiles with per-profile data isolation |
| **Packages** | Installs APKs from local files or URLs; manages F-Droid repos |
| **Backup** | Creates and restores compressed archives of all Waydroid data directories |
| **Performance** | Configures ZRAM, CPU governor, Turbo Boost, and GameMode for gaming |
| **Maintenance** | Display settings, screenshots, screen recording, logcat, file transfer, debloat |

## Installation

```bash
pip install waydroid-toolkit          # CLI only
pip install "waydroid-toolkit[gui]"   # CLI + GTK4 GUI
```

System requirements for the GUI: `libgtk-4` and `libadwaita` ≥ 1.4.

## Usage

### CLI

```bash
wdt status                            # show runtime state
wdt install --image-type GAPPS        # install Waydroid with GApps image
wdt extensions list                   # list available extensions
wdt extensions install libhoudini     # install ARM translation
wdt extensions install magisk         # install Magisk
wdt images list                       # list image profiles
wdt images switch androidtv           # switch to Android TV profile
wdt packages install /path/to/app.apk
wdt packages repo add fdroid https://f-droid.org/repo
wdt backup create
wdt backup restore waydroid_backup_20240101_120000.tar.gz
wdt performance apply --zram-size 8192 --governor performance
wdt maintenance screenshot
wdt maintenance logcat --errors
wdt maintenance debloat
```

### GUI

```bash
waydroid-toolkit
```

## Architecture

```
src/waydroid_toolkit/
├── core/           # Waydroid runtime interface, ADB, privilege helpers
├── modules/
│   ├── installer/  # Cross-distro package install + waydroid init
│   ├── extensions/ # Plugin engine: GApps, microG, Magisk, ARM translation
│   ├── images/     # Image profile manager
│   ├── packages/   # APK install, F-Droid repo management
│   ├── backup/     # Backup and restore
│   ├── performance/# ZRAM, CPU governor, GameMode
│   └── maintenance/# Display, ADB tools, debloat
├── cli/            # Click-based CLI (wdt)
├── gui/            # GTK4/Adwaita GUI (waydroid-toolkit)
└── utils/          # Distro detection, networking, overlay helpers
```

The CLI and GUI are thin layers over the modules. All business logic lives in `modules/` and `core/`, making it straightforward to add new frontends (TUI, D-Bus service, etc.).

## Upstream Projects

WayDroid Toolkit integrates concepts and techniques from the following projects:

| Project | Role in WayDroid Toolkit |
|---|---|
| [waydroid/waydroid](https://github.com/waydroid/waydroid) | Core runtime — not modified, called via CLI/DBus |
| [casualsnek/waydroid_script](https://github.com/casualsnek/waydroid_script) | Extension install approach, overlay layout, asset URLs |
| [waydroid-helper/waydroid-helper](https://github.com/waydroid-helper/waydroid-helper) | GTK4 GUI patterns, key mapper concept |
| [Nigel1992/Waydroid-Advanced-Manager](https://github.com/Nigel1992/Waydroid-Advanced-Manager) | ADB tool set (screenshot, logcat, file transfer) |
| [amir0zx/waydroid-image-sw](https://github.com/amir0zx/waydroid-image-sw) | Image profile switching with data isolation |
| [berndhofer/waybak](https://github.com/berndhofer/waybak) | Backup/restore directory layout |
| [lil-xhris/Waydroid-boost-](https://github.com/lil-xhris/Waydroid-boost-) | ZRAM + CPU governor tuning approach |
| [waydroid/waydroid-linux_tools](https://github.com/waydroid/waydroid-linux_tools) | Debloater package list, Plymouth integration |
| [waydroid/waydroid-package-manager](https://github.com/waydroid/waydroid-package-manager) | F-Droid repo management model |
| [mistrmochov/WaydroidSU](https://github.com/mistrmochov/WaydroidSU) | Magisk lifecycle management |
| [Amstel-DEV/ota](https://github.com/Amstel-DEV/ota) | OTA image manifest format |
| [n1lby73/waydroid-installer](https://github.com/n1lby73/waydroid-installer) | Cross-distro install logic |

## Development

```bash
git clone https://github.com/your-org/waydroid-toolkit
cd waydroid-toolkit
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/unit/
```

## License

GPL-3.0 — consistent with Waydroid and the majority of the upstream projects this integrates.
