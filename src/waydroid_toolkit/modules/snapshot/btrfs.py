"""btrfs snapshot backend.

Snapshots the btrfs subvolume that contains ``/var/lib/waydroid`` using
``btrfs subvolume snapshot``.  Read-only snapshots are stored alongside
the source subvolume in a ``_snapshots/`` directory.

All btrfs operations require root. Commands are run via ``sudo btrfs ...``.
"""

from __future__ import annotations

import datetime
import subprocess
from pathlib import Path

from .backends import SnapshotBackend, SnapshotInfo

# Default subvolume path for Waydroid data.
_DEFAULT_SUBVOL = Path("/var/lib/waydroid")
# Snapshots are stored in a sibling directory.
_DEFAULT_SNAP_DIR = Path("/var/lib/waydroid_snapshots")


class BtrfsBackend(SnapshotBackend):
    """Snapshot backend using ``btrfs subvolume snapshot``."""

    NAME = "btrfs"

    def __init__(
        self,
        subvol: Path = _DEFAULT_SUBVOL,
        snap_dir: Path = _DEFAULT_SNAP_DIR,
    ) -> None:
        self._subvol = subvol
        self._snap_dir = snap_dir

    # ── SnapshotBackend interface ─────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if ``btrfs`` is on PATH and *subvol* is a btrfs subvolume."""
        try:
            result = subprocess.run(
                ["btrfs", "subvolume", "show", str(self._subvol)],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def create(self, label: str = "") -> SnapshotInfo:
        name = self._snap_name(label)
        dest = self._snap_dir / name
        _run(["sudo", "mkdir", "-p", str(self._snap_dir)])
        _run([
            "sudo", "btrfs", "subvolume", "snapshot",
            "-r",                    # read-only snapshot
            str(self._subvol),
            str(dest),
        ])
        return SnapshotInfo(
            name=name,
            created=datetime.datetime.now(tz=datetime.UTC),
            backend=self.NAME,
            source=str(self._subvol),
            size_bytes=None,  # btrfs doesn't report snapshot size cheaply
        )

    def list(self) -> list[SnapshotInfo]:
        if not self._snap_dir.exists():
            return []
        result = _run(
            ["sudo", "btrfs", "subvolume", "list", "-o", "--sort=-ogen",
             str(self._snap_dir)],
            check=False,
        )
        snaps: list[SnapshotInfo] = []
        for line in result.stdout.splitlines():
            # Line format: "ID NNN gen NNN top level NNN path <path>"
            parts = line.split()
            if not parts:
                continue
            path_part = parts[-1]
            snap_name = Path(path_part).name
            if not snap_name.startswith("waydroid-"):
                continue
            # Parse timestamp from name (waydroid-YYYYMMDD_HHMMSS[-label])
            created = _parse_snap_timestamp(snap_name)
            snaps.append(SnapshotInfo(
                name=snap_name,
                created=created,
                backend=self.NAME,
                source=str(self._subvol),
            ))
        return sorted(snaps, key=lambda s: s.created, reverse=True)

    def restore(self, name: str) -> None:
        """Restore by swapping the live subvolume with the snapshot.

        Steps:
        1. Rename the current live subvolume to a temporary name.
        2. Create a writable snapshot of the read-only snapshot.
        3. Move the writable snapshot into place.
        4. Delete the old live subvolume.
        """
        snap = self._snap_dir / name
        if not snap.exists():
            raise FileNotFoundError(f"Snapshot not found: {snap}")

        live = self._subvol
        old = live.parent / f"{live.name}_old"

        _run(["sudo", "mv", str(live), str(old)])
        _run([
            "sudo", "btrfs", "subvolume", "snapshot",
            str(snap), str(live),   # writable (no -r flag)
        ])
        _run(["sudo", "btrfs", "subvolume", "delete", str(old)])

    def delete(self, name: str) -> None:
        snap = self._snap_dir / name
        _run(["sudo", "btrfs", "subvolume", "delete", str(snap)])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(
    cmd: list[str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"btrfs command failed: {' '.join(cmd)}\n{result.stderr.strip()}"
        )
    return result


def _parse_snap_timestamp(name: str) -> datetime.datetime:
    """Extract the UTC timestamp embedded in a snapshot name."""
    # name format: waydroid-YYYYMMDD_HHMMSS[-optional-label]
    try:
        ts_part = name[len("waydroid-"):].split("-")[0]  # YYYYMMDD_HHMMSS
        return datetime.datetime.strptime(ts_part, "%Y%m%d_%H%M%S").replace(
            tzinfo=datetime.UTC
        )
    except ValueError:
        return datetime.datetime.now(tz=datetime.UTC)
