# Architecture

## Source layout

```
src/waydroid_toolkit/
├── __init__.py              # version
├── cli/
│   ├── main.py              # Click group, command registration
│   └── commands/            # one file per top-level command group
├── core/
│   ├── adb.py               # ADB connection + shell/push/pull/logcat
│   ├── waydroid.py          # waydroid CLI wrapper, WaydroidConfig
│   └── privilege.py         # sudo/polkit helpers
├── gui/
│   ├── app.py               # Qt application entry point
│   ├── bridge.py            # QObject bridges (Python ↔ QML)
│   ├── qt_compat.py         # PySide6/PyQt6 shim
│   └── qml/                 # QML pages and components
├── modules/
│   ├── backup/              # tar.gz backup/restore
│   ├── dbus/                # D-Bus service
│   ├── extensions/          # extension plugins + resolver
│   ├── images/              # profile management, OTA, ATV detection
│   ├── maintenance/         # display, screenshot, record, logcat, files
│   ├── packages/            # APK install, F-Droid
│   ├── performance/         # ZRAM, governor, GameMode
│   └── snapshot/            # ZFS/btrfs snapshots
└── utils/                   # shared helpers (net, distro, overlay, …)
```

## Key design decisions

### No logic in bridges

`gui/bridge.py` bridges are thin: they call module functions and emit
signals. All business logic lives in `modules/`.

### Optional dependencies

Qt, D-Bus, and snapshot backends are optional. Each is imported lazily
inside the function that needs it, with a clear `ImportError` message.

### Extension plugin pattern

Extensions implement `Extension` (ABC) and register in `REGISTRY`. The
resolver is independent of the registry — it accepts any `Mapping[str, Extension]`.

### Subprocess over bindings

Waydroid, ADB, ZFS, and btrfs are invoked via `subprocess` rather than
Python bindings. This keeps the dependency surface small and makes the
code easy to test with `unittest.mock.patch("subprocess.run")`.

## Data flow: `wdt extensions install gapps`

```
CLI (extensions.py)
  └─ resolve(["gapps"], REGISTRY)          # resolver.py
       └─ BFS expand requires
       └─ conflict check
       └─ topological sort
  └─ install_with_deps(["gapps"], REGISTRY)
       └─ GAppsExtension.install()         # gapps.py
            └─ download_image()            # net.py
            └─ extract to overlay          # overlay.py
            └─ run_waydroid("session", "stop")
```
