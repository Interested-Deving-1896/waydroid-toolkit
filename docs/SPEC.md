# WayDroid Toolkit — Technical Specification

## Scope

WayDroid Toolkit is a management layer that sits above the Waydroid core runtime. It does not fork or replace `waydroid/waydroid`. It calls the Waydroid CLI and DBus interface, reads/writes `/var/lib/waydroid/`, and uses ADB to interact with the running Android container.

**In scope:**
- Installing and initialising Waydroid on supported distros
- Installing extensions (GApps, microG, Magisk, ARM translation) via the overlay filesystem
- Managing multiple Android image profiles with isolated userdata
- Installing Android packages (APK files, F-Droid repos)
- Backing up and restoring all Waydroid data
- Applying host-side performance tuning for gaming workloads
- Maintenance operations: display settings, screenshots, logcat, file transfer, debloat

**Out of scope:**
- Building Android images (handled by `YogSottot/waydroid_stuff`, `waydroid-androidtv-builds`)
- Hosting OTA update servers (handled by `Amstel-DEV/ota`)
- Platform-specific deployments (Raspberry Pi, Chrome OS, Apple Silicon)
- Modifying the Waydroid core runtime

---

## Module Specifications

### `core.waydroid`

Wraps the `waydroid` CLI binary and reads `/var/lib/waydroid/waydroid.cfg`.

- `is_installed()` — checks PATH for `waydroid` binary
- `is_initialized()` — checks that `system.img` and `vendor.img` exist at `images_path`
- `get_session_state()` → `SessionState` — parses `waydroid status` output
- `run_waydroid(*args, sudo)` — runs a waydroid subcommand
- `shell(command)` — executes a command inside the Android container via `waydroid shell`
- `WaydroidConfig.load()` — parses `waydroid.cfg` into a dataclass

### `core.adb`

Manages the ADB connection to Waydroid's endpoint at `192.168.250.1:5555`.

- `connect(retries, delay)` — connects with retry logic
- `shell(command)` — runs a command via `adb shell`
- `install_apk(path)` — installs an APK via `adb install -r`
- `push(local, remote)` / `pull(remote, local)` — file transfer
- `screenshot(dest)` — captures via `adb exec-out screencap -p`
- `logcat(tag, errors_only)` — returns a streaming `Popen` handle

### `core.privilege`

- `is_root()` — checks `os.geteuid() == 0`
- `require_root(operation)` — raises `PermissionError` if neither root nor passwordless sudo
- `sudo_run(*args)` — runs a command with sudo

### `modules.extensions`

Plugin architecture. Each extension implements `Extension` (abstract base class):

```
Extension
  .meta: ExtensionMeta       # id, name, description, conflicts, requires
  .is_installed() -> bool
  .install(progress)
  .uninstall(progress)
  .state() -> ExtensionState
```

The `REGISTRY` dict maps extension IDs to instances. Conflict checking is enforced by the CLI/GUI before calling `install()`.

**Bundled extensions:**

| ID | Name | Conflicts |
|---|---|---|
| `gapps` | OpenGApps pico | `microg` |
| `microg` | microG | `gapps` |
| `magisk` | Magisk (Waydroid fork) | — |
| `libhoudini` | Intel ARM translation | `libndk` |
| `libndk` | Google NDK translation | `libhoudini` |

All extensions require `mount_overlays = true` in `waydroid.cfg`. Extensions install files into `/var/lib/waydroid/overlay/` which Waydroid mounts over the base image at container start.

### `modules.images`

Manages image profiles stored under `~/waydroid-images/`. A valid profile is any directory containing both `system.img` and `vendor.img`.

Switching profiles:
1. Stops the running session
2. Updates `images_path` in `waydroid.cfg`
3. Symlinks `~/.local/share/waydroid/data` and `/var/lib/waydroid/overlay_rw` to profile-specific directories under `~/.local/share/waydroid/profiles/<name>/`

This gives each profile isolated userdata and overlay state.

### `modules.backup`

Backs up three directories to a `tar.gz` archive:
- `~/.local/share/waydroid` (user app data)
- `/var/lib/waydroid` (container config, images path)
- `/etc/waydroid-extra/images` (if present)

The session is stopped before backup and the archive is owned by the calling user. Restore extracts to `/` with `sudo tar -xzf`.

### `modules.packages`

Two sub-concerns:

**APK management** — uses ADB (`adb install -r`, `adb uninstall`, `pm list packages -3`).

**F-Droid repos** — stores repo metadata under `~/.local/share/waydroid-toolkit/repos/<name>/`. Downloads `index-v1.json` from each repo URL. `search_repos(query)` scans all cached indices.

### `modules.performance`

Applies host-side tuning. All operations require root.

- **ZRAM** — uses `zramctl --find --size --algorithm` then `mkswap` + `swapon --priority 100`
- **CPU governor** — writes to `/sys/devices/system/cpu/cpufreq/policy*/scaling_governor`
- **Turbo Boost** — writes to `/sys/devices/system/cpu/intel_pstate/no_turbo`
- **GameMode** — calls `gamemoded -r` if the binary is present

A systemd service (`waydroid-boost.service`) can be installed to persist the profile across reboots.

### `modules.maintenance`

Thin wrappers over `core.adb` and `core.waydroid`:

- Display: `waydroid prop set persist.waydroid.{width,height,density}`
- Screenshot: `adb exec-out screencap -p` piped to a local file
- Screen record: `adb shell screenrecord` then `adb pull`
- File transfer: `adb push` / `adb pull`
- Logcat: streaming `adb logcat` via `subprocess.Popen`
- App freeze/unfreeze: `pm disable-user --user 0` / `pm enable`
- Debloat: `pm uninstall -k --user 0` for each target package

### `modules.installer`

Detects the host distro via `/etc/os-release`, adds the Waydroid package repo, installs the package, then runs `waydroid init -s <IMAGE_TYPE> -f`.

Supported distros: Debian, Ubuntu, Fedora, Arch, openSUSE.

---

## CLI Design (`wdt`)

Built with [Click](https://click.palletsprojects.com/). Output formatted with [Rich](https://github.com/Textualize/rich).

```
wdt
├── status
├── install        [--image-type] [--arch] [--skip-repo] [--init-only]
├── extensions
│   ├── list
│   ├── install    <id>
│   └── remove     <id>
├── images
│   ├── list       [--base]
│   └── switch     <name> [--base]
├── packages
│   ├── install    <source>
│   ├── remove     <package>
│   ├── list
│   ├── search     <query>
│   └── repo
│       ├── add    <name> <url>
│       ├── remove <name>
│       └── list
├── backup
│   ├── create     [--dest]
│   ├── list       [--dir]
│   └── restore    <archive> [--yes]
├── performance
│   ├── apply      [--zram-size] [--zram-algo] [--governor] [--no-turbo] [--no-gamemode]
│   ├── restore
│   └── enable-service
└── maintenance
    ├── info
    ├── set-resolution <width> <height>
    ├── set-density    <dpi>
    ├── reset-display
    ├── screenshot     [--dest]
    ├── record         [--dest] [--duration]
    ├── push           <local> <android-dest>
    ├── pull           <android-src> <local>
    ├── logcat         [--tag] [--errors]
    ├── freeze         <package>
    ├── unfreeze       <package>
    ├── clear-data     <package> [--cache-only]
    ├── launch         <package>
    └── debloat        [-p <package>]... [--yes]
```

---

## GUI Design

Built with GTK4 + libadwaita. Requires `PyGObject >= 3.44`.

Layout: `Adw.NavigationSplitView` with a sidebar `Gtk.ListBox` and a content `Gtk.Stack`. Each module maps to one page.

All blocking operations (network, subprocess, filesystem) run on daemon threads. Results are posted back to the GTK main loop via `GLib.idle_add()`.

Pages:
- **Status** — `Adw.PreferencesGroup` of `Adw.ActionRow` widgets, refreshed on demand
- **Extensions** — one `Adw.ActionRow` per extension with Install/Remove buttons; conflict checking before install
- **Images** — scans `~/waydroid-images/`, Switch button per non-active profile
- **Packages** — APK URL/path entry + installed package list
- **Backup** — Create button + selectable list of archives + Restore button
- **Performance** — `SpinButton`, `DropDown`, `Adw.SwitchRow` for each tuning parameter
- **Maintenance** — display settings form, screenshot/record buttons, device info rows

---

## Dependency Policy

| Dependency | Reason |
|---|---|
| `click` | CLI framework |
| `rich` | Terminal output formatting |
| `requests` | HTTP downloads (fallback; stdlib `urllib` used in `utils.net`) |
| `toml` | Config file parsing |
| `PyGObject` | GTK4/Adwaita GUI (optional, `[gui]` extra) |

No dependency on any upstream Waydroid helper project's code — integration is at the interface level (CLI calls, overlay filesystem layout, ADB protocol).

---

## Privilege Model

| Operation | Privilege required |
|---|---|
| Read status, list packages, ADB shell | None |
| Install extensions, switch images | `sudo` (writes to `/var/lib/waydroid/`) |
| Install/uninstall Waydroid package | `sudo` |
| Create/restore backup | `sudo` (reads root-owned `/var/lib/waydroid/`) |
| Apply performance profile | `sudo` (writes to `/sys/`, `/etc/systemd/`) |

Operations that require root call `core.privilege.require_root()` which raises `PermissionError` with a clear message if neither root nor passwordless sudo is available.

---

## Testing Strategy

- **Unit tests** (`tests/unit/`) — mock all subprocess and filesystem calls; test pure logic
- **Integration tests** (`tests/integration/`) — require a running Waydroid instance; skipped in CI
- Coverage target: 80% for `core/` and `modules/`; GUI pages excluded from coverage requirement

Run tests:
```bash
pytest tests/unit/
pytest tests/unit/ tests/integration/ --run-integration  # with live Waydroid
```
