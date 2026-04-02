"""Snapshot support for Waydroid data directories.

Provides filesystem-level snapshots via ZFS or btrfs, with a common
interface so callers don't need to know which backend is active.

Usage
-----
    from waydroid_toolkit.modules.snapshot import get_backend, SnapshotInfo

    backend = get_backend()          # auto-detects ZFS or btrfs
    snap = backend.create("before-gapps-install")
    ...
    backend.restore(snap.name)
    backend.delete(snap.name)
"""

from .backends import SnapshotBackend, SnapshotInfo
from .btrfs import BtrfsBackend
from .detector import detect_backend, get_backend
from .zfs import ZfsBackend

__all__ = [
    "BtrfsBackend",
    "SnapshotBackend",
    "SnapshotInfo",
    "ZfsBackend",
    "detect_backend",
    "get_backend",
]
