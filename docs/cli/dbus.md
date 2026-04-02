# wdt dbus

D-Bus service mode. Registers `io.github.waydroid_toolkit` on the session bus.

Requires `python3-dbus` and `python3-gi`:

```bash
sudo apt install python3-dbus python3-gi
```

## Commands

### `serve`

```bash
wdt dbus serve
```

Starts the service and blocks. Use a systemd user unit or `&` to background it.

**D-Bus activation** (auto-start on first call) is supported via the service
file installed at
`~/.local/share/dbus-1/services/io.github.waydroid_toolkit.service`.

### Query commands

All query commands connect to the running service and print the result.

```bash
wdt dbus status
wdt dbus list-profiles
wdt dbus switch-profile androidtv-11
wdt dbus list-extensions
wdt dbus install-extension widevine
wdt dbus create-snapshot before-update
wdt dbus list-snapshots
wdt dbus stop
```

## Interface

**Bus name**: `io.github.waydroid_toolkit`  
**Object path**: `/io/github/waydroid_toolkit`  
**Interface**: `io.github.waydroid_toolkit.Manager`

### Methods

| Method | Signature | Description |
|---|---|---|
| `GetStatus` | `→ s` | JSON: `{state, version}` |
| `ListProfiles` | `→ s` | JSON array of `{name, path}` |
| `SwitchProfile` | `s → b` | Switch to named profile |
| `ListExtensions` | `→ s` | JSON array of `{id, name, state}` |
| `InstallExtension` | `s → b` | Install extension by ID |
| `CreateSnapshot` | `s → s` | Create snapshot; returns name |
| `ListSnapshots` | `→ s` | JSON array of snapshot metadata |
| `Stop` | `→ void` | Stop the service |

### Signals

| Signal | Signature | Emitted when |
|---|---|---|
| `ProfileChanged` | `s` | After successful `SwitchProfile` |
| `ExtensionInstalled` | `s` | After successful `InstallExtension` |
| `SnapshotCreated` | `ss` | After successful `CreateSnapshot` |
