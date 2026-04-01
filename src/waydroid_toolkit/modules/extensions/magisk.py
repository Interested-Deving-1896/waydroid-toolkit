"""Magisk extension — installs Magisk into the Waydroid overlay.

Supports the upstream Magisk fork patched for Waydroid
(as maintained by mistrmochov/MagiskForWaydroid and casualsnek/waydroid_script).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Optional

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.core.waydroid import get_session_state, SessionState
from waydroid_toolkit.utils.net import download
from waydroid_toolkit.utils.overlay import is_overlay_enabled
from .base import Extension, ExtensionMeta

_MAGISK_APK_URL = (
    "https://github.com/mistrmochov/MagiskForWaydroid/releases/latest/download/Magisk.apk"
)
_MAGISK_MARKER = Path("/var/lib/waydroid/overlay/system/app/Magisk")


class MagiskExtension(Extension):
    @property
    def meta(self) -> ExtensionMeta:
        return ExtensionMeta(
            id="magisk",
            name="Magisk (Waydroid fork)",
            description=(
                "Installs Magisk root manager into the Waydroid overlay. "
                "Uses a Waydroid-compatible fork with ReZygisk built in."
            ),
            requires_root=True,
        )

    def is_installed(self) -> bool:
        return _MAGISK_MARKER.exists()

    def install(self, progress: Optional[Callable[[str], None]] = None) -> None:
        require_root("Installing Magisk")
        if not is_overlay_enabled():
            raise RuntimeError("mount_overlays must be enabled to install Magisk.")
        if get_session_state() != SessionState.RUNNING:
            raise RuntimeError("Waydroid must be running before installing Magisk.")

        cache = Path("/tmp/waydroid-toolkit/Magisk.apk")
        if progress:
            progress("Downloading Magisk APK...")
        download(_MAGISK_APK_URL, cache)

        if progress:
            progress("Installing Magisk into overlay...")
        # Install APK into overlay system/app
        dest = Path("/var/lib/waydroid/overlay/system/app/Magisk")
        subprocess.run(["sudo", "mkdir", "-p", str(dest)], check=True)
        subprocess.run(["sudo", "cp", str(cache), str(dest / "Magisk.apk")], check=True)

        if progress:
            progress("Running Magisk setup inside Waydroid...")
        subprocess.run(
            ["sudo", "waydroid", "shell", "pm", "install", "/system/app/Magisk/Magisk.apk"],
            capture_output=True,
        )
        if progress:
            progress("Magisk installed. Restart Waydroid, then run 'wdt extensions magisk setup'.")

    def uninstall(self, progress: Optional[Callable[[str], None]] = None) -> None:
        require_root("Uninstalling Magisk")
        if _MAGISK_MARKER.exists():
            subprocess.run(["sudo", "rm", "-rf", str(_MAGISK_MARKER)], check=True)
        if progress:
            progress("Magisk removed from overlay.")
