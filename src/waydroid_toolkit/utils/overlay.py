"""Waydroid overlay filesystem helpers.

Waydroid mounts an OverlayFS on top of system.img so that modifications
can be made without altering the base image. Extensions are installed
by placing files under /var/lib/waydroid/overlay/.
"""

from __future__ import annotations

import shutil
from pathlib import Path

_OVERLAY_ROOT = Path("/var/lib/waydroid/overlay")
_OVERLAY_RW = Path("/var/lib/waydroid/overlay_rw")


def overlay_path(android_path: str) -> Path:
    """Convert an Android absolute path to its overlay host path.

    e.g. '/system/lib/libfoo.so' -> '/var/lib/waydroid/overlay/system/lib/libfoo.so'
    """
    return _OVERLAY_ROOT / android_path.lstrip("/")


def install_file(src: Path, android_dest: str) -> Path:
    """Copy src into the overlay at android_dest. Creates parent dirs."""
    dest = overlay_path(android_dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def remove_file(android_path: str) -> bool:
    """Remove a file from the overlay. Returns True if it existed."""
    target = overlay_path(android_path)
    if target.exists():
        target.unlink()
        return True
    return False


def is_overlay_enabled() -> bool:
    """Return True if mount_overlays is enabled in waydroid.cfg."""
    from waydroid_toolkit.core.waydroid import WaydroidConfig
    return WaydroidConfig.load().mount_overlays
