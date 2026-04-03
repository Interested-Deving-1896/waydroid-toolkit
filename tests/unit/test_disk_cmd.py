"""Tests for wdt disk command."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli


def _mock_run(stdout: str = "", returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


def test_disk_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["disk", "--help"])
    assert result.exit_code == 0
    assert "resize" in result.output
    assert "info" in result.output


def test_disk_resize_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["disk", "resize", "--help"])
    assert result.exit_code == 0
    assert "SIZE" in result.output


def test_disk_resize_success() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.disk._run") as mock_run, \
         patch("waydroid_toolkit.cli.commands.disk._container_name",
               return_value="waydroid"), \
         patch("waydroid_toolkit.cli.commands.disk._get_root_size",
               side_effect=["10GB", "20GB"]), \
         patch("waydroid_toolkit.cli.commands.disk._get_pool", return_value="default"):
        mock_run.return_value = _mock_run()
        result = runner.invoke(cli, ["disk", "resize", "20GB"])
    assert result.exit_code == 0
    assert "20GB" in result.output
    assert "resized" in result.output.lower()


def test_disk_resize_invalid_format() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.disk._container_name",
               return_value="waydroid"):
        result = runner.invoke(cli, ["disk", "resize", "20"])
    assert result.exit_code != 0
    assert "Invalid size" in result.output


def test_disk_resize_invalid_format_no_unit() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.disk._container_name",
               return_value="waydroid"):
        result = runner.invoke(cli, ["disk", "resize", "abc"])
    assert result.exit_code != 0


def test_disk_resize_valid_formats() -> None:
    """All valid size formats should pass validation."""
    valid = ["20GB", "+5GB", "100GiB", "+10GiB", "512MB", "1TB"]
    runner = CliRunner()
    for size in valid:
        with patch("waydroid_toolkit.cli.commands.disk._run") as mock_run, \
             patch("waydroid_toolkit.cli.commands.disk._container_name",
                   return_value="waydroid"), \
             patch("waydroid_toolkit.cli.commands.disk._get_root_size",
                   return_value="10GB"), \
             patch("waydroid_toolkit.cli.commands.disk._get_pool", return_value="default"):
            mock_run.return_value = _mock_run()
            result = runner.invoke(cli, ["disk", "resize", size])
        assert result.exit_code == 0, f"Expected success for size={size}, got: {result.output}"


def test_disk_resize_incus_failure() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.disk._run") as mock_run, \
         patch("waydroid_toolkit.cli.commands.disk._container_name",
               return_value="waydroid"), \
         patch("waydroid_toolkit.cli.commands.disk._get_root_size", return_value="10GB"), \
         patch("waydroid_toolkit.cli.commands.disk._get_pool", return_value="default"):
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "incus", stderr="no such device"
        )
        result = runner.invoke(cli, ["disk", "resize", "20GB"])
    assert result.exit_code != 0
    assert "failed" in result.output.lower() or "Resize failed" in result.output


def test_disk_resize_custom_container() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.disk._run") as mock_run, \
         patch("waydroid_toolkit.cli.commands.disk._get_root_size", return_value="10GB"), \
         patch("waydroid_toolkit.cli.commands.disk._get_pool", return_value="default"):
        mock_run.return_value = _mock_run()
        result = runner.invoke(cli, ["disk", "resize", "20GB", "--container", "mywaydroid"])
    assert result.exit_code == 0
    # Verify the custom container name was used in the incus call
    resize_call = [c for c in mock_run.call_args_list
                   if "config" in str(c) and "device" in str(c)]
    assert any("mywaydroid" in str(c) for c in resize_call)


def test_disk_info_stopped_container() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.disk._run") as mock_run, \
         patch("waydroid_toolkit.cli.commands.disk._container_name",
               return_value="waydroid"), \
         patch("waydroid_toolkit.cli.commands.disk._get_root_size", return_value="20GB"), \
         patch("waydroid_toolkit.cli.commands.disk._get_pool", return_value="default"):
        # state check returns STOPPED, pool info returns something
        mock_run.side_effect = [
            _mock_run("space used: 5GB\nspace free: 15GB"),  # storage info
            _mock_run("STOPPED"),                             # list state
        ]
        result = runner.invoke(cli, ["disk", "info"])
    assert result.exit_code == 0
    assert "waydroid" in result.output
    assert "20GB" in result.output


def test_disk_info_running_container() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.disk._run") as mock_run, \
         patch("waydroid_toolkit.cli.commands.disk._container_name",
               return_value="waydroid"), \
         patch("waydroid_toolkit.cli.commands.disk._get_root_size", return_value="20GB"), \
         patch("waydroid_toolkit.cli.commands.disk._get_pool", return_value="default"):
        mock_run.side_effect = [
            _mock_run("space used: 5GB"),   # storage info
            _mock_run("RUNNING"),            # list state
            _mock_run("Filesystem  Size  Used\n/dev/sda1   20G   5G"),  # df
        ]
        result = runner.invoke(cli, ["disk", "info"])
    assert result.exit_code == 0
    assert "20GB" in result.output


def test_disk_info_custom_container() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.disk._run") as mock_run, \
         patch("waydroid_toolkit.cli.commands.disk._get_root_size", return_value="15GB"), \
         patch("waydroid_toolkit.cli.commands.disk._get_pool", return_value="default"):
        mock_run.side_effect = [
            _mock_run(""),       # storage info
            _mock_run("STOPPED"),  # list state
        ]
        result = runner.invoke(cli, ["disk", "info", "--container", "mybox"])
    assert result.exit_code == 0
    assert "mybox" in result.output
