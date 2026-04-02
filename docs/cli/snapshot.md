# wdt snapshot

Filesystem-level snapshots via ZFS or btrfs.

The backend is auto-detected (ZFS preferred). Use `--backend` to override.

## Commands

### `create`

```bash
wdt snapshot create [LABEL]
wdt snapshot create before-gapps
wdt snapshot create --backend btrfs pre-update
```

Takes a snapshot of the Waydroid data directory. The snapshot name is
`waydroid-YYYYMMDD_HHMMSS[-LABEL]`.

### `list`

```bash
wdt snapshot list
wdt snapshot list --backend zfs
```

### `restore`

```bash
wdt snapshot restore SNAPSHOT_NAME
```

!!! warning
    Restoring overwrites the current Waydroid data. Stop the Waydroid
    session before restoring.

### `delete`

```bash
wdt snapshot delete SNAPSHOT_NAME
```

## Backends

### ZFS

Snapshots the dataset configured in `ZfsBackend` (default: `rpool/waydroid`).
Uses `zfs snapshot`, `zfs rollback`, and `zfs destroy`.

### btrfs

Snapshots the `/var/lib/waydroid` subvolume as a read-only snapshot stored
in `/var/lib/waydroid_snapshots/`. Restore swaps the live subvolume with a
writable copy of the snapshot.
