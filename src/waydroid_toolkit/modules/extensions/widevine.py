"""Widevine L3 DRM extension.

Installs Google's Widevine L3 DRM library into the Waydroid vendor overlay,
enabling DRM-protected content playback (Netflix, Disney+, etc.) at L3 level.

Sources
-------
Android 11 (x86_64): supremegamers/vendor_google_proprietary_widevine-prebuilt
Android 13 (x86_64): WayDroid-ATV/vendor_google_proprietary_widevine-prebuilt
Android 11 (arm64):  supremegamers/vendor_google_proprietary_widevine-prebuilt

Zip layout
----------
The downloaded zip extracts to:
  vendor_google_proprietary_widevine-prebuilt-<sha>/prebuilts/
    bin/hw/*widevine*
    bin/move_widevine_data.sh
    etc/init/*widevine.rc
    etc/vintf/manifest/*widevine.xml
    lib/libwvhidl.so  lib/libwvaidl.so  lib/mediadrm/
    lib64/libwvhidl.so  lib64/libwvaidl.so  lib64/mediadrm/

These map directly to /var/lib/waydroid/overlay/vendor/.

Android 13 note
---------------
Android 13 requires a libprotobuf symlink:
  vendor/lib64/libprotobuf-cpp-lite.so -> libprotobuf-cpp-lite-3.9.1.so
"""

from __future__ import annotations

import hashlib
import platform
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.utils.net import download
from waydroid_toolkit.utils.overlay import is_overlay_enabled

from .base import Extension, ExtensionMeta

# ── Download catalogue ────────────────────────────────────────────────────────

_SOURCES: dict[str, dict[str, tuple[str, str]]] = {
    "x86_64": {
        "11": (
            "https://github.com/supremegamers/vendor_google_proprietary_widevine-prebuilt"
            "/archive/48d1076a570837be6cdce8252d5d143363e37cc1.zip",
            "f587b8859f9071da4bca6cea1b9bed6a",
        ),
        "13": (
            "https://github.com/WayDroid-ATV/vendor_google_proprietary_widevine-prebuilt"
            "/archive/679552343d8b2e8d7a19b6df61c7a03963d0c75b.zip",
            "80ab79ea85c7b2556baedb371a54e01c",
        ),
    },
    "arm64-v8a": {
        "11": (
            "https://github.com/supremegamers/vendor_google_proprietary_widevine-prebuilt"
            "/archive/a1a19361d36311bee042da8cf4ced798d2c76d98.zip",
            "fed6898b5cfd2a908cb134df97802554",
        ),
    },
}

_OVERLAY_VENDOR = Path("/var/lib/waydroid/overlay/vendor")
_CACHE_DIR = Path("/tmp/waydroid-toolkit")
_MARKER = _OVERLAY_VENDOR / "lib64" / "libwvhidl.so"


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _detect_arch() -> str:
    machine = platform.machine().lower()
    if machine == "x86_64":
        return "x86_64"
    if machine == "aarch64":
        return "arm64-v8a"
    return "x86_64"


def _sudo_copytree(src: Path, dst: Path) -> None:
    subprocess.run(["sudo", "mkdir", "-p", str(dst)], check=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _sudo_copytree(item, target)
        else:
            subprocess.run(["sudo", "cp", "-f", str(item), str(target)], check=True)


def install_widevine(
    zip_path: Path,
    overlay_vendor: Path,
    android_version: str,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Extract *zip_path* and install Widevine files into *overlay_vendor*."""
    with tempfile.TemporaryDirectory(prefix="wdt-widevine-") as tmp:
        tmp_path = Path(tmp)

        if progress:
            progress("Unpacking Widevine zip…")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)

        # Find the extracted directory (named vendor_google_...-<sha>)
        extracted = [d for d in tmp_path.iterdir() if d.is_dir()]
        if not extracted:
            raise RuntimeError("Widevine zip extracted no directories.")
        prebuilts = extracted[0] / "prebuilts"
        if not prebuilts.is_dir():
            raise RuntimeError(
                f"Expected 'prebuilts/' inside Widevine zip, not found in {zip_path}"
            )

        if progress:
            progress("Copying Widevine files into vendor overlay…")
        _sudo_copytree(prebuilts, overlay_vendor)

        # Android 13 requires a libprotobuf compatibility symlink
        if android_version == "13":
            lib64 = overlay_vendor / "lib64"
            link = lib64 / "libprotobuf-cpp-lite.so"
            target = "libprotobuf-cpp-lite-3.9.1.so"
            if not link.exists():
                subprocess.run(
                    ["sudo", "ln", "-sf", target, str(link)], check=True
                )
                if progress:
                    progress("Created libprotobuf-cpp-lite.so symlink (Android 13).")


class WidevineExtension(Extension):
    """Installs Widevine L3 DRM into the Waydroid vendor overlay.

    Enables L3-level DRM playback for streaming apps. L1 (hardware-backed)
    is not achievable in a container environment.
    """

    def __init__(self, android_version: str = "11") -> None:
        supported = {"11", "13"}
        if android_version not in supported:
            raise ValueError(
                f"Unsupported Android version '{android_version}'. "
                f"Supported: {', '.join(sorted(supported))}"
            )
        self._android_version = android_version

    @property
    def meta(self) -> ExtensionMeta:
        return ExtensionMeta(
            id="widevine",
            name=f"Widevine L3 (Android {self._android_version})",
            description=(
                "Google Widevine L3 DRM library. Enables protected content "
                "playback in streaming apps (Netflix, Disney+, etc.)."
            ),
            requires_root=True,
        )

    def is_installed(self) -> bool:
        return _MARKER.exists()

    def install(self, progress: Callable[[str], None] | None = None) -> None:
        require_root("Installing Widevine")
        if not is_overlay_enabled():
            raise RuntimeError(
                "mount_overlays must be enabled in waydroid.cfg to install Widevine."
            )

        arch = _detect_arch()
        arch_sources = _SOURCES.get(arch, {})
        if self._android_version not in arch_sources:
            raise RuntimeError(
                f"No Widevine package for arch '{arch}' / "
                f"Android {self._android_version}."
            )

        url, expected_md5 = arch_sources[self._android_version]
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache = _CACHE_DIR / f"widevine-{self._android_version}-{arch}.zip"

        if cache.exists() and _md5(cache) == expected_md5:
            if progress:
                progress("Using cached Widevine zip.")
        else:
            if progress:
                progress(f"Downloading Widevine ({self._android_version}/{arch})…")
            download(url, cache)
            actual = _md5(cache)
            if actual != expected_md5:
                cache.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Widevine zip MD5 mismatch: expected {expected_md5}, got {actual}."
                )

        subprocess.run(["sudo", "mkdir", "-p", str(_OVERLAY_VENDOR)], check=True)
        install_widevine(cache, _OVERLAY_VENDOR, self._android_version, progress)

        if progress:
            progress("Widevine installed. Restart Waydroid to apply.")

    def uninstall(self, progress: Callable[[str], None] | None = None) -> None:
        require_root("Uninstalling Widevine")
        targets = [
            _OVERLAY_VENDOR / "lib" / "libwvhidl.so",
            _OVERLAY_VENDOR / "lib" / "libwvaidl.so",
            _OVERLAY_VENDOR / "lib" / "mediadrm",
            _OVERLAY_VENDOR / "lib64" / "libwvhidl.so",
            _OVERLAY_VENDOR / "lib64" / "libwvaidl.so",
            _OVERLAY_VENDOR / "lib64" / "mediadrm",
            _OVERLAY_VENDOR / "lib64" / "libprotobuf-cpp-lite.so",
            _OVERLAY_VENDOR / "bin" / "hw",
            _OVERLAY_VENDOR / "bin" / "move_widevine_data.sh",
            _OVERLAY_VENDOR / "etc" / "init",
            _OVERLAY_VENDOR / "etc" / "vintf" / "manifest",
        ]
        for t in targets:
            if t.exists():
                subprocess.run(["sudo", "rm", "-rf", str(t)], check=True)
                if progress:
                    progress(f"Removed {t.relative_to(_OVERLAY_VENDOR)}")
        if progress:
            progress("Widevine removed from overlay.")
