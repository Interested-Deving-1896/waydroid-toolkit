"""Tests for wdt upgrade command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli


def _make_update_info(available: bool) -> MagicMock:
    info = MagicMock()
    info.update_available = available
    info.current_datetime = "2024-01-01"
    info.latest = MagicMock()
    info.latest.datetime = "2024-06-01"
    info.channel = "system"
    return info


def test_upgrade_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["upgrade", "--help"])
    assert result.exit_code == 0
    assert "check" in result.output
    assert "apply" in result.output


def test_upgrade_check_up_to_date() -> None:
    runner = CliRunner()
    sys_info = _make_update_info(False)
    sys_info.channel = "system"
    ven_info = _make_update_info(False)
    ven_info.channel = "vendor"
    with patch("waydroid_toolkit.cli.commands.upgrade.check_updates",
               return_value=(sys_info, ven_info)):
        result = runner.invoke(cli, ["upgrade", "check"])
    assert result.exit_code == 0
    assert "up to date" in result.output


def test_upgrade_check_update_available() -> None:
    runner = CliRunner()
    sys_info = _make_update_info(True)
    sys_info.channel = "system"
    ven_info = _make_update_info(False)
    ven_info.channel = "vendor"
    with patch("waydroid_toolkit.cli.commands.upgrade.check_updates",
               return_value=(sys_info, ven_info)):
        result = runner.invoke(cli, ["upgrade", "check"])
    assert result.exit_code == 0
    assert "update available" in result.output
    assert "wdt upgrade apply" in result.output


def test_upgrade_check_network_error() -> None:
    import urllib.error
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.upgrade.check_updates",
               side_effect=urllib.error.URLError("timeout")):
        result = runner.invoke(cli, ["upgrade", "check"])
    assert result.exit_code != 0
    assert "Network error" in result.output


def test_upgrade_apply_already_up_to_date() -> None:
    runner = CliRunner()
    sys_info = _make_update_info(False)
    ven_info = _make_update_info(False)
    with patch("waydroid_toolkit.cli.commands.upgrade.check_updates",
               return_value=(sys_info, ven_info)):
        result = runner.invoke(cli, ["upgrade", "apply", "--yes"])
    assert result.exit_code == 0
    assert "up to date" in result.output


def test_upgrade_apply_downloads_and_applies() -> None:
    from pathlib import Path
    runner = CliRunner()
    sys_info = _make_update_info(True)
    ven_info = _make_update_info(True)

    with patch("waydroid_toolkit.cli.commands.upgrade.check_updates",
               return_value=(sys_info, ven_info)), \
         patch("waydroid_toolkit.cli.commands.upgrade._waydroid_running",
               return_value=False), \
         patch("waydroid_toolkit.cli.commands.upgrade.download_updates",
               return_value=(Path("/tmp/system.img"), Path("/tmp/vendor.img"))), \
         patch("waydroid_toolkit.cli.commands.upgrade.subprocess.run",
               return_value=MagicMock(returncode=0)), \
         patch("waydroid_toolkit.cli.commands.upgrade.scan_profiles", return_value=[]), \
         patch("waydroid_toolkit.cli.commands.upgrade.switch_profile"):
        result = runner.invoke(cli, ["upgrade", "apply", "--yes", "--no-snapshot"])
    assert result.exit_code == 0
    assert "Upgrade complete" in result.output


def test_upgrade_apply_requires_confirmation() -> None:
    runner = CliRunner()
    sys_info = _make_update_info(True)
    ven_info = _make_update_info(True)
    with patch("waydroid_toolkit.cli.commands.upgrade.check_updates",
               return_value=(sys_info, ven_info)), \
         patch("waydroid_toolkit.cli.commands.upgrade._waydroid_running",
               return_value=False):
        result = runner.invoke(cli, ["upgrade", "apply"], input="n\n")
    assert result.exit_code != 0


def test_upgrade_apply_stops_running_waydroid() -> None:
    from pathlib import Path
    runner = CliRunner()
    sys_info = _make_update_info(True)
    ven_info = _make_update_info(True)

    with patch("waydroid_toolkit.cli.commands.upgrade.check_updates",
               return_value=(sys_info, ven_info)), \
         patch("waydroid_toolkit.cli.commands.upgrade._waydroid_running",
               return_value=True), \
         patch("waydroid_toolkit.cli.commands.upgrade.run_waydroid") as mock_wd, \
         patch("waydroid_toolkit.cli.commands.upgrade.download_updates",
               return_value=(Path("/tmp/system.img"), None)), \
         patch("waydroid_toolkit.cli.commands.upgrade.subprocess.run",
               return_value=MagicMock(returncode=0)), \
         patch("waydroid_toolkit.cli.commands.upgrade.scan_profiles", return_value=[]):
        result = runner.invoke(cli, ["upgrade", "apply", "--yes", "--no-snapshot",
                                     "--no-restart"])
    assert result.exit_code == 0
    # session stop should have been called
    stop_calls = [c for c in mock_wd.call_args_list if "stop" in str(c)]
    assert len(stop_calls) >= 1


def test_upgrade_no_subcommand_runs_check() -> None:
    """wdt upgrade with no subcommand should run check."""
    runner = CliRunner()
    sys_info = _make_update_info(False)
    sys_info.channel = "system"
    ven_info = _make_update_info(False)
    ven_info.channel = "vendor"
    with patch("waydroid_toolkit.cli.commands.upgrade.check_updates",
               return_value=(sys_info, ven_info)):
        result = runner.invoke(cli, ["upgrade"])
    assert result.exit_code == 0
    assert "up to date" in result.output
