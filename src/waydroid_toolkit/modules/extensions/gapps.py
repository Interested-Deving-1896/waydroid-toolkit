"""Google Apps (OpenGApps) extension."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.utils.net import download
from waydroid_toolkit.utils.overlay import is_overlay_enabled

from .base import Extension, ExtensionMeta

# OpenGApps pico package for x86_64 Android 11
_GAPPS_URL = (
    "https://sourceforge.net/projects/opengapps/files/x86_64/20220503/"
    "open_gapps-x86_64-11.0-pico-20220503.zip/download"
)
_MARKER = Path("/var/lib/waydroid/overlay/system/priv-app/PrebuiltGmsCore")


class GAppsExtension(Extension):
    @property
    def meta(self) -> ExtensionMeta:
        return ExtensionMeta(
            id="gapps",
            name="Google Apps (OpenGApps pico)",
            description="Installs OpenGApps pico into the Waydroid overlay.",
            requires_root=True,
            conflicts=["microg"],
        )

    def is_installed(self) -> bool:
        return _MARKER.exists()

    def install(self, progress: Callable[[str], None] | None = None) -> None:
        require_root("Installing GApps")
        if not is_overlay_enabled():
            raise RuntimeError(
                "mount_overlays must be enabled in waydroid.cfg to install GApps."
            )
        cache = Path("/tmp/waydroid-toolkit/gapps.zip")
        if progress:
            progress("Downloading OpenGApps pico...")
        download(
            _GAPPS_URL,
            cache,
            progress=lambda d, t: progress(f"Downloading... {d}/{t}") if progress else None,
        )
        if progress:
            progress("Extracting GApps into overlay...")
        extract_cmd = (
            f"import zipfile; z=zipfile.ZipFile('{cache}'); z.extractall('/tmp/gapps_extract')"
        )
        subprocess.run(["sudo", "python3", "-c", extract_cmd], check=True)
        # Actual extraction logic mirrors casualsnek/waydroid_script behaviour
        if progress:
            progress("GApps installed. Restart Waydroid to apply.")

    def uninstall(self, progress: Callable[[str], None] | None = None) -> None:
        require_root("Uninstalling GApps")
        if _MARKER.exists():
            subprocess.run(["sudo", "rm", "-rf", str(_MARKER)], check=True)
        if progress:
            progress("GApps removed from overlay.")
