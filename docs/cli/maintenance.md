# wdt maintenance

Display settings, screenshots, screen recording, logcat, file transfer, and debloat.

## Commands

### `screenshot`

```bash
wdt maintenance screenshot
wdt maintenance screenshot --dest ~/Pictures/waydroid.png
```

Saves a PNG screenshot to `~/Pictures/Waydroid/screenshot_YYYYMMDD_HHMMSS.png`
(or `--dest`).

### `record`

```bash
wdt maintenance record
wdt maintenance record --duration 30 --dest ~/Videos/demo.mp4
```

Records the Waydroid display. Default duration: 60 seconds. Saved to
`~/Videos/Waydroid/recording_YYYYMMDD_HHMMSS.mp4`.

### `logcat`

```bash
wdt maintenance logcat
wdt maintenance logcat --tag MyApp
wdt maintenance logcat --errors
wdt maintenance logcat --lines 200
```

### `push`

```bash
wdt maintenance push LOCAL_PATH ANDROID_DEST
wdt maintenance push ~/Downloads/app.apk /sdcard/app.apk
```

### `pull`

```bash
wdt maintenance pull ANDROID_SRC LOCAL_DEST
wdt maintenance pull /sdcard/Download/file.zip ~/Downloads/
```

### `debloat`

```bash
wdt maintenance debloat
wdt maintenance debloat --packages org.lineageos.jelly,com.android.email
```

Removes common LineageOS bloatware packages using `pm uninstall -k --user 0`.

### `set-resolution`

```bash
wdt maintenance set-resolution 1920 1080
```

### `set-density`

```bash
wdt maintenance set-density 240
```

### `reset-display`

```bash
wdt maintenance reset-display
```

Resets width, height, and density to 0 (use host display size).
