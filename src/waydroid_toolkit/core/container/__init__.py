"""Container backend abstraction.

Provides a swappable interface over LXC and Incus so that all modules
above core/ are agnostic to which container runtime is in use.

Typical usage
-------------
    from waydroid_toolkit.core.container import get_active, BackendType

    backend = get_active()          # reads config or auto-detects
    state   = backend.get_state()
    backend.execute(["getprop", "ro.build.version.release"])
"""

from .base import BackendInfo, BackendType, ContainerBackend, ContainerState
from .incus_backend import IncusBackend
from .lxc_backend import LxcBackend
from .selector import detect, get_active, list_available, set_active

__all__ = [
    "BackendInfo",
    "BackendType",
    "ContainerBackend",
    "ContainerState",
    "IncusBackend",
    "LxcBackend",
    "detect",
    "get_active",
    "list_available",
    "set_active",
]
