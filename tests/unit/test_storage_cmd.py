"""Unit tests for wdt storage CLI commands."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli
from waydroid_toolkit.modules.storage.nfs import NfsMount

_ADD = "waydroid_toolkit.cli.commands.storage.add_nfs_mount"
_REMOVE = "waydroid_toolkit.cli.commands.storage.remove_nfs_mount"
_LIST = "waydroid_toolkit.cli.commands.storage.list_nfs_mounts"


class TestStorageNfsAdd:
    def test_add_basic(self):
        runner = CliRunner()
        with patch(_ADD) as mock_add:
            mock_add.return_value = NfsMount(
                device_name="nfs-192-168-1-10--exports",
                source="192.168.1.10:/exports",
                container_path="/data/shared",
                mount_type="nfs",
                options="soft,async",
            )
            result = runner.invoke(cli, ["storage", "nfs", "add", "192.168.1.10:/exports"])

        assert result.exit_code == 0
        assert "Mounted" in result.output
        assert "nfs-192-168-1-10--exports" in result.output

    def test_add_invalid_type_exits_1(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["storage", "nfs", "add", "host:/path", "--type", "smb"]
        )
        assert result.exit_code != 0

    def test_add_subprocess_error_exits_1(self):
        import subprocess
        runner = CliRunner()
        with patch(_ADD, side_effect=subprocess.CalledProcessError(1, "incus")):
            result = runner.invoke(cli, ["storage", "nfs", "add", "host:/path"])
        assert result.exit_code == 1
        assert "incus command failed" in result.output


class TestStorageNfsList:
    def test_list_empty(self):
        runner = CliRunner()
        with patch(_LIST, return_value=[]):
            result = runner.invoke(cli, ["storage", "nfs", "list"])
        assert result.exit_code == 0
        assert "No disk devices" in result.output

    def test_list_with_mounts(self):
        runner = CliRunner()
        with patch(_LIST, return_value=[
            NfsMount(
                device_name="nfs-share",
                source="192.168.1.10:/exports",
                container_path="/data/shared",
                mount_type="disk",
                options="soft,async",
            )
        ]):
            result = runner.invoke(cli, ["storage", "nfs", "list"])
        assert result.exit_code == 0
        assert "nfs-share" in result.output
        assert "192.168.1.10:/exports" in result.output


class TestStorageNfsRemove:
    def test_remove_confirmed(self):
        runner = CliRunner()
        with patch(_REMOVE) as mock_rm:
            result = runner.invoke(
                cli, ["storage", "nfs", "remove", "nfs-share"], input="y\n"
            )
        assert result.exit_code == 0
        mock_rm.assert_called_once_with("nfs-share")
        assert "Removed" in result.output

    def test_remove_aborted(self):
        runner = CliRunner()
        with patch(_REMOVE) as mock_rm:
            runner.invoke(cli, ["storage", "nfs", "remove", "nfs-share"], input="n\n")
            mock_rm.assert_not_called()
