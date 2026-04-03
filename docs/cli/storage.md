# wdt storage

Manage shared storage for the Waydroid container.

Ported from [canonical/anbox-cloud-nfs-operator](https://github.com/canonical/anbox-cloud-nfs-operator).
The Juju subordinate charm that mounted NFS into LXD-hosted Anbox containers
is replaced with direct `incus config device` commands.

## Sub-commands

| Command | Description |
|---|---|
| `wdt storage nfs add SOURCE` | Attach an NFS share as an Incus disk device |
| `wdt storage nfs remove DEVICE` | Detach a disk device by name |
| `wdt storage nfs list` | List all disk devices on the container |

## Usage

### Mount an NFS share

```bash
wdt storage nfs add 192.168.1.10:/exports/assets
```

Mounts the NFS share at `/data/shared` inside the Waydroid container.

### Custom mount point

```bash
wdt storage nfs add 192.168.1.10:/exports/games --path /data/games
```

### AWS EFS

```bash
wdt storage nfs add fs-0abc1234:/ --type efs --options tls
```

### Local bind mount

```bash
wdt storage nfs add /mnt/gamedata --type disk --path /data/games
```

### List mounts

```bash
wdt storage nfs list
```

### Remove a mount

```bash
wdt storage nfs remove nfs-192-168-1-10--exports-assets
```

## Options for `wdt storage nfs add`

| Option | Default | Description |
|---|---|---|
| `--path` | `/data/shared` | Mount point inside the container |
| `--name` | auto | Incus device name |
| `--type` | `nfs` | Mount type: `nfs`, `efs`, `disk` |
| `--options` | `soft,async` | Extra mount options |

## Mapping from anbox-cloud-nfs-operator

| Anbox | Waydroid |
|---|---|
| Juju charm deploy | `wdt storage nfs add` |
| `juju config mount_type=nfs` | `--type nfs` |
| `juju config nfs_path=host:/path` | `SOURCE` argument |
| `juju config nfs_extra_options=tls` | `--options tls` |
| `/media/anbox-data` mount target | `--path /data/shared` (configurable) |
| `juju remove-relation` | `wdt storage nfs remove` |
