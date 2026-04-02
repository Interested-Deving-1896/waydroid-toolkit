# Snapshot module

`waydroid_toolkit.modules.snapshot`

## Auto-detection

```python
from waydroid_toolkit.modules.snapshot import get_backend, detect_backend

backend = get_backend()        # raises RuntimeError if neither ZFS nor btrfs available
backend = detect_backend()     # returns None if unavailable
```

## Common interface

All backends implement `SnapshotBackend`:

```python
backend.is_available() -> bool
backend.create(label="") -> SnapshotInfo
backend.list() -> list[SnapshotInfo]
backend.restore(name: str) -> None
backend.delete(name: str) -> None
```

`SnapshotInfo` fields: `name`, `created`, `backend`, `source`, `size_bytes`.

## ZFS backend

```python
from waydroid_toolkit.modules.snapshot import ZfsBackend

backend = ZfsBackend(dataset="rpool/waydroid")
info = backend.create("before-gapps")
```

Uses `zfs snapshot`, `zfs rollback -r`, `zfs destroy`.

## btrfs backend

```python
from waydroid_toolkit.modules.snapshot import BtrfsBackend
from pathlib import Path

backend = BtrfsBackend(
    subvol=Path("/var/lib/waydroid"),
    snap_dir=Path("/var/lib/waydroid_snapshots"),
)
info = backend.create("before-gapps")
```

Uses `btrfs subvolume snapshot -r` (read-only). Restore creates a writable
copy and swaps it with the live subvolume.

## Snapshot naming

All snapshots are named `waydroid-YYYYMMDD_HHMMSS[-label]` (UTC). This
ensures lexicographic order matches chronological order.
