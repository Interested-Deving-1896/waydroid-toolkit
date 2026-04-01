"""Tests for the CLI entry point and subcommands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "WayDroid Toolkit" in result.output


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_subcommand_help_status() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--help"])
    assert result.exit_code == 0


def test_subcommand_help_extensions() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["extensions", "--help"])
    assert result.exit_code == 0
    assert "install" in result.output
    assert "remove" in result.output
    assert "list" in result.output


def test_subcommand_help_backup() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["backup", "--help"])
    assert result.exit_code == 0


def test_subcommand_help_images() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["images", "--help"])
    assert result.exit_code == 0


def test_subcommand_help_packages() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["packages", "--help"])
    assert result.exit_code == 0


def test_subcommand_help_performance() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["performance", "--help"])
    assert result.exit_code == 0


def test_subcommand_help_maintenance() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["maintenance", "--help"])
    assert result.exit_code == 0
    assert "screenshot" in result.output
    assert "logcat" in result.output
    assert "debloat" in result.output


# ── maintenance subcommands ───────────────────────────────────────────────────

def test_maintenance_info_shows_keys() -> None:
    runner = CliRunner()
    info = {"android_version": "13", "sdk_version": "33",
            "product_model": "Waydroid", "cpu_abi": "x86_64"}
    with patch("waydroid_toolkit.cli.commands.maintenance.get_device_info", return_value=info):
        result = runner.invoke(cli, ["maintenance", "info"])
    assert result.exit_code == 0
    assert "android_version" in result.output
    assert "13" in result.output


def test_maintenance_screenshot_default_path(tmp_path: Path) -> None:
    dest = tmp_path / "screenshot_20240101_120000.png"
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.take_screenshot", return_value=dest):
        result = runner.invoke(cli, ["maintenance", "screenshot"])
    assert result.exit_code == 0
    # Rich may wrap long paths across lines — collapse whitespace before checking
    flat = "".join(result.output.split())
    assert "screenshot_20240101_120000.png" in flat


def test_maintenance_set_resolution() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.set_resolution") as mock_res:
        result = runner.invoke(cli, ["maintenance", "set-resolution", "1920", "1080"])
    assert result.exit_code == 0
    mock_res.assert_called_once_with(1920, 1080)
    assert "1920x1080" in result.output


def test_maintenance_set_density() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.set_density") as mock_dpi:
        result = runner.invoke(cli, ["maintenance", "set-density", "240"])
    assert result.exit_code == 0
    mock_dpi.assert_called_once_with(240)


def test_maintenance_reset_display() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.reset_display") as mock_reset:
        result = runner.invoke(cli, ["maintenance", "reset-display"])
    assert result.exit_code == 0
    mock_reset.assert_called_once()


def test_maintenance_freeze() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.freeze_app") as mock_freeze:
        result = runner.invoke(cli, ["maintenance", "freeze", "com.example.app"])
    assert result.exit_code == 0
    mock_freeze.assert_called_once_with("com.example.app")


def test_maintenance_unfreeze() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.unfreeze_app") as mock_unfreeze:
        result = runner.invoke(cli, ["maintenance", "unfreeze", "com.example.app"])
    assert result.exit_code == 0
    mock_unfreeze.assert_called_once_with("com.example.app")


def test_maintenance_clear_data() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.clear_app_data") as mock_clear:
        result = runner.invoke(cli, ["maintenance", "clear-data", "com.example.app"])
    assert result.exit_code == 0
    mock_clear.assert_called_once_with("com.example.app", cache_only=False)


def test_maintenance_clear_data_cache_only() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.clear_app_data") as mock_clear:
        result = runner.invoke(cli, ["maintenance", "clear-data",
                                     "--cache-only", "com.example.app"])
    assert result.exit_code == 0
    mock_clear.assert_called_once_with("com.example.app", cache_only=True)


def test_maintenance_push(tmp_path: Path) -> None:
    src = tmp_path / "file.txt"
    src.write_text("data")
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.push_file") as mock_push:
        result = runner.invoke(cli, ["maintenance", "push", str(src), "/sdcard/file.txt"])
    assert result.exit_code == 0
    mock_push.assert_called_once()


def test_maintenance_pull(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.pull_file") as mock_pull:
        result = runner.invoke(cli, ["maintenance", "pull", "/sdcard/file.txt",
                                     str(tmp_path / "out.txt")])
    assert result.exit_code == 0
    mock_pull.assert_called_once()


def test_maintenance_logcat_streams_lines() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.stream_logcat",
               return_value=iter(["line one", "line two"])):
        result = runner.invoke(cli, ["maintenance", "logcat"])
    assert result.exit_code == 0
    assert "line one" in result.output
    assert "line two" in result.output


def test_maintenance_logcat_errors_flag() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.stream_logcat",
               return_value=iter([])) as mock_logcat:
        runner.invoke(cli, ["maintenance", "logcat", "--errors"])
    mock_logcat.assert_called_once_with(tag=None, errors_only=True)


def test_maintenance_debloat_with_yes_flag() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.debloat",
               return_value=["com.android.email"]) as mock_debloat:
        result = runner.invoke(cli, ["maintenance", "debloat", "--yes",
                                     "-p", "com.android.email"])
    assert result.exit_code == 0
    mock_debloat.assert_called_once()
    assert "1" in result.output


def test_maintenance_debloat_requires_confirmation() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.debloat") as mock_debloat:
        result = runner.invoke(cli, ["maintenance", "debloat", "-p", "com.android.email"],
                               input="n\n")
    assert result.exit_code != 0
    mock_debloat.assert_not_called()


def test_maintenance_launch() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.maintenance.launch_app") as mock_launch:
        result = runner.invoke(cli, ["maintenance", "launch", "com.example.app"])
    assert result.exit_code == 0
    mock_launch.assert_called_once_with("com.example.app")


def test_subcommand_help_backend() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["backend", "--help"])
    assert result.exit_code == 0
    assert "switch" in result.output
    assert "detect" in result.output
    assert "list" in result.output


# ── backup subcommands ────────────────────────────────────────────────────────

def test_backup_list_empty(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["backup", "list", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No backups" in result.output


def test_backup_list_shows_archives(tmp_path: Path) -> None:
    (tmp_path / "waydroid_backup_20240101_120000.tar.gz").write_bytes(b"x" * 1024)
    runner = CliRunner()
    result = runner.invoke(cli, ["backup", "list", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "waydroid_backup_20240101_120000.tar.gz" in result.output


def test_backup_create_invokes_module(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.backup.create_backup") as mock_create:
        mock_create.return_value = tmp_path / "waydroid_backup_20240101_120000.tar.gz"
        result = runner.invoke(cli, ["backup", "create", "--dest", str(tmp_path)])
    assert result.exit_code == 0
    mock_create.assert_called_once()


def test_backup_restore_requires_confirmation(tmp_path: Path) -> None:
    archive = tmp_path / "waydroid_backup_20240101_120000.tar.gz"
    archive.touch()
    runner = CliRunner()
    # Decline confirmation
    result = runner.invoke(cli, ["backup", "restore", str(archive)], input="n\n")
    assert result.exit_code != 0


def test_backup_restore_with_yes_flag(tmp_path: Path) -> None:
    archive = tmp_path / "waydroid_backup_20240101_120000.tar.gz"
    archive.touch()
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.backup.restore_backup") as mock_restore:
        result = runner.invoke(cli, ["backup", "restore", "--yes", str(archive)])
    assert result.exit_code == 0
    mock_restore.assert_called_once()


# ── packages subcommands ──────────────────────────────────────────────────────

def test_packages_list_empty() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.packages.get_installed_packages", return_value=[]):
        result = runner.invoke(cli, ["packages", "list"])
    assert result.exit_code == 0
    assert "No third-party" in result.output


def test_packages_list_shows_packages() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.packages.get_installed_packages",
               return_value=["com.example.app", "org.fdroid.fdroid"]):
        result = runner.invoke(cli, ["packages", "list"])
    assert result.exit_code == 0
    assert "com.example.app" in result.output


def test_packages_install_local_file(tmp_path: Path) -> None:
    apk = tmp_path / "app.apk"
    apk.write_bytes(b"PK")
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.packages.install_apk_file") as mock_install:
        result = runner.invoke(cli, ["packages", "install", str(apk)])
    assert result.exit_code == 0
    mock_install.assert_called_once()


def test_packages_install_url() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.packages.install_apk_url") as mock_install:
        result = runner.invoke(cli, ["packages", "install", "https://example.com/app.apk"])
    assert result.exit_code == 0
    mock_install.assert_called_once()


def test_packages_search_no_results() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.packages.search_repos", return_value=[]):
        result = runner.invoke(cli, ["packages", "search", "zzznomatch"])
    assert result.exit_code == 0
    assert "No results" in result.output


def test_packages_repo_list_empty() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.packages.list_repos", return_value=[]):
        result = runner.invoke(cli, ["packages", "repo", "list"])
    assert result.exit_code == 0
    assert "No repos" in result.output


# ── backend subcommands ───────────────────────────────────────────────────────

def test_backend_list_shows_backends() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["backend", "list"])
    assert result.exit_code == 0
    # Both backend names should appear
    assert "lxc" in result.output.lower() or "incus" in result.output.lower()


def test_backend_detect_output() -> None:
    runner = CliRunner()
    # detect is imported as detect_backend from waydroid_toolkit.core.container
    with patch("waydroid_toolkit.cli.commands.backend.detect_backend") as mock_detect:
        mock_backend = MagicMock()
        mock_backend.backend_type.value = "lxc"
        mock_detect.return_value = mock_backend
        result = runner.invoke(cli, ["backend", "detect"])
    assert result.exit_code == 0
