# waydroid-toolkit

Unified management suite for [Waydroid](https://github.com/waydroid/waydroid) — a container-based Android runtime for Linux.

waydroid-toolkit consolidates the fragmented ecosystem of Waydroid helper scripts, GUI managers, extension installers, and maintenance tools into a single project with a consistent CLI and optional Qt GUI.

## Features

| Module | What it does |
|---|---|
| **Extensions** | Install GApps, microG, Magisk, libhoudini, libndk, Widevine L3, key mapper with automatic dependency resolution |
| **Images** | Manage multiple system/vendor image profiles; auto-detect and configure Android TV images |
| **Snapshots** | Filesystem-level snapshots via ZFS or btrfs |
| **D-Bus** | Session-bus service exposing all toolkit operations to other processes |
| **Maintenance** | Screenshots, screen recording, logcat streaming, file transfer, debloat |
| **Backup** | Compressed tar.gz archives of all Waydroid data directories |
| **Packages** | Install APKs from local files or URLs; manage F-Droid repos |
| **Performance** | ZRAM, CPU governor, Turbo Boost, GameMode tuning |

## Quick install

```bash
pip install waydroid-toolkit          # CLI only
pip install "waydroid-toolkit[gui]"   # CLI + Qt GUI
```

## Quick start

```bash
wdt status
wdt extensions install gapps widevine
wdt images list
wdt snapshot create before-gapps
wdt maintenance screenshot
```

See [Getting Started](getting-started/installation.md) for full setup instructions.
