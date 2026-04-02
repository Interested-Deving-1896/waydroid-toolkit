# Images module

`waydroid_toolkit.modules.images`

## Image profiles

```python
from waydroid_toolkit.modules.images import scan_profiles, switch_profile, get_active_profile

profiles = scan_profiles()           # scan ~/waydroid-images/
active   = get_active_profile()      # returns ImageProfile | None
switch_profile(profiles[0])          # switch + auto-apply ATV props if detected
```

`ImageProfile` is a dataclass with `name: str` and `path: Path`.

## Android TV detection

```python
from waydroid_toolkit.modules.images import (
    is_atv_profile,
    apply_atv_props,
    apply_standard_props,
    profile_is_atv_configured,
)

if is_atv_profile(profile.path):
    apply_atv_props()
else:
    apply_standard_props()
```

### Detection logic

1. Run `debugfs -R "cat /system/build.prop" system.img` and check for
   `ro.build.characteristics=tv`.
2. If `debugfs` is unavailable or times out, fall back to checking the
   directory name for `tv`, `atv`, or `androidtv`.

### ATV properties written

| Property | Value |
|---|---|
| `persist.waydroid.width` | `1920` |
| `persist.waydroid.height` | `1080` |
| `persist.waydroid.density` | `213` |
| `persist.waydroid.fake_touch` | `1` |
| `ro.build.characteristics` | `tv` |

## OTA updates

```python
from waydroid_toolkit.modules.images import check_updates, download_updates

system_info, vendor_info = check_updates()
if system_info.update_available:
    system_path, vendor_path = download_updates(dest_dir=Path("~/waydroid-images/ota"))
```
