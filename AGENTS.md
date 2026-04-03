# AGENTS.md — WayDroid Toolkit

Architecture decisions, conventions, and patterns established across the
development history of this project. Read this before making changes.

---

## Repository layout

```
src/waydroid_toolkit/
  cli/           Click command groups (wdt <group> <subcommand>)
  core/          Low-level interfaces: adb, waydroid CLI, container backends
  gui/           GTK4/Adwaita application
  modules/       Feature modules: backup, extensions, images, installer,
                 maintenance, packages, performance
  utils/         Shared utilities: distro detection, net, overlay, privilege
tests/
  unit/          Fast, fully mocked — always run in CI
  integration/   Require live Waydroid + ADB — skipped in CI automatically
```

---

## Container backend abstraction

`src/waydroid_toolkit/core/container/`

Waydroid uses LXC directly. This toolkit adds an `Incus` backend as an
alternative. Both implement `ContainerBackend` (ABC in `base.py`).

**Key files:**
- `base.py` — `ContainerBackend` ABC, `BackendType`, `ContainerState`
- `lxc_backend.py` — wraps `lxc-*` CLI tools
- `incus_backend.py` — wraps `incus` CLI
- `selector.py` — reads/writes `~/.config/waydroid-toolkit/config.toml`

**Default backend:** `selector.detect()` prefers Incus over LXC. When Incus
is not installed it falls back to LXC and prints a warning to stderr
directing the user to `wdt backend switch incus`.

**Switching backends at runtime:**
- `wdt backend switch incus` / `wdt backend set incus` — both call
  `selector.set_active(BackendType.INCUS)` and persist to config.
  `set` is an alias for `switch` added for discoverability.
- `wdt install --backend incus` (default) — activates the chosen backend
  immediately after `waydroid init` completes.

**Programmatic switch:** `selector.set_active(BackendType.INCUS)` writes the
config; `selector.get_active()` returns the active backend instance.

**Adding a new backend:** subclass `ContainerBackend`, implement all abstract
methods, add the `BackendType` enum value, register in `selector.py` and
`__init__.py`.

### Incus backend — LXC parity gaps (all closed)

Six categories of behaviour that LXC handles natively but Incus needs
explicit configuration for:

1. **raw.lxc merge** — All passthrough directives (mount entries, seccomp,
   AppArmor, cgroup, caps) from all three LXC config files are merged into
   one string and applied in a single `incus config set` call.
   Separate calls overwrite each other — never split them.

2. **Device nodes** — Each character device (binder, ashmem, GPU, DRI render
   nodes, DMA heaps) is added as a native `unix-char` device via
   `incus config device add`. Static devices are declared in
   `_static_char_devices()`; optional nodes are discovered by glob in
   `_glob_char_devices()` at setup time.

3. **Filesystem mounts** — tmpfs overlays (`/dev`, `/tmp`, `/var`, `/run`)
   and bind mounts (vendor partition, sysfs nodes, WSLg) are added as
   `disk` devices.

4. **Session mounts** — `configure_session(SessionConfig)` applies
   per-session Wayland socket, audio socket, and userdata bind mounts at
   session start. `remove_session_devices()` cleans them up at stop.

5. **Android environment** — `execute()` passes `ANDROID_ENV` (PATH,
   ANDROID_ROOT, ANDROID_DATA, BOOTCLASSPATH, etc.) via `--env` on every
   `incus exec` call.

6. **Exec privileges** — `execute()` accepts `uid`, `gid`,
   `disable_apparmor`, `extra_env` → `--user` / `--disable-apparmor`.

---

## wdt doctor

`src/waydroid_toolkit/cli/commands/doctor.py`

Checks prerequisites and runtime environment. Exits 0 when all required
checks pass (warnings are non-fatal). Exits 1 when any required check fails.

**Checks performed:**

| Check | Required | Notes |
|---|---|---|
| `waydroid` binary | ✅ | |
| waydroid initialized | ✅ | only if binary found |
| container backend | ✅ | reads active backend from config |
| `incus` binary | ✅ | only when Incus backend is active |
| `incus waydroid` container | ✅ | only when Incus backend is active |
| LXC active but Incus available | ⚠ warning | suggests `wdt backend set incus` |
| `binder_linux` kernel module | ✅ | |
| `ashmem_linux` kernel module | ⚠ warning | optional on modern kernels |
| `/dev/binder`, `/dev/ashmem` | ✅ | |
| GPU/DMA device nodes | ⚠ warning | optional, needed for GPU accel |
| `adb` binary | ✅ | |
| ADB connected | ⚠ warning | only if adb found |
| audio socket (PipeWire/PA) | ⚠ warning | |

**Adding a new check:** append a `_check()` or `_warn()` call to the `rows`
list in `cmd()`. Both return a 4-tuple `(label, status, detail, fix)`.
`_check()` increments `fail_count` on failure; `_warn()` increments
`warn_count`. Do not raise exceptions from check functions — catch and
convert to `_check(..., ok=False)`.

**JSON output:** `wdt doctor --json` emits a JSON array of
`{check, status, detail, fix}` objects. Rich markup is stripped from
`status` in JSON mode.

---

## Audio backend selection

`SessionConfig` supports PulseAudio and PipeWire natively.

`detect_audio_backend()` probes `$XDG_RUNTIME_DIR/pipewire-0`:
- Present → `AudioBackend.PIPEWIRE` (native socket, lower latency)
- Absent → `AudioBackend.PULSEAUDIO`

The PulseAudio compatibility socket (`pulse/native`) is intentionally **not**
used as the detection signal — its presence only means `pipewire-pulse` is
running, not that the native PipeWire socket is available.

`SessionConfig.detect(audio=AudioBackend.AUTO)` auto-populates all fields
from the running host environment. Pass `audio=AudioBackend.PULSEAUDIO` or
`PIPEWIRE` to override detection.

---

## GUI presenter pattern

`src/waydroid_toolkit/gui/presenters.py`

GTK page classes (`gui/pages/*.py`) must not contain domain logic. All
data-gathering is extracted into presenter functions that return plain
dataclasses:

| Function | Returns | Used by |
|----------|---------|---------|
| `get_status_data()` | `StatusData` | Status page |
| `get_backup_entries()` | `list[BackupEntry]` | Backup page |
| `get_extension_rows()` | `list[ExtensionRow]` | Extensions page |
| `get_image_profile_rows()` | `list[ImageProfileRow]` | Images page |
| `get_device_info_data()` | `dict[str, str]` | Maintenance page |

Pages call these from background threads, then apply results to widgets via
`GLib.idle_add`. This keeps widget code thin and makes business logic
testable without a display server.

**When adding a new page:** put all data-gathering in a presenter function
first, test it in `tests/unit/test_presenters.py`, then wire it into the
page's `_work()` thread.

---

## GUI error reporting

`src/waydroid_toolkit/gui/pages/base.py`

`BasePage` provides two methods for background operation failures:

```python
self._show_toast(message, timeout=3)   # informational
self._show_error(message)              # prefixes "Error:", timeout=5
```

These post an `Adw.Toast` via the application-wide `ToastOverlay` registered
by `MainWindow` at startup (`register_toast_overlay(overlay)`). The overlay
is `None` in unit tests — both methods are no-ops in that case.

**Pattern for background threads:**

```python
def _work() -> None:
    try:
        do_something()
        GLib.idle_add(lambda: self._status_label.set_label("Done."))
    except Exception as exc:
        msg = str(exc)
        GLib.idle_add(lambda: self._status_label.set_label(f"Error: {msg}"))
        GLib.idle_add(lambda: self._show_error(msg))

threading.Thread(target=_work, daemon=True).start()
```

Every `except` block in a page **must** call `_show_error` in addition to
updating any inline status label.

---

## Distro detection

`src/waydroid_toolkit/utils/distro.py`

`detect()` reads `/etc/os-release` and matches `ID` and `ID_LIKE` fields.
Supported distros: Debian, Ubuntu, Fedora, Arch, openSUSE, NixOS, Void,
Alpine, Gentoo.

**NixOS** is a special case: `install_package()` raises `NotImplementedError`
with a message directing the user to `configuration.nix`. There is no
imperative install path for NixOS.

When adding support for a new distro:
1. Add the enum value to `Distro`
2. Add detection logic in `detect()` (match against `ID` or `ID_LIKE`)
3. Add `_INSTALL_CMD` and `remove_cmds` entries in `installer.py`
4. Add `_REPO_SETUP` entry (empty list if no repo script needed)
5. Add parametrized test cases in `test_distro.py` and `test_installer.py`

---

## ADB connection reliability

`src/waydroid_toolkit/core/adb.py`

`connect()` checks `SessionState` before each attempt. When Waydroid is not
running, the `adb connect` call is skipped and the loop sleeps before
retrying. This prevents wasted TCP connection attempts against a stopped
container.

The session state check uses a lazy import to avoid a circular dependency:

```python
from waydroid_toolkit.core.waydroid import SessionState, get_session_state
```

When patching `connect()` in tests, patch
`waydroid_toolkit.core.waydroid.get_session_state` (the source), not
`waydroid_toolkit.core.adb.get_session_state` (which doesn't exist at module
level due to the lazy import).

---

## Testing conventions

### Unit tests (`tests/unit/`)

- All external calls (subprocess, filesystem, network) are mocked.
- Patch at the **import site**, not the definition site, unless the import
  is lazy (inside a function), in which case patch at the definition site.
- Common gotcha: `shell()` in `waydroid.py` does
  `from waydroid_toolkit.core.container import get_active as _get_backend`
  lazily. Patch `waydroid_toolkit.core.container.get_active`.

### Integration tests (`tests/integration/`)

- Require a live Waydroid session and ADB connection.
- The `_require_live_waydroid` autouse fixture in `conftest.py` skips all
  tests automatically when prerequisites are not met.
- Never add `@pytest.mark.skip` manually — let the fixture handle it.
- APK install/uninstall tests require `tests/integration/fixtures/minimal.apk`
  which is not committed. Tests that need it call `pytest.skip()` when absent.

### GUI tests (`tests/unit/test_gui_toast.py`)

GTK is not available in CI. `test_gui_toast.py` installs `gi` stubs into
`sys.modules` at import time before importing any GUI code. If you add new
GTK widget types used in `base.py`, add corresponding stubs in
`_install_gi_stubs()`.

---

## CI

`.github/workflows/ci.yml` runs on every push and PR:

- **Lint (ruff)** — `ruff check src/ tests/`
- **Unit tests (Python 3.11)** — `pytest tests/unit/`
- **Unit tests (Python 3.12)** — `pytest tests/unit/`

Integration tests are not run in CI (no Waydroid available). They are
intended for local development and pre-release validation.

---

## wdt container — Incus-level container operations

`src/waydroid_toolkit/cli/commands/container.py`

Provides `wdt container snapshot` and `wdt container console` — operations
that act on the Waydroid container via the active backend.

**Note:** `wdt snapshot` (in `commands/snapshot.py`) is a separate command
that manages **filesystem-level snapshots** (ZFS/btrfs) of the Waydroid data
directory. `wdt container snapshot` manages **Incus container snapshots**
(point-in-time state of the running container). Both are valid and serve
different purposes.

| Command | What it snapshots |
|---|---|
| `wdt snapshot create` | ZFS/btrfs filesystem snapshot of `/var/lib/waydroid` |
| `wdt container snapshot create` | Incus container state snapshot |

`wdt container console` and `wdt container snapshot *` require the Incus
backend. When the LXC backend is active, these commands raise a clear
`NotImplementedError` with a message directing the user to
`wdt backend set incus`.

---

## wdt assemble — declarative configuration

`src/waydroid_toolkit/cli/commands/assemble.py`

Applies a YAML configuration file idempotently. Unlike incusbox/imt which
manage fleets of containers, Waydroid has a single container — so `wdt assemble`
configures that single instance: backend, image type, extensions, performance.

```yaml
waydroid:
  backend: incus          # incus | lxc
  image_type: VANILLA     # VANILLA | GAPPS
  arch: x86_64            # x86_64 | arm64
  extensions:
    - gapps
    - widevine
  performance:
    zram_size: 4096
    zram_algo: lz4
    governor: performance
```

Uses PyYAML when available; falls back to a minimal built-in parser for
environments without it. See `data/example-assemble.yaml`.

---

## ContainerBackend — write-operation gating

`LxcBackend` implements the full `ContainerBackend` ABC but raises
`NotImplementedError` for write operations that have no safe LXC equivalent:

- `snapshot_create`, `snapshot_list`, `snapshot_restore`, `snapshot_delete`
- `console`

Read-only operations (`get_state`, `execute`, `get_info`) continue to work
on LXC. This allows existing LXC users to query state without breaking, while
making the limitation explicit for write operations.

The error message always includes `"wdt backend set incus"` so users know
exactly how to resolve it.

---

## Intentional divergence from other Incus projects

The following features exist in other projects in this suite but are
**intentionally absent** from waydroid-toolkit because they are
Android-specific or Waydroid-specific concepts with no equivalent elsewhere:

| Feature | Reason absent |
|---|---|
| `extensions` (GApps, Magisk, ARM translation, microG) | Android-specific; no equivalent in Linux containers or macOS VMs |
| `performance` (ZRAM, GameMode, CPU governor) | Android gaming tuning; not applicable to general containers |
| `wdt snapshot` (ZFS/btrfs) | Waydroid data directory layout is Android-specific |
| `wdt build` (penguins-eggs) | Android image build pipeline; not applicable elsewhere |
| `wdt dbus` | Waydroid session D-Bus interface; Android-specific |
| `wdt maintenance` (logcat, screenshots, debloat) | Android device management; not applicable elsewhere |
| `wdt packages` (F-Droid, APK install) | Android package management |
| `wdt images` (OTA image profiles) | Waydroid OTA channel; Android-specific |
| `remoteapp` / GPU passthrough | Not yet implemented; planned for Incus backend |
| macOS image pipeline (OVMF, OpenCore) | macOS-specific boot chain |

These are not gaps — they are correct omissions for an Android container manager.

---

## Adding a new CLI command

1. Create `src/waydroid_toolkit/cli/commands/<group>.py` with a
   `@click.group()` and subcommands.
2. Register it in `src/waydroid_toolkit/cli/main.py`:
   ```python
   from .commands.<group> import <group>
   cli.add_command(<group>)
   ```
3. Add CLI tests in `tests/unit/test_cli.py` using `CliRunner`.
4. Mock all domain calls — CLI tests should not touch the filesystem or
   subprocesses.
