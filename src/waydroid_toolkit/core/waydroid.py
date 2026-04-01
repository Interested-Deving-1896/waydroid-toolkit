"""Low-level interface to the Waydroid runtime.

Wraps the waydroid CLI and reads /var/lib/waydroid/waydroid.cfg.
All other modules go through this layer rather than shelling out directly.
"""

from __future__ import annotations

import configparser
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

_CFG_PATH = Path("/var/lib/waydroid/waydroid.cfg")
_USER_DATA = Path.home() / ".local/share/waydroid"


class SessionState(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class WaydroidConfig:
    images_path: str = ""
    mount_overlays: bool = True
    suspend_action: str = "freeze"
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls) -> WaydroidConfig:
        if not _CFG_PATH.exists():
            return cls()
        parser = configparser.ConfigParser()
        parser.read(_CFG_PATH)
        waydroid_section = parser["waydroid"] if "waydroid" in parser else {}
        return cls(
            images_path=waydroid_section.get("images_path", ""),
            mount_overlays=waydroid_section.get("mount_overlays", "true").lower() == "true",
            suspend_action=waydroid_section.get("suspend_action", "freeze"),
        )


def get_session_state() -> SessionState:
    """Return the current Waydroid session state."""
    try:
        result = subprocess.run(
            ["waydroid", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.lower()
        if "running" in output:
            return SessionState.RUNNING
        return SessionState.STOPPED
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return SessionState.UNKNOWN


def run_waydroid(
    *args: str, sudo: bool = False, timeout: int = 60
) -> subprocess.CompletedProcess[str]:
    """Run a waydroid subcommand, optionally with sudo."""
    cmd = (["sudo"] if sudo else []) + ["waydroid", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def shell(command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Execute a command inside the Waydroid Android shell via waydroid shell."""
    return subprocess.run(
        ["sudo", "waydroid", "shell", command],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def is_installed() -> bool:
    """Return True if the waydroid binary is present on PATH."""
    try:
        subprocess.run(["waydroid", "--version"], capture_output=True, timeout=3)
        return True
    except FileNotFoundError:
        return False


def is_initialized() -> bool:
    """Return True if Waydroid has been initialised (images present)."""
    cfg = WaydroidConfig.load()
    if not cfg.images_path:
        return False
    images = Path(cfg.images_path)
    return (images / "system.img").exists() and (images / "vendor.img").exists()


def get_android_id() -> str | None:
    """Retrieve the Android device ID needed for GApps registration."""
    result = shell(
        'ANDROID_RUNTIME_ROOT=/apex/com.android.runtime sqlite3 '
        '/data/data/com.google.android.gsf/databases/gservices.db '
        '"select * from main where name = \\"android_id\\";"'
    )
    if result.returncode == 0 and result.stdout.strip():
        parts = result.stdout.strip().split("|")
        return parts[-1] if parts else None
    return None
