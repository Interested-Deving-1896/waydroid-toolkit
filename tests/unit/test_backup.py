"""Tests for the backup module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.backup.backup import (
    create_backup,
    list_backups,
    restore_backup,
)


def test_list_backups_empty(tmp_path: Path) -> None:
    assert list_backups(tmp_path) == []


def test_list_backups_sorted_newest_first(tmp_path: Path) -> None:
    names = [
        "waydroid_backup_20240101_120000.tar.gz",
        "waydroid_backup_20240301_090000.tar.gz",
        "waydroid_backup_20240201_150000.tar.gz",
    ]
    for name in names:
        (tmp_path / name).touch()

    result = list_backups(tmp_path)
    assert [p.name for p in result] == sorted(names, reverse=True)


def test_list_backups_ignores_non_matching(tmp_path: Path) -> None:
    (tmp_path / "waydroid_backup_20240101_120000.tar.gz").touch()
    (tmp_path / "other_file.tar.gz").touch()
    (tmp_path / "notes.txt").touch()

    result = list_backups(tmp_path)
    assert len(result) == 1
    assert result[0].name == "waydroid_backup_20240101_120000.tar.gz"


def test_list_backups_missing_dir(tmp_path: Path) -> None:
    assert list_backups(tmp_path / "nonexistent") == []


# ── create_backup ─────────────────────────────────────────────────────────────

class TestCreateBackup:
    def _mock_run(self, returncode: int = 0) -> MagicMock:
        return MagicMock(returncode=returncode, stderr="")

    def test_creates_archive_in_dest(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.backup.backup.require_root"):
            with patch("waydroid_toolkit.modules.backup.backup.get_session_state") as mock_state:
                mock_state.return_value = MagicMock(value="stopped")
                with patch("waydroid_toolkit.modules.backup.backup.subprocess.run") as mock_run:
                    mock_run.return_value = self._mock_run()
                    archive = create_backup(dest_dir=tmp_path)
        assert archive.parent == tmp_path
        assert archive.name.startswith("waydroid_backup_")
        assert archive.name.endswith(".tar.gz")

    def test_raises_on_tar_failure(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.backup.backup.require_root"):
            with patch("waydroid_toolkit.modules.backup.backup.get_session_state") as mock_state:
                mock_state.return_value = MagicMock(value="stopped")
                with patch("waydroid_toolkit.modules.backup.backup.subprocess.run") as mock_run:
                    mock_run.return_value = self._mock_run(returncode=1)
                    mock_run.return_value.stderr = "tar: error"
                    with pytest.raises(RuntimeError, match="Backup failed"):
                        create_backup(dest_dir=tmp_path)

    def test_stops_running_session(self, tmp_path: Path) -> None:
        from waydroid_toolkit.core.waydroid import SessionState
        with patch("waydroid_toolkit.modules.backup.backup.require_root"):
            with patch("waydroid_toolkit.modules.backup.backup.get_session_state",
                       return_value=SessionState.RUNNING):
                with patch("waydroid_toolkit.modules.backup.backup.run_waydroid") as mock_wd:
                    with patch("waydroid_toolkit.modules.backup.backup.subprocess.run") as mock_run:
                        mock_run.return_value = self._mock_run()
                        create_backup(dest_dir=tmp_path)
        mock_wd.assert_called_once_with("session", "stop", sudo=True)

    def test_progress_called(self, tmp_path: Path) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.backup.backup.require_root"):
            with patch("waydroid_toolkit.modules.backup.backup.get_session_state") as mock_state:
                mock_state.return_value = MagicMock(value="stopped")
                with patch("waydroid_toolkit.modules.backup.backup.subprocess.run") as mock_run:
                    mock_run.return_value = self._mock_run()
                    create_backup(dest_dir=tmp_path, progress=messages.append)
        assert len(messages) >= 1


# ── restore_backup ────────────────────────────────────────────────────────────

class TestRestoreBackup:
    def test_raises_if_archive_missing(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.backup.backup.require_root"):
            with pytest.raises(FileNotFoundError):
                restore_backup(tmp_path / "nonexistent.tar.gz")

    def test_calls_tar_extract(self, tmp_path: Path) -> None:
        archive = tmp_path / "waydroid_backup_20240101_120000.tar.gz"
        archive.touch()
        with patch("waydroid_toolkit.modules.backup.backup.require_root"):
            with patch("waydroid_toolkit.modules.backup.backup.get_session_state") as mock_state:
                mock_state.return_value = MagicMock(value="stopped")
                with patch("waydroid_toolkit.modules.backup.backup.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stderr="")
                    restore_backup(archive)
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("tar" in c and "-xzf" in c for c in cmds)

    def test_raises_on_tar_failure(self, tmp_path: Path) -> None:
        archive = tmp_path / "waydroid_backup_20240101_120000.tar.gz"
        archive.touch()
        with patch("waydroid_toolkit.modules.backup.backup.require_root"):
            with patch("waydroid_toolkit.modules.backup.backup.get_session_state") as mock_state:
                mock_state.return_value = MagicMock(value="stopped")
                with patch("waydroid_toolkit.modules.backup.backup.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=1, stderr="tar: error")
                    with pytest.raises(RuntimeError, match="Restore failed"):
                        restore_backup(archive)
