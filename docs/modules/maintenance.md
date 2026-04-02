# Maintenance module

`waydroid_toolkit.modules.maintenance.tools`

## Display settings

```python
from waydroid_toolkit.modules.maintenance.tools import (
    set_resolution, set_density, reset_display
)

set_resolution(1920, 1080)
set_density(240)
reset_display()            # set width/height/density to 0 (use host size)
```

## Device info

```python
from waydroid_toolkit.modules.maintenance.tools import get_device_info

info = get_device_info()
# {"android_version": "13", "sdk_version": "33", "product_model": "...", ...}
```

## Screenshot

```python
from waydroid_toolkit.modules.maintenance.tools import take_screenshot
from pathlib import Path

path = take_screenshot()                        # auto-named in ~/Pictures/Waydroid/
path = take_screenshot(Path("/tmp/shot.png"))   # explicit destination
```

## Screen recording

```python
from waydroid_toolkit.modules.maintenance.tools import record_screen

path = record_screen(duration_seconds=30)
# Saves to ~/Videos/Waydroid/recording_YYYYMMDD_HHMMSS.mp4
```

The GUI `MaintenanceBridge` wraps this in a background thread with
`startRecording(duration)` / `stopRecording()` slots and a `recordingSaved(path)`
signal.

## File transfer

```python
from waydroid_toolkit.modules.maintenance.tools import push_file, pull_file
from pathlib import Path

push_file(Path("/host/file.apk"), "/sdcard/file.apk")
pull_file("/sdcard/Download/file.zip", Path("/host/Downloads/file.zip"))
```

## Logcat

```python
from waydroid_toolkit.modules.maintenance.tools import stream_logcat, get_logcat

# Bounded snapshot
output = get_logcat(lines=500, tag="MyApp", errors_only=False)

# Live streaming generator
for line in stream_logcat(tag="MyApp"):
    print(line)
    if should_stop:
        break
```

## App management

```python
from waydroid_toolkit.modules.maintenance.tools import (
    freeze_app, unfreeze_app, clear_app_data, launch_app, debloat
)

freeze_app("com.android.email")
unfreeze_app("com.android.email")
clear_app_data("com.example.app", cache_only=True)
launch_app("com.example.app")
removed = debloat(progress=print)
```
