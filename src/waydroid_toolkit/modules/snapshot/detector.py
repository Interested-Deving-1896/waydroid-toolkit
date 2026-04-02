"""Auto-detect the available snapshot backend.

Preference order: ZFS > btrfs.  Returns None if neither is available.
"""

from __future__ import annotations

from .backends import SnapshotBackend
from .btrfs import BtrfsBackend
from .zfs import ZfsBackend


def detect_backend() -> SnapshotBackend | None:
    """Return the first available snapshot backend, or None.

    Checks ZFS first (preferred), then btrfs.
    """
    for backend in (ZfsBackend(), BtrfsBackend()):
        if backend.is_available():
            return backend
    return None


def get_backend() -> SnapshotBackend:
    """Return the active snapshot backend.

    Raises
    ------
    RuntimeError
        If neither ZFS nor btrfs is available on this system.
    """
    backend = detect_backend()
    if backend is None:
        raise RuntimeError(
            "No snapshot backend available. "
            "Install ZFS (zfsutils-linux) or ensure /var/lib/waydroid "
            "is on a btrfs subvolume."
        )
    return backend
