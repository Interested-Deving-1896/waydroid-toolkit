"""GUI presenter functions — pure data-gathering logic extracted from page classes.

Each function collects the data a page needs to display and returns it as a
plain dataclass or dict. This keeps the QML bridge code thin and makes the
business logic testable without a display server.

Pages call these functions from their background threads via the bridge's
``_run()`` helper, then emit the result as a Qt signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from waydroid_toolkit.core.adb import is_available as adb_available
from waydroid_toolkit.core.adb import is_connected as adb_connected
from waydroid_toolkit.core.waydroid import (
    SessionState,
    WaydroidConfig,
    get_session_state,
    is_initialized,
    is_installed,
)
from waydroid_toolkit.modules.backup.backup import list_backups
from waydroid_toolkit.modules.extensions import ExtensionState
from waydroid_toolkit.modules.extensions import list_all as list_extensions
from waydroid_toolkit.modules.images.manager import (
    get_active_profile,
    scan_profiles,
)
from waydroid_toolkit.modules.maintenance.tools import get_device_info

# ── Status page ───────────────────────────────────────────────────────────────

@dataclass
class StatusData:
    installed: bool
    initialized: bool
    session_state: SessionState
    images_path: str
    mount_overlays: bool
    adb_available: bool
    adb_connected: bool


def get_status_data() -> StatusData:
    """Collect all data needed by the Status page."""
    installed = is_installed()
    initialized = is_initialized() if installed else False
    state = get_session_state() if installed else SessionState.UNKNOWN
    cfg = WaydroidConfig.load()
    adb_ok = adb_available()
    adb_conn = adb_connected() if adb_ok else False
    return StatusData(
        installed=installed,
        initialized=initialized,
        session_state=state,
        images_path=cfg.images_path,
        mount_overlays=cfg.mount_overlays,
        adb_available=adb_ok,
        adb_connected=adb_conn,
    )


# ── Backup page ───────────────────────────────────────────────────────────────

@dataclass
class BackupEntry:
    name: str
    path: Path
    size_mb: float


def get_backup_entries(backup_dir: Path | None = None) -> list[BackupEntry]:
    """Return available backup archives as display-ready entries."""
    archives = list_backups(backup_dir) if backup_dir else list_backups()
    return [
        BackupEntry(
            name=a.name,
            path=a,
            size_mb=a.stat().st_size / (1024 * 1024),
        )
        for a in archives
    ]


# ── Extensions page ───────────────────────────────────────────────────────────

@dataclass
class ExtensionRow:
    ext_id: str
    name: str
    description: str
    state: ExtensionState
    conflicts: list[str] = field(default_factory=list)


def get_extension_rows() -> list[ExtensionRow]:
    """Return all extensions with their current install state."""
    return [
        ExtensionRow(
            ext_id=ext.meta.id,
            name=ext.meta.name,
            description=ext.meta.description,
            state=ext.state(),
            conflicts=ext.meta.conflicts,
        )
        for ext in list_extensions()
    ]


# ── Images page ───────────────────────────────────────────────────────────────

@dataclass
class ImageProfileRow:
    name: str
    path: Path
    is_active: bool


def get_image_profile_rows() -> list[ImageProfileRow]:
    """Return all discovered image profiles, marking the active one."""
    profiles = scan_profiles()
    active = get_active_profile()
    return [
        ImageProfileRow(
            name=p.name,
            path=p.path,
            is_active=bool(active and str(p.path) in active),
        )
        for p in profiles
    ]


# ── Maintenance page ──────────────────────────────────────────────────────────

def get_device_info_data() -> dict[str, str]:
    """Return Android device properties for the Maintenance page."""
    return get_device_info()
