"""Waydroid image profile manager.

Manages multiple system/vendor image profiles and switches between them
with full data isolation (userdata and overlay per profile).

Mirrors the behaviour of amir0zx/waydroid-image-sw.

Profile layout under ~/waydroid-images/:
  ~/waydroid-images/
    vanilla/
      system.img
      vendor.img
    gapps/
      system.img
      vendor.img
    androidtv/
      system.img
      vendor.img
"""

from __future__ import annotations

import configparser
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.core.waydroid import get_session_state, run_waydroid, SessionState, WaydroidConfig

_IMAGES_BASE = Path.home() / "waydroid-images"
_PROFILES_BASE = Path.home() / ".local/share/waydroid/profiles"
_LIVE_DATA = Path.home() / ".local/share/waydroid/data"
_CFG_PATH = Path("/var/lib/waydroid/waydroid.cfg")


@dataclass
class ImageProfile:
    name: str
    path: Path

    @property
    def system_img(self) -> Path:
        return self.path / "system.img"

    @property
    def vendor_img(self) -> Path:
        return self.path / "vendor.img"

    @property
    def is_valid(self) -> bool:
        return self.system_img.exists() and self.vendor_img.exists()


def scan_profiles(base: Path = _IMAGES_BASE) -> list[ImageProfile]:
    """Recursively scan base for directories containing system.img + vendor.img."""
    profiles = []
    if not base.exists():
        return profiles
    for candidate in sorted(base.rglob("system.img")):
        profile_dir = candidate.parent
        if (profile_dir / "vendor.img").exists():
            profiles.append(ImageProfile(name=profile_dir.name, path=profile_dir))
    return profiles


def get_active_profile() -> Optional[str]:
    """Return the images_path from waydroid.cfg, or None if not set."""
    cfg = WaydroidConfig.load()
    return cfg.images_path or None


def _set_images_path(path: Path) -> None:
    """Update images_path in /var/lib/waydroid/waydroid.cfg."""
    parser = configparser.ConfigParser()
    parser.read(_CFG_PATH)
    if "waydroid" not in parser:
        parser["waydroid"] = {}
    parser["waydroid"]["images_path"] = str(path)
    tmp = _CFG_PATH.with_suffix(".tmp")
    with tmp.open("w") as fh:
        parser.write(fh)
    subprocess.run(["sudo", "mv", str(tmp), str(_CFG_PATH)], check=True)


def _link_profile_data(profile_name: str) -> None:
    """Symlink live userdata and overlays to profile-specific directories."""
    profile_store = _PROFILES_BASE / profile_name
    profile_store.mkdir(parents=True, exist_ok=True)

    profile_data = profile_store / "data"
    profile_data.mkdir(parents=True, exist_ok=True)

    # Replace live data symlink
    if _LIVE_DATA.is_symlink():
        _LIVE_DATA.unlink()
    elif _LIVE_DATA.exists():
        _LIVE_DATA.rename(_LIVE_DATA.with_suffix(".bak"))
    _LIVE_DATA.symlink_to(profile_data)

    # Overlay directories
    for overlay_name in ("overlay_rw", "overlay_work"):
        live = Path("/var/lib/waydroid") / overlay_name
        stored = profile_store / overlay_name
        subprocess.run(["sudo", "mkdir", "-p", str(stored)], check=True)
        subprocess.run(["sudo", "rm", "-rf", str(live)], check=True)
        subprocess.run(["sudo", "ln", "-s", str(stored), str(live)], check=True)


def switch_profile(
    profile: ImageProfile,
    progress: Optional[Callable[[str], None]] = None,
) -> None:
    """Switch Waydroid to the given image profile."""
    require_root("Switching image profile")
    if not profile.is_valid:
        raise ValueError(f"Profile '{profile.name}' is missing system.img or vendor.img")

    if get_session_state() == SessionState.RUNNING:
        if progress:
            progress("Stopping Waydroid session...")
        run_waydroid("session", "stop", sudo=True)
        subprocess.run(["sudo", "systemctl", "stop", "waydroid-container"], capture_output=True)

    if progress:
        progress(f"Switching to profile: {profile.name}")
    _set_images_path(profile.path)
    _link_profile_data(profile.name)

    if progress:
        progress(f"Active profile is now '{profile.name}'. Start Waydroid to apply.")
