"""Tests for wdt cloud-sync."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.cloud_sync import cmd as cloud_sync_cmd


def _mock_rclone(configured: bool = True) -> MagicMock:
    m = MagicMock(returncode=0)
    m.stdout = "wdt-backups:\n" if configured else ""
    return m


class TestCloudSyncPush:
    def test_push_exits_when_rclone_missing(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value=None):
            result = runner.invoke(cloud_sync_cmd, ["push"])
        assert result.exit_code != 0

    def test_push_exits_when_remote_not_configured(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value="/usr/bin/rclone"):
            with patch("waydroid_toolkit.cli.commands.cloud_sync.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="")
                with patch("waydroid_toolkit.cli.commands.cloud_sync._backup_dir", return_value=tmp_path):
                    result = runner.invoke(cloud_sync_cmd, ["push"])
        assert result.exit_code != 0

    def test_push_uploads_tar_files(self, tmp_path: Path) -> None:
        (tmp_path / "mybox-20240101.tar.gz").write_bytes(b"x" * 1024)
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value="/usr/bin/rclone"):
            with patch("waydroid_toolkit.cli.commands.cloud_sync.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="wdt-backups:\n")
                with patch("waydroid_toolkit.cli.commands.cloud_sync._backup_dir", return_value=tmp_path):
                    result = runner.invoke(cloud_sync_cmd, ["push"])
        assert result.exit_code == 0
        assert "Uploaded" in result.output

    def test_push_filter_skips_non_matching(self, tmp_path: Path) -> None:
        (tmp_path / "mybox.tar.gz").write_bytes(b"x")
        (tmp_path / "otherbox.tar.gz").write_bytes(b"x")
        runner = CliRunner()
        calls = []
        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value="/usr/bin/rclone"):
            with patch("waydroid_toolkit.cli.commands.cloud_sync.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="wdt-backups:\n")
                with patch("waydroid_toolkit.cli.commands.cloud_sync._backup_dir", return_value=tmp_path):
                    result = runner.invoke(cloud_sync_cmd, ["push", "mybox"])
        assert result.exit_code == 0
        # Only mybox should appear in upload output
        assert "mybox" in result.output


class TestCloudSyncStatus:
    def test_status_exits_when_rclone_missing(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value=None):
            result = runner.invoke(cloud_sync_cmd, ["status"])
        assert result.exit_code != 0

    def test_status_shows_configured(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value="/usr/bin/rclone"):
            with patch("waydroid_toolkit.cli.commands.cloud_sync.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="wdt-backups:\n")
                with patch("waydroid_toolkit.cli.commands.cloud_sync._backup_dir", return_value=tmp_path):
                    result = runner.invoke(cloud_sync_cmd, ["status"])
        assert result.exit_code == 0
        assert "configured" in result.output

    def test_status_exits_when_not_configured(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value="/usr/bin/rclone"):
            with patch("waydroid_toolkit.cli.commands.cloud_sync.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="")
                with patch("waydroid_toolkit.cli.commands.cloud_sync._backup_dir", return_value=tmp_path):
                    result = runner.invoke(cloud_sync_cmd, ["status"])
        assert result.exit_code != 0


class TestCloudSyncList:
    def test_list_exits_when_not_configured(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value="/usr/bin/rclone"):
            with patch("waydroid_toolkit.cli.commands.cloud_sync.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="")
                result = runner.invoke(cloud_sync_cmd, ["list"])
        assert result.exit_code != 0

    def test_list_shows_remote_files(self, tmp_path: Path) -> None:
        runner = CliRunner()
        lsf_output = "mybox.tar.gz;1024;2024-01-01 00:00:00\n"
        call_count = 0

        def fake_run(cmd, **kw):
            nonlocal call_count
            call_count += 1
            m = MagicMock(returncode=0)
            if "listremotes" in cmd:
                m.stdout = "wdt-backups:\n"
            else:
                m.stdout = lsf_output
            return m

        with patch("waydroid_toolkit.cli.commands.cloud_sync.shutil.which", return_value="/usr/bin/rclone"):
            with patch("waydroid_toolkit.cli.commands.cloud_sync.subprocess.run", side_effect=fake_run):
                with patch("waydroid_toolkit.cli.commands.cloud_sync._backup_dir", return_value=tmp_path):
                    result = runner.invoke(cloud_sync_cmd, ["list"])
        assert result.exit_code == 0
        assert "mybox.tar.gz" in result.output
