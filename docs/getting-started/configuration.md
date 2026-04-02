# Configuration

waydroid-toolkit reads and writes `/var/lib/waydroid/waydroid.cfg` (the
standard Waydroid configuration file). No separate config file is needed.

## Key properties

| Property | Default | Description |
|---|---|---|
| `persist.waydroid.width` | `0` (host width) | Display width in pixels |
| `persist.waydroid.height` | `0` (host height) | Display height in pixels |
| `persist.waydroid.density` | `0` (auto) | Display DPI |
| `persist.waydroid.fake_touch` | `0` | Map D-pad to touch events (ATV) |
| `ro.build.characteristics` | `default` | `tv` for Android TV profiles |

## Android TV profiles

When `wdt images switch` detects an Android TV image (via `debugfs` or
directory name heuristic), it automatically writes the ATV display properties
above. To apply or reset them manually:

```bash
wdt images atv apply           # write ATV props
wdt images atv apply --standard  # reset to standard props
```

## Image profile directory

By default, `wdt images list` scans `~/waydroid-images/`. Each subdirectory
containing `system.img` and `vendor.img` is treated as a profile.

```
~/waydroid-images/
├── lineage-20/
│   ├── system.img
│   └── vendor.img
└── androidtv-11/
    ├── system.img
    └── vendor.img
```

## Snapshot backends

Snapshots use ZFS or btrfs automatically. To force a specific backend:

```bash
wdt snapshot create --backend zfs my-label
wdt snapshot create --backend btrfs my-label
```

The ZFS backend snapshots the dataset configured in `ZfsBackend` (default:
`rpool/waydroid`). The btrfs backend snapshots `/var/lib/waydroid` and stores
snapshots in `/var/lib/waydroid_snapshots/`.
