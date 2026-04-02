# CLI Overview

```
wdt [OPTIONS] COMMAND [ARGS]...
```

| Command | Description |
|---|---|
| `status` | Show Waydroid runtime state |
| `install` | Install Waydroid on this system |
| `extensions` | Manage extensions (GApps, Widevine, key mapper, …) |
| `images` | Manage image profiles and Android TV detection |
| `snapshot` | Filesystem snapshots via ZFS or btrfs |
| `dbus` | D-Bus service mode |
| `maintenance` | Screenshots, screen recording, logcat, file transfer |
| `backup` | Backup and restore Waydroid data |
| `packages` | Install APKs, manage F-Droid repos |
| `performance` | Host-side performance tuning |
| `build` | Build Android images via penguins-eggs |
| `backend` | Select and inspect the container backend |
| `gui` | Launch the Qt GUI |

Use `wdt COMMAND --help` for per-command help.

## Global options

| Option | Description |
|---|---|
| `-v`, `--version` | Print version and exit |
| `-h`, `--help` | Show help |
