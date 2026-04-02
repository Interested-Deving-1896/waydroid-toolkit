# wdt backup

Backup and restore Waydroid data directories.

## Commands

### `create`

```bash
wdt backup create
wdt backup create --dest ~/backups/
```

Creates a compressed `tar.gz` archive of:

- `~/.local/share/waydroid` (user app data)
- `/var/lib/waydroid` (container config, images path)
- `/etc/waydroid-extra/images` (extra images, if present)

The Waydroid session is stopped automatically before archiving.

### `list`

```bash
wdt backup list
```

### `restore`

```bash
wdt backup restore ARCHIVE_PATH
wdt backup restore ~/.local/share/waydroid-toolkit/backups/waydroid_backup_20240101_120000.tar.gz
```

!!! warning
    Restoring overwrites all Waydroid data. The session is stopped first.
