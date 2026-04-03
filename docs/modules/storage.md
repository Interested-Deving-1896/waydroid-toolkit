# Storage module

`waydroid_toolkit.modules.storage`

Manages shared storage for the Waydroid Incus container via `incus config device`.

Ported from [canonical/anbox-cloud-nfs-operator](https://github.com/canonical/anbox-cloud-nfs-operator).

## API

```python
from waydroid_toolkit.modules.storage import (
    NfsMount,
    add_nfs_mount,
    remove_nfs_mount,
    list_nfs_mounts,
)

# Attach an NFS share
mount = add_nfs_mount(
    source="192.168.1.10:/exports/assets",
    container_path="/data/shared",
    mount_type="nfs",
    extra_options="soft,async",
)

# List all disk devices
mounts = list_nfs_mounts()

# Remove by device name
remove_nfs_mount(mount.device_name)
```

## NfsMount dataclass

| Field | Type | Description |
|---|---|---|
| `device_name` | `str` | Incus device name |
| `source` | `str` | NFS path or local path |
| `container_path` | `str` | Mount point inside container |
| `mount_type` | `str` | `nfs`, `efs`, or `disk` |
| `options` | `str` | Extra mount options |

See [wdt storage CLI reference](../cli/storage.md) for command-line usage.
