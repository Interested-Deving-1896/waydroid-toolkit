"""Low-level interface to the Waydroid runtime.

Wraps the waydroid CLI and reads /var/lib/waydroid/waydroid.cfg.
Container lifecycle queries (state, exec) are routed through the active
ContainerBackend so that LXC and Incus are interchangeable.
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
    system_ota: str = "https://ota.waydro.id/system"
    vendor_ota: str = "https://ota.waydro.id/vendor"
    system_datetime: int = 0
    vendor_datetime: int = 0
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
            system_ota=waydroid_section.get("system_ota", "https://ota.waydro.id/system"),
            vendor_ota=waydroid_section.get("vendor_ota", "https://ota.waydro.id/vendor"),
            system_datetime=int(waydroid_section.get("system_datetime", "0")),
            vendor_datetime=int(waydroid_section.get("vendor_datetime", "0")),
        )


def get_session_state() -> SessionState:
    """Return the current Waydroid session state.

    Queries the active container backend first (backend-agnostic). Falls
    back to parsing `waydroid status` output if the backend is unavailable.
    """
    # Lazy import avoids a circular dependency at module load time.
    from waydroid_toolkit.core.container import ContainerState
    from waydroid_toolkit.core.container import get_active as _get_backend

    try:
        backend = _get_backend()
        state = backend.get_state()
        _map = {
            ContainerState.RUNNING: SessionState.RUNNING,
            ContainerState.STOPPED: SessionState.STOPPED,
            ContainerState.FROZEN: SessionState.STOPPED,
            ContainerState.UNKNOWN: SessionState.UNKNOWN,
        }
        return _map[state]
    except Exception:
        pass

    # Fallback: parse waydroid CLI output directly
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
    """Execute a command inside the Waydroid Android shell.

    Routes through the active container backend so the call works
    identically whether LXC or Incus is in use.
    Falls back to `waydroid shell` if the backend is unavailable.
    """
    from waydroid_toolkit.core.container import get_active as _get_backend

    try:
        backend = _get_backend()
        return backend.execute(command.split(), timeout=timeout)
    except Exception:
        pass

    # Fallback: use the waydroid CLI directly
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
