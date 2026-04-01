"""Core layer — direct interfaces to Waydroid runtime, ADB, and system privileges."""

from .waydroid import SessionState, WaydroidConfig, get_session_state, is_initialized, is_installed
from .adb import connect as adb_connect, is_available as adb_available, is_connected as adb_connected
from .privilege import is_root, require_root

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
