"""Android TV image profile support.

Detects whether a Waydroid image profile contains Android TV (ATV) images
and applies the appropriate display and input properties so the TV launcher
and remote-control navigation work correctly.

Detection
---------
ATV images ship with ``ro.build.characteristics=tv`` in their build.prop.
We read this from the mounted system image (or from the profile directory
if the image is not currently mounted) using ``debugfs``.

ATV-specific settings applied via ``waydroid prop set``
-------------------------------------------------------
- ``persist.waydroid.width``  → 1920
- ``persist.waydroid.height`` → 1080
- ``persist.waydroid.density`` → 213  (standard TV DPI)
- ``persist.waydroid.fake_touch`` → 1  (map D-pad to touch events)
- ``ro.build.characteristics`` → tv

These are written to ``/var/lib/waydroid/waydroid.cfg`` under the
``[properties]`` section so they survive reboots.
"""

from __future__ import annotations

import configparser
import subprocess
from pathlib import Path

from waydroid_toolkit.core.waydroid import WaydroidConfig

_CFG_PATH = Path("/var/lib/waydroid/waydroid.cfg")

# Display settings for ATV profiles
_ATV_PROPS: dict[str, str] = {
    "persist.waydroid.width":            "1920",
    "persist.waydroid.height":           "1080",
    "persist.waydroid.density":          "213",
    "persist.waydroid.fake_touch":       "1",
    "ro.build.characteristics":          "tv",
}

# Display settings for standard (phone/tablet) profiles
_STANDARD_PROPS: dict[str, str] = {
    "persist.waydroid.width":            "0",   # 0 = use host display size
    "persist.waydroid.height":           "0",
    "persist.waydroid.density":          "0",
    "persist.waydroid.fake_touch":       "0",
    "ro.build.characteristics":          "default",
}


def is_atv_profile(profile_path: Path) -> bool:
    """Return True if the system image in *profile_path* is an Android TV build.

    Checks ``ro.build.characteristics`` in the image's build.prop.
    Falls back to checking the profile directory name for ``tv`` or ``atv``.
    """
    system_img = profile_path / "system.img"
    if system_img.exists():
        try:
            result = subprocess.run(
                ["debugfs", "-R", "cat /system/build.prop", str(system_img)],
                capture_output=True, text=True, timeout=10,
            )
            if "ro.build.characteristics=tv" in result.stdout:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # debugfs not available; fall through to name heuristic

    name = profile_path.name.lower()
    return "tv" in name or "atv" in name or "androidtv" in name


def apply_atv_props(cfg_path: Path = _CFG_PATH) -> None:
    """Write ATV display/input properties to *cfg_path*."""
    _write_props(_ATV_PROPS, cfg_path)


def apply_standard_props(cfg_path: Path = _CFG_PATH) -> None:
    """Reset display/input properties to standard (phone/tablet) defaults."""
    _write_props(_STANDARD_PROPS, cfg_path)


def _write_props(props: dict[str, str], cfg_path: Path) -> None:
    parser = configparser.ConfigParser()
    if cfg_path.exists():
        parser.read(cfg_path)
    if "properties" not in parser:
        parser["properties"] = {}
    for key, value in props.items():
        parser["properties"][key] = value
    tmp = cfg_path.with_suffix(".tmp")
    with tmp.open("w") as fh:
        parser.write(fh)
    subprocess.run(["sudo", "mv", str(tmp), str(cfg_path)], check=True)


def get_current_props(cfg_path: Path = _CFG_PATH) -> dict[str, str]:
    """Return the current ATV-relevant properties from *cfg_path*."""
    parser = configparser.ConfigParser()
    if cfg_path.exists():
        parser.read(cfg_path)
    section = parser["properties"] if "properties" in parser else {}
    return {k: section.get(k, "") for k in _ATV_PROPS}


def profile_is_atv_configured(cfg_path: Path = _CFG_PATH) -> bool:
    """Return True if the current waydroid.cfg has ATV properties applied."""
    props = get_current_props(cfg_path)
    return props.get("ro.build.characteristics", "") == "tv"
