"""Core layer — direct interfaces to Waydroid runtime, ADB, and system privileges."""

from .adb import connect as adb_connect
from .adb import is_available as adb_available
from .adb import is_connected as adb_connected
from .privilege import is_root, require_root
from .waydroid import SessionState, WaydroidConfig, get_session_state, is_initialized, is_installed

__all__ = [
    "SessionState",
    "WaydroidConfig",
    "get_session_state",
    "is_initialized",
    "is_installed",
    "adb_connect",
    "adb_available",
    "adb_connected",
    "is_root",
    "require_root",
]
