"""Google Apps extension.

Supports two GApps sources depending on the target Android version:
  - Android 11: OpenGApps pico (x86_64) from SourceForge
  - Android 13: MindTheGapps (x86_64) from GitHub

OpenGApps pico zip layout (Android 11)
---------------------------------------
The outer zip contains a ``Core/`` directory of per-app ``.tar.lz`` archives.
Each archive unpacks to one of two shapes:

  APK packages:
    <AppName>/<dpi>/nodpi/<AppDir>/<AppName>.apk [+ lib/]
    installed to overlay/system/priv-app/<AppDir>/

  Non-APK (config/framework) packages:
    <AppName>/common/<etc|framework|...>/...
    installed to overlay/system/<etc|framework|...>/

MindTheGapps zip layout (Android 13)
--------------------------------------
The zip contains a ``system/`` tree that maps 1:1 to the overlay:
  system/priv-app/...  -> overlay/system/priv-app/...
  system/product/...   -> overlay/system/product/...

Host requirements
-----------------
OpenGApps extraction requires ``lzip`` and ``tar`` on PATH.
MindTheGapps uses only Python's ``zipfile`` module.
"""

from __future__ import annotations

import hashlib
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
    "11": {
        "x86_64": (
            "https://sourceforge.net/projects/opengapps/files/x86_64/20220503/"
            "open_gapps-x86_64-11.0-pico-20220503.zip/download",
            "5a6d242be34ad1acf92899c7732afa1b",
        ),
        "x86": (
            "https://sourceforge.net/projects/opengapps/files/x86/20220503/"
            "open_gapps-x86-11.0-pico-20220503.zip/download",
            "efda4943076016d00b40e0874b12ddd3",
        ),
        "arm64-v8a": (
            "https://sourceforge.net/projects/opengapps/files/arm64/20220503/"
            "open_gapps-arm64-11.0-pico-20220503.zip/download",
            "7790055d34bbfc6fe610b0cd263a7add",
        ),
        "armeabi-v7a": (
            "https://sourceforge.net/projects/opengapps/files/arm/20220215/"
            "open_gapps-arm-11.0-pico-20220215.zip/download",
            "8719519fa32ae83a62621c6056d32814",
        ),
    },
    "13": {
        "x86_64": (
            "https://github.com/s1204IT/MindTheGappsBuilder/releases/download/"
            "20231028/MindTheGapps-13.0.0-x86_64-20231028.zip",
            "63ccebbf93d45c384f58d7c40049d398",
        ),
        "x86": (
            "https://github.com/s1204IT/MindTheGappsBuilder/releases/download/"
            "20231028/MindTheGapps-13.0.0-x86-20231028.zip",
            "f12b6a8ed14eedbb4b5b3c932a865956",
        ),
        "arm64-v8a": (
            "https://github.com/s1204IT/MindTheGappsBuilder/releases/download/"
            "20231028/MindTheGapps-13.0.0-arm64-20231028.zip",
            "11180da0a5d9f2ed2863882c30a8d556",
        ),
        "armeabi-v7a": (
            "https://github.com/s1204IT/MindTheGappsBuilder/releases/download/"
            "20231028/MindTheGapps-13.0.0-arm-20231028.zip",
            "d525c980bac427844aa4cb01628f8a8f",
        ),
    },
}

# OpenGApps .tar.lz archives that contain config/framework files (not APKs)
_NON_APK_ARCHIVES = frozenset({
    "defaultetc-common.tar.lz",
    "defaultframework-common.tar.lz",
    "googlepixelconfig-common.tar.lz",
    "vending-common.tar.lz",
})

# OpenGApps archives to skip entirely (setup wizard variants)
_SKIP_ARCHIVES = frozenset({
    "setupwizarddefault-x86_64.tar.lz",
    "setupwizardtablet-x86_64.tar.lz",
})

_OVERLAY_ROOT = Path("/var/lib/waydroid/overlay")
_CACHE_DIR = Path("/tmp/waydroid-toolkit")
_MARKER = _OVERLAY_ROOT / "system" / "priv-app" / "PrebuiltGmsCore"

# Overlay paths removed by uninstall (covers both Android 11 and 13 layouts)
_UNINSTALL_TARGETS = [
    "system/priv-app/PrebuiltGmsCore",
    "system/priv-app/GoogleServicesFramework",
    "system/priv-app/Phonesky",
    "system/priv-app/ConfigUpdater",
    "system/priv-app/GoogleExtServices",
    "system/priv-app/GoogleExtShared",
    "system/priv-app/GoogleFeedback",
    "system/priv-app/GoogleBackupTransport",
    "system/priv-app/GoogleOneTimeInitializer",
    "system/priv-app/GoogleContactsSyncAdapter",
    "system/priv-app/GooglePartnerSetup",
    "system/priv-app/GoogleRestore",
    "system/priv-app/CarrierSetup",
    "system/priv-app/AndroidMigratePrebuilt",
    "system/product/priv-app/GmsCore",
    "system/product/priv-app/Phonesky",
    "system/product/priv-app/Velvet",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_arch() -> str:
    """Return the Waydroid ABI string for the host CPU."""
    import platform
    machine = platform.machine().lower()
    if machine == "x86_64":
        return "x86_64"
    if machine in ("i386", "i686", "x86"):
        return "x86"
    if machine == "aarch64":
        return "arm64-v8a"
    if machine.startswith("arm"):
        return "armeabi-v7a"
    return "x86_64"  # safe default for most Waydroid hosts


def _check_lzip() -> None:
    """Raise RuntimeError if lzip is not on PATH (needed for OpenGApps)."""
    if shutil.which("lzip") is None:
        raise RuntimeError(
            "lzip is required to extract OpenGApps pico.\n"
            "Install it with your package manager, e.g.:\n"
            "  sudo apt install lzip        # Debian/Ubuntu\n"
            "  sudo dnf install lzip        # Fedora\n"
            "  sudo pacman -S lzip          # Arch"
        )


def _sudo_copytree(src: Path, dst: Path) -> None:
    """Recursively copy src into dst using sudo (dst is root-owned overlay)."""
    subprocess.run(["sudo", "mkdir", "-p", str(dst)], check=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _sudo_copytree(item, target)
        else:
            subprocess.run(["sudo", "cp", "-f", str(item), str(target)], check=True)


def install_opengapps_11(
    zip_path: Path,
    overlay_system: Path,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Extract and install an OpenGApps pico Android-11 zip into the overlay."""
    _check_lzip()

    with tempfile.TemporaryDirectory(prefix="wdt-gapps-") as tmp:
        tmp_path = Path(tmp)
        extract_dir = tmp_path / "extract"
        appunpack = tmp_path / "appunpack"
        extract_dir.mkdir()
        appunpack.mkdir()

        if progress:
            progress("Unpacking outer GApps zip…")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        core_dir = extract_dir / "Core"
        if not core_dir.is_dir():
            raise RuntimeError(
                f"Expected 'Core/' directory inside GApps zip, not found in {zip_path}"
            )

        for lz_file in sorted(core_dir.iterdir()):
            name = lz_file.name
            if name in _SKIP_ARCHIVES:
                continue

            # Clear appunpack between archives
            for child in list(appunpack.iterdir()):
                shutil.rmtree(child) if child.is_dir() else child.unlink()

            if progress:
                progress(f"Installing {name}…")

            subprocess.run(
                ["tar", "--lzip", "-xf", str(lz_file), "-C", str(appunpack)],
                check=True,
            )

            app_name_dirs = list(appunpack.iterdir())
            if not app_name_dirs:
                continue
            app_root = app_name_dirs[0]

            if name in _NON_APK_ARCHIVES:
                # Config/framework: <AppName>/common/<etc|framework|...>/
                common_dir = app_root / "common"
                if common_dir.is_dir():
                    for content_dir in common_dir.iterdir():
                        _sudo_copytree(content_dir, overlay_system / content_dir.name)
            else:
                # APK: <AppName>/<dpi>/nodpi/<AppDir>/
                dpi_dirs = list(app_root.iterdir())
                if not dpi_dirs:
                    continue
                dpi_dir = dpi_dirs[0]
                nodpi = dpi_dir / "nodpi"
                src_dir = nodpi if nodpi.is_dir() else dpi_dir
                for app_dir in src_dir.iterdir():
                    _sudo_copytree(app_dir, overlay_system / "priv-app" / app_dir.name)


def install_mindthegapps_13(
    zip_path: Path,
    overlay_system: Path,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Extract and install a MindTheGapps Android-13 zip into the overlay."""
    with tempfile.TemporaryDirectory(prefix="wdt-gapps-") as tmp:
        tmp_path = Path(tmp)

        if progress:
            progress("Unpacking MindTheGapps zip…")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)

        src_system = tmp_path / "system"
        if not src_system.is_dir():
            raise RuntimeError(
                f"Expected 'system/' directory inside MindTheGapps zip, "
                f"not found in {zip_path}"
            )

        if progress:
            progress("Copying files into overlay…")
        _sudo_copytree(src_system, overlay_system)


# ── Extension class ───────────────────────────────────────────────────────────

class GAppsExtension(Extension):
    """Installs Google Apps into the Waydroid overlay.

    Defaults to Android 11 / OpenGApps pico. Pass ``android_version="13"``
    to use MindTheGapps instead.
    """

    def __init__(self, android_version: str = "11") -> None:
        if android_version not in _SOURCES:
            raise ValueError(
                f"Unsupported Android version '{android_version}'. "
                f"Supported: {', '.join(sorted(_SOURCES))}"
            )
        self._android_version = android_version

    @property
    def meta(self) -> ExtensionMeta:
        source = "OpenGApps pico" if self._android_version == "11" else "MindTheGapps"
        return ExtensionMeta(
            id="gapps",
            name=f"Google Apps ({source}, Android {self._android_version})",
            description=(
                f"Installs {source} into the Waydroid overlay "
                f"(Android {self._android_version})."
            ),
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

        arch = detect_arch()
        version_sources = _SOURCES.get(self._android_version, {})
        if arch not in version_sources:
            raise RuntimeError(
                f"No GApps package available for arch '{arch}' / "
                f"Android {self._android_version}."
            )

        url, expected_md5 = version_sources[arch]
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache = _CACHE_DIR / f"gapps-{self._android_version}-{arch}.zip"

        # Re-use cached download if MD5 matches
        if cache.exists() and _md5(cache) == expected_md5:
            if progress:
                progress("Using cached GApps zip.")
        else:
            if progress:
                progress(f"Downloading GApps ({self._android_version}/{arch})…")
            download(
                url,
                cache,
                progress=(
                    (lambda d, t: progress(f"Downloading… {d}/{t} bytes"))
                    if progress else None
                ),
            )
            actual = _md5(cache)
            if actual != expected_md5:
                cache.unlink(missing_ok=True)
                raise RuntimeError(
                    f"GApps zip MD5 mismatch: expected {expected_md5}, got {actual}. "
                    "The download may be corrupt. Try again."
                )

        overlay_system = _OVERLAY_ROOT / "system"
        subprocess.run(["sudo", "mkdir", "-p", str(overlay_system)], check=True)

        if self._android_version == "11":
            install_opengapps_11(cache, overlay_system, progress)
        else:
            install_mindthegapps_13(cache, overlay_system, progress)

        if progress:
            progress("GApps installed. Restart Waydroid to apply.")

    def uninstall(self, progress: Callable[[str], None] | None = None) -> None:
        require_root("Uninstalling GApps")
        for rel in _UNINSTALL_TARGETS:
            target = _OVERLAY_ROOT / rel
            if target.exists():
                subprocess.run(["sudo", "rm", "-rf", str(target)], check=True)
                if progress:
                    progress(f"Removed {target.name}")
        if progress:
            progress("GApps removed from overlay.")
