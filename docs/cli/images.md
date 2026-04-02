# wdt images

Manage Waydroid image profiles and Android TV detection.

## Commands

### `list`

```bash
wdt images list
wdt images list --base /mnt/images
```

Scans `~/waydroid-images/` (or `--base`) for profiles and prints a table.

### `switch`

```bash
wdt images switch PROFILE_NAME
wdt images switch androidtv-11
```

Switches the active image profile. If the target image is detected as an
Android TV build, ATV display properties are written to `waydroid.cfg`
automatically.

### `check-update`

```bash
wdt images check-update
```

Checks the OTA channel for available image updates.

### `download`

```bash
wdt images download
wdt images download --dest /mnt/images/ota
```

Downloads the latest system and vendor images.

### `atv detect`

```bash
wdt images atv detect [PATH]
```

Prints `android-tv` or `standard`. If `PATH` is omitted, uses the active profile.

Detection checks `ro.build.characteristics=tv` in the image's `build.prop`
via `debugfs`, falling back to a directory name heuristic (`tv`, `atv`,
`androidtv`).

### `atv apply`

```bash
wdt images atv apply
wdt images atv apply --standard
```

Writes ATV (or standard) display/input properties to `waydroid.cfg`.

| Property | ATV value | Standard value |
|---|---|---|
| `persist.waydroid.width` | `1920` | `0` |
| `persist.waydroid.height` | `1080` | `0` |
| `persist.waydroid.density` | `213` | `0` |
| `persist.waydroid.fake_touch` | `1` | `0` |
| `ro.build.characteristics` | `tv` | `default` |
