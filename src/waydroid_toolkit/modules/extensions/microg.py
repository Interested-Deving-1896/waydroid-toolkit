"""microG extension — privacy-respecting Google Services replacement."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Optional

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.utils.net import download
from waydroid_toolkit.utils.overlay import is_overlay_enabled
from .base import Extension, ExtensionMeta

_MICROG_URL = "https://github.com/casualsnek/waydroid_script/raw/main/stuff/microg.zip"
_MICROG_MARKER = Path("/var/lib/waydroid/overlay/system/priv-app/GmsCore")


class MicroGExtension(Extension):
    @property
    def meta(self) -> ExtensionMeta:
        return ExtensionMeta(
            id="microg",
            name="microG",
            description=(
                "Open-source reimplementation of Google Play Services. "
                "Also installs Aurora Store and Aurora Droid."
            ),
            requires_root=True,
            conflicts=["gapps"],
        )

    def is_installed(self) -> bool:
        return _MICROG_MARKER.exists()

    def install(self, progress: Optional[Callable[[str], None]] = None) -> None:
        require_root("Installing microG")
        if not is_overlay_enabled():
            raise RuntimeError("mount_overlays must be enabled.")
        cache = Path("/tmp/waydroid-toolkit/microg.zip")
        if progress:
            progress("Downloading microG...")
        download(_MICROG_URL, cache)
        if progress:
            progress("Extracting microG into overlay...")
        subprocess.run(
            ["sudo", "unzip", "-o", str(cache), "-d", "/var/lib/waydroid/overlay"],
            check=True,
        )
        if progress:
            progress("microG installed. Restart Waydroid to apply.")

    def uninstall(self, progress: Optional[Callable[[str], None]] = None) -> None:
        require_root("Uninstalling microG")
        subprocess.run(["sudo", "rm", "-rf", str(_MICROG_MARKER)], capture_output=True)
        if progress:
            progress("microG removed.")
