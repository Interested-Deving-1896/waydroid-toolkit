"""Tests for waydroid_toolkit.modules.snapshot."""

from __future__ import annotations

import datetime
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.snapshot.backends import SnapshotInfo
from waydroid_toolkit.modules.snapshot.btrfs import BtrfsBackend, _parse_snap_timestamp
from waydroid_toolkit.modules.snapshot.detector import detect_backend, get_backend
from waydroid_toolkit.modules.snapshot.zfs import ZfsBackend, _parse_zfs_size

# ── ZfsBackend ────────────────────────────────────────────────────────────────

class TestZfsBackend:
    def _backend(self, dataset: str = "rpool/waydroid") -> ZfsBackend:
        return ZfsBackend(dataset=dataset)

    def test_is_available_true_when_zfs_list_succeeds(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert self._backend().is_available() is True

    def test_is_available_false_when_zfs_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert self._backend().is_available() is False

    def test_is_available_false_when_dataset_missing(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert self._backend().is_available() is False

    def test_is_available_false_on_timeout(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("zfs", 5)):
            assert self._backend().is_available() is False

    def test_create_runs_zfs_snapshot(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            self._backend().create("test-label")
        # First call is the snapshot, second is the size query
        first_cmd = mock_run.call_args_list[0][0][0]
        assert "snapshot" in first_cmd
        assert any("waydroid-" in arg for arg in first_cmd)

    def test_create_returns_snapshot_info(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            info = self._backend().create("mylabel")
        assert isinstance(info, SnapshotInfo)
        assert info.backend == "zfs"
        assert info.source == "rpool/waydroid"
        assert "mylabel" in info.name
        assert info.name.startswith("waydroid-")

    def test_create_raises_on_failure(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="dataset busy")
            with pytest.raises(RuntimeError, match="ZFS command failed"):
                self._backend().create()

    def test_list_parses_output(self) -> None:
        output = (
            "rpool/waydroid@waydroid-20240101_120000\tMon Jan  1 12:00 2024\t1.5G\n"
            "rpool/waydroid@waydroid-20240102_080000\tTue Jan  2 08:00 2024\t2G\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            snaps = self._backend().list()
        assert len(snaps) == 2
        # Newest first
        assert snaps[0].name == "waydroid-20240102_080000"
        assert snaps[1].name == "waydroid-20240101_120000"

    def test_list_ignores_non_waydroid_snapshots(self) -> None:
        output = (
            "rpool/waydroid@manual-snap\tMon Jan  1 12:00 2024\t100M\n"
            "rpool/waydroid@waydroid-20240101_120000\tMon Jan  1 12:00 2024\t1G\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            snaps = self._backend().list()
        assert len(snaps) == 1
        assert snaps[0].name == "waydroid-20240101_120000"

    def test_list_returns_empty_on_no_output(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            assert self._backend().list() == []

    def test_restore_calls_rollback(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            self._backend().restore("waydroid-20240101_120000")
        cmd = mock_run.call_args[0][0]
        assert "rollback" in cmd
        assert "rpool/waydroid@waydroid-20240101_120000" in cmd

    def test_restore_raises_on_failure(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="no such snapshot")
            with pytest.raises(RuntimeError, match="ZFS command failed"):
                self._backend().restore("nonexistent")

    def test_delete_calls_destroy(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            self._backend().delete("waydroid-20240101_120000")
        cmd = mock_run.call_args[0][0]
        assert "destroy" in cmd
        assert "rpool/waydroid@waydroid-20240101_120000" in cmd

    def test_delete_raises_on_failure(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="busy")
            with pytest.raises(RuntimeError):
                self._backend().delete("waydroid-20240101_120000")


class TestParseZfsSize:
    def test_gigabytes(self) -> None:
        assert _parse_zfs_size("2G") == 2 * 1024**3

    def test_megabytes(self) -> None:
        assert _parse_zfs_size("512M") == 512 * 1024**2

    def test_kilobytes(self) -> None:
        assert _parse_zfs_size("100K") == 100 * 1024

    def test_terabytes(self) -> None:
        assert _parse_zfs_size("1T") == 1024**4

    def test_plain_integer(self) -> None:
        assert _parse_zfs_size("1024") == 1024

    def test_dash_returns_none(self) -> None:
        assert _parse_zfs_size("-") is None

    def test_empty_returns_none(self) -> None:
        assert _parse_zfs_size("") is None

    def test_fractional(self) -> None:
        result = _parse_zfs_size("1.5G")
        assert result == int(1.5 * 1024**3)


# ── BtrfsBackend ──────────────────────────────────────────────────────────────

class TestBtrfsBackend:
    def _backend(self, tmp_path: Path) -> BtrfsBackend:
        subvol = tmp_path / "waydroid"
        subvol.mkdir()
        snap_dir = tmp_path / "waydroid_snapshots"
        return BtrfsBackend(subvol=subvol, snap_dir=snap_dir)

    def test_is_available_true_when_btrfs_show_succeeds(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert b.is_available() is True

    def test_is_available_false_when_btrfs_not_found(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert b.is_available() is False

    def test_is_available_false_on_timeout(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("btrfs", 5)):
            assert b.is_available() is False

    def test_create_runs_snapshot_command(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            b.create("my-label")
        # Find the snapshot call (not the mkdir)
        snap_calls = [
            c for c in mock_run.call_args_list
            if "snapshot" in c[0][0]
        ]
        assert snap_calls
        cmd = snap_calls[0][0][0]
        assert "-r" in cmd  # read-only

    def test_create_returns_snapshot_info(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            info = b.create("label")
        assert isinstance(info, SnapshotInfo)
        assert info.backend == "btrfs"
        assert "label" in info.name
        assert info.name.startswith("waydroid-")

    def test_create_raises_on_failure(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not a subvolume")
            with pytest.raises(RuntimeError, match="btrfs command failed"):
                b.create()

    def test_list_returns_empty_when_snap_dir_missing(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        # snap_dir doesn't exist yet
        assert b.list() == []

    def test_list_parses_subvolume_output(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        b._snap_dir.mkdir(parents=True)
        output = (
            "ID 256 gen 10 top level 5 path waydroid-20240101_120000\n"
            "ID 257 gen 11 top level 5 path waydroid-20240102_080000\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            snaps = b.list()
        assert len(snaps) == 2
        names = {s.name for s in snaps}
        assert "waydroid-20240101_120000" in names
        assert "waydroid-20240102_080000" in names

    def test_list_ignores_non_waydroid_subvolumes(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        b._snap_dir.mkdir(parents=True)
        output = (
            "ID 256 gen 10 top level 5 path manual-backup\n"
            "ID 257 gen 11 top level 5 path waydroid-20240101_120000\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output, stderr="")
            snaps = b.list()
        assert len(snaps) == 1

    def test_restore_swaps_subvolumes(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        snap_name = "waydroid-20240101_120000"
        b._snap_dir.mkdir(parents=True)
        (b._snap_dir / snap_name).mkdir()

        calls_made: list[list[str]] = []
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            mock_run.side_effect = lambda cmd, **kw: (
                calls_made.append(cmd) or MagicMock(returncode=0, stdout="", stderr="")
            )
            b.restore(snap_name)

        all_cmds = " ".join(" ".join(c) for c in calls_made)
        assert "mv" in all_cmds
        assert "snapshot" in all_cmds
        assert "delete" in all_cmds

    def test_restore_raises_when_snapshot_missing(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        with pytest.raises(FileNotFoundError):
            b.restore("nonexistent-snap")

    def test_delete_calls_subvolume_delete(self, tmp_path: Path) -> None:
        b = self._backend(tmp_path)
        b._snap_dir.mkdir(parents=True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            b.delete("waydroid-20240101_120000")
        cmd = mock_run.call_args[0][0]
        assert "delete" in cmd
        assert "waydroid-20240101_120000" in " ".join(cmd)


class TestParseSnapTimestamp:
    def test_parses_standard_name(self) -> None:
        dt = _parse_snap_timestamp("waydroid-20240115_143000")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 14
        assert dt.minute == 30

    def test_parses_name_with_label(self) -> None:
        dt = _parse_snap_timestamp("waydroid-20240115_143000-before-gapps")
        assert dt.year == 2024
        assert dt.month == 1

    def test_invalid_name_returns_now(self) -> None:
        before = datetime.datetime.now(tz=datetime.UTC)
        dt = _parse_snap_timestamp("waydroid-badformat")
        after = datetime.datetime.now(tz=datetime.UTC)
        assert before <= dt <= after


# ── detector ─────────────────────────────────────────────────────────────────

class TestDetector:
    def test_detect_returns_zfs_when_available(self) -> None:
        with patch.object(ZfsBackend, "is_available", return_value=True):
            backend = detect_backend()
        assert isinstance(backend, ZfsBackend)

    def test_detect_returns_btrfs_when_zfs_unavailable(self) -> None:
        with patch.object(ZfsBackend, "is_available", return_value=False):
            with patch.object(BtrfsBackend, "is_available", return_value=True):
                backend = detect_backend()
        assert isinstance(backend, BtrfsBackend)

    def test_detect_returns_none_when_neither_available(self) -> None:
        with patch.object(ZfsBackend, "is_available", return_value=False):
            with patch.object(BtrfsBackend, "is_available", return_value=False):
                assert detect_backend() is None

    def test_get_backend_raises_when_none_available(self) -> None:
        with patch.object(ZfsBackend, "is_available", return_value=False):
            with patch.object(BtrfsBackend, "is_available", return_value=False):
                with pytest.raises(RuntimeError, match="No snapshot backend"):
                    get_backend()

    def test_get_backend_returns_zfs_first(self) -> None:
        with patch.object(ZfsBackend, "is_available", return_value=True):
            backend = get_backend()
        assert isinstance(backend, ZfsBackend)


# ── SnapshotInfo dataclass ────────────────────────────────────────────────────

class TestSnapshotInfo:
    def test_fields(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        info = SnapshotInfo(
            name="waydroid-20240101_120000",
            created=now,
            backend="zfs",
            source="rpool/waydroid",
            size_bytes=1024,
        )
        assert info.name == "waydroid-20240101_120000"
        assert info.backend == "zfs"
        assert info.size_bytes == 1024

    def test_size_bytes_optional(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        info = SnapshotInfo(
            name="snap",
            created=now,
            backend="btrfs",
            source="/var/lib/waydroid",
        )
        assert info.size_bytes is None
