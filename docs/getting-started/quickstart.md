# Quick Start

## Check status

```bash
wdt status
```

## Install extensions

Extensions are installed with automatic dependency resolution. Conflicting
extensions (e.g. GApps and microG) are detected before anything is written.

```bash
# See what's available
wdt extensions list

# Install GApps and Widevine L3 (dependencies resolved automatically)
wdt extensions install gapps widevine

# Preview the install order without installing
wdt extensions install gapps widevine --dry-run

# Show dependency graph for an extension
wdt extensions deps magisk
```

## Manage image profiles

```bash
# List profiles under ~/waydroid-images/
wdt images list

# Switch to a profile (ATV properties applied automatically if detected)
wdt images switch androidtv-11

# Detect whether the active profile is Android TV
wdt images atv detect

# Manually apply ATV display properties
wdt images atv apply
```

## Snapshots

```bash
# Create a snapshot before making changes
wdt snapshot create before-gapps

# List snapshots
wdt snapshot list

# Restore (stops Waydroid first)
wdt snapshot restore waydroid-20240101_120000-before-gapps

# Delete
wdt snapshot delete waydroid-20240101_120000-before-gapps
```

## Maintenance

```bash
# Take a screenshot
wdt maintenance screenshot

# Start a 30-second screen recording
wdt maintenance record --duration 30

# Stream logcat (Ctrl-C to stop)
wdt maintenance logcat --tag MyApp

# Push/pull files
wdt maintenance push /path/to/file.apk /sdcard/file.apk
wdt maintenance pull /sdcard/Download/file.zip ~/Downloads/

# Debloat (remove common LineageOS bloatware)
wdt maintenance debloat
```

## D-Bus service

```bash
# Start the service (blocks; use systemd or a background job)
wdt dbus serve &

# Query the running service
wdt dbus status
wdt dbus list-extensions
wdt dbus create-snapshot before-update
```
