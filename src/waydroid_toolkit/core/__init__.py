"""Core layer — Waydroid runtime, ADB, container backend, and privilege helpers."""

from .adb import connect as adb_connect
from .adb import is_available as adb_available
from .adb import is_connected as adb_connected
from .container import (
    BackendType,
    ContainerBackend,
    ContainerState,
    IncusBackend,
    LxcBackend,
)
from .container import (
    detect as detect_backend,
)
from .container import (
    get_active as get_active_backend,
)
from .container import (
    list_available as list_available_backends,
)
from .container import (
    set_active as set_active_backend,
)
from .privilege import is_root, require_root
from .waydroid import SessionState, WaydroidConfig, get_session_state, is_initialized, is_installed

__all__ = [
    # Waydroid runtime
    "SessionState",
    "WaydroidConfig",
    "get_session_state",
    "is_initialized",
    "is_installed",
    # ADB
    "adb_connect",
    "adb_available",
    "adb_connected",
    # Privilege
    "is_root",
    "require_root",
    # Container backend
    "BackendType",
    "ContainerBackend",
    "ContainerState",
    "IncusBackend",
    "LxcBackend",
    "detect_backend",
    "get_active_backend",
    "list_available_backends",
    "set_active_backend",
]
