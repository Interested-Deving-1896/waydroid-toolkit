"""Abstract snapshot backend interface."""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SnapshotInfo:
    """Metadata for a single snapshot."""

    name: str
    """Unique snapshot identifier (e.g. ``waydroid-20240101_120000``)."""

    created: datetime.datetime
    """Creation timestamp (UTC)."""

    backend: str
    """Backend that owns this snapshot (``"zfs"`` or ``"btrfs"``)."""

    source: str
    """Dataset or subvolume path that was snapshotted."""

    size_bytes: int | None = None
    """Approximate size on disk, or None if unavailable."""


class SnapshotBackend(ABC):
    """Common interface for ZFS and btrfs snapshot backends."""

    NAME: str = ""  # overridden by subclasses

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this backend's tools and filesystem are present."""

    @abstractmethod
    def create(self, label: str = "") -> SnapshotInfo:
        """Take a snapshot of the Waydroid data directory.

        Parameters
        ----------
        label:
            Optional human-readable suffix appended to the snapshot name.

        Returns
        -------
        SnapshotInfo
            Metadata for the newly created snapshot.
        """

    @abstractmethod
    def list(self) -> list[SnapshotInfo]:
        """Return all snapshots managed by this backend, newest first."""

    @abstractmethod
    def restore(self, name: str) -> None:
        """Roll back the Waydroid data directory to *name*.

        The Waydroid session must be stopped before calling this.
        """

    @abstractmethod
    def delete(self, name: str) -> None:
        """Permanently delete the snapshot identified by *name*."""

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _timestamp() -> str:
        return datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d_%H%M%S")

    def _snap_name(self, label: str) -> str:
        ts = self._timestamp()
        suffix = f"-{label}" if label else ""
        return f"waydroid-{ts}{suffix}"
