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
