"""ZFS snapshot backend.

Snapshots the ZFS dataset that contains ``/var/lib/waydroid``.

All ZFS operations require root (or the ``zfs allow`` delegation).
Commands are run via ``sudo zfs ...``.
"""

from __future__ import annotations

import datetime
import subprocess
from pathlib import Path

from .backends import SnapshotBackend, SnapshotInfo

# Default dataset to snapshot — can be overridden via the constructor.
_DEFAULT_DATASET = "rpool/waydroid"


class ZfsBackend(SnapshotBackend):
    """Snapshot backend using ZFS send/receive and ``zfs snapshot``."""

    NAME = "zfs"

    def __init__(self, dataset: str = _DEFAULT_DATASET) -> None:
        self._dataset = dataset

    # ── SnapshotBackend interface ─────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if ``zfs`` is on PATH and *dataset* exists."""
        try:
            result = subprocess.run(
                ["zfs", "list", "-H", self._dataset],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def create(self, label: str = "") -> SnapshotInfo:
        name = self._snap_name(label)
        snap_id = f"{self._dataset}@{name}"
        _run(["sudo", "zfs", "snapshot", snap_id])
        return SnapshotInfo(
            name=name,
            created=datetime.datetime.now(tz=datetime.timezone.utc),
            backend=self.NAME,
            source=self._dataset,
            size_bytes=self._snap_size(snap_id),
        )

    def list(self) -> list[SnapshotInfo]:
        result = _run(
            ["zfs", "list", "-H", "-t", "snapshot", "-o", "name,creation,used",
             "-r", self._dataset],
            check=False,
        )
        snaps: list[SnapshotInfo] = []
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            full_name, creation_str, used_str = parts[0], parts[1], parts[2]
            if "@" not in full_name:
                continue
            _, snap_name = full_name.split("@", 1)
            if not snap_name.startswith("waydroid-"):
                continue
            try:
                created = datetime.datetime.strptime(
                    creation_str, "%a %b %d %H:%M %Y"
                ).replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                created = datetime.datetime.now(tz=datetime.timezone.utc)
            size = _parse_zfs_size(used_str)
            snaps.append(SnapshotInfo(
                name=snap_name,
                created=created,
                backend=self.NAME,
                source=self._dataset,
                size_bytes=size,
            ))
        return sorted(snaps, key=lambda s: s.created, reverse=True)

    def restore(self, name: str) -> None:
        snap_id = f"{self._dataset}@{name}"
        _run(["sudo", "zfs", "rollback", "-r", snap_id])

    def delete(self, name: str) -> None:
        snap_id = f"{self._dataset}@{name}"
        _run(["sudo", "zfs", "destroy", snap_id])

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _snap_size(self, snap_id: str) -> int | None:
        try:
            result = _run(
                ["zfs", "get", "-H", "-o", "value", "used", snap_id],
                check=False,
            )
            return _parse_zfs_size(result.stdout.strip())
        except Exception:  # noqa: BLE001
            return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(
    cmd: list[str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"ZFS command failed: {' '.join(cmd)}\n{result.stderr.strip()}"
        )
    return result


def _parse_zfs_size(value: str) -> int | None:
    """Parse a ZFS human-readable size string (e.g. ``1.23G``) to bytes."""
    suffixes = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    value = value.strip()
    if not value or value == "-":
        return None
    try:
        if value[-1].upper() in suffixes:
            return int(float(value[:-1]) * suffixes[value[-1].upper()])
        return int(value)
    except (ValueError, IndexError):
        return None
