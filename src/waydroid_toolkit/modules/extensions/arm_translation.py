"""ARM translation layer extensions — libhoudini and libndk.

libhoudini: Intel's translation layer, better for Intel/AMD x86 hosts.
libndk:     Google's NDK translation, better performance on AMD.

Sources mirror casualsnek/waydroid_script which pulls from WSA and guybrush firmware.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Optional

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.utils.net import download
from waydroid_toolkit.utils.overlay import is_overlay_enabled
from .base import Extension, ExtensionMeta

_HOUDINI_URL = (
    "https://github.com/casualsnek/waydroid_script/raw/main/stuff/houdini.zip"
)
_NDK_URL = (
    "https://github.com/casualsnek/waydroid_script/raw/main/stuff/ndk_translation.zip"
)

_HOUDINI_MARKER = Path("/var/lib/waydroid/overlay/system/lib/libhoudini.so")
_NDK_MARKER = Path("/var/lib/waydroid/overlay/system/lib/libndk_translation.so")


class LibhoudiniExtension(Extension):
    @property
    def meta(self) -> ExtensionMeta:
        return ExtensionMeta(
            id="libhoudini",
            name="libhoudini (Intel ARM translation)",
            description="Intel's ARM-to-x86 translation layer. Recommended for Intel/AMD hosts.",
            requires_root=True,
            conflicts=["libndk"],
        )

    def is_installed(self) -> bool:
        return _HOUDINI_MARKER.exists()

    def install(self, progress: Optional[Callable[[str], None]] = None) -> None:
        require_root("Installing libhoudini")
        if not is_overlay_enabled():
            raise RuntimeError("mount_overlays must be enabled.")
        cache = Path("/tmp/waydroid-toolkit/houdini.zip")
        if progress:
            progress("Downloading libhoudini...")
        download(_HOUDINI_URL, cache)
        if progress:
            progress("Extracting libhoudini into overlay...")
        subprocess.run(
            ["sudo", "unzip", "-o", str(cache), "-d", "/var/lib/waydroid/overlay"],
            check=True,
        )
        if progress:
            progress("libhoudini installed. Restart Waydroid to apply.")

    def uninstall(self, progress: Optional[Callable[[str], None]] = None) -> None:
        require_root("Uninstalling libhoudini")
        for path in [
            "/var/lib/waydroid/overlay/system/lib/libhoudini.so",
            "/var/lib/waydroid/overlay/system/lib64/libhoudini.so",
        ]:
            subprocess.run(["sudo", "rm", "-f", path], capture_output=True)
        if progress:
            progress("libhoudini removed.")


class LibndkExtension(Extension):
    @property
    def meta(self) -> ExtensionMeta:
        return ExtensionMeta(
            id="libndk",
            name="libndk (Google NDK ARM translation)",
            description="Google's NDK translation layer from guybrush firmware. Better on AMD.",
            requires_root=True,
            conflicts=["libhoudini"],
        )

    def is_installed(self) -> bool:
        return _NDK_MARKER.exists()

    def install(self, progress: Optional[Callable[[str], None]] = None) -> None:
        require_root("Installing libndk")
        if not is_overlay_enabled():
            raise RuntimeError("mount_overlays must be enabled.")
        cache = Path("/tmp/waydroid-toolkit/ndk_translation.zip")
        if progress:
            progress("Downloading libndk...")
        download(_NDK_URL, cache)
        if progress:
            progress("Extracting libndk into overlay...")
        subprocess.run(
            ["sudo", "unzip", "-o", str(cache), "-d", "/var/lib/waydroid/overlay"],
            check=True,
        )
        if progress:
            progress("libndk installed. Restart Waydroid to apply.")

    def uninstall(self, progress: Optional[Callable[[str], None]] = None) -> None:
        require_root("Uninstalling libndk")
        for path in [
            "/var/lib/waydroid/overlay/system/lib/libndk_translation.so",
            "/var/lib/waydroid/overlay/system/lib64/libndk_translation.so",
        ]:
            subprocess.run(["sudo", "rm", "-f", path], capture_output=True)
        if progress:
            progress("libndk removed.")
