"""Tests for wdt profiles command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli


def _make_profile(name: str, path: Path) -> MagicMock:
    p = MagicMock()
    p.name = name
    p.path = path
    return p


def test_profiles_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["profiles", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "show" in result.output
    assert "switch" in result.output
    assert "active" in result.output
    assert "add" in result.output


def test_profiles_list_empty(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.scan_profiles", return_value=[]), \
         patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "list"])
    assert result.exit_code == 0
    assert "No profiles" in result.output


def test_profiles_list_shows_profiles(tmp_path: Path) -> None:
    p1 = _make_profile("vanilla", tmp_path / "vanilla")
    p1.path.mkdir()
    (p1.path / "system.img").write_bytes(b"x" * 512 * 1024 * 1024)
    (p1.path / "vendor.img").write_bytes(b"x" * 256 * 1024 * 1024)

    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.scan_profiles", return_value=[p1]), \
         patch("waydroid_toolkit.cli.commands.profiles.get_active_profile", return_value=None), \
         patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "list"])
    assert result.exit_code == 0
    assert "vanilla" in result.output


def test_profiles_list_marks_active(tmp_path: Path) -> None:
    p1 = _make_profile("gapps", tmp_path / "gapps")
    p1.path.mkdir()

    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.scan_profiles", return_value=[p1]), \
         patch("waydroid_toolkit.cli.commands.profiles.get_active_profile",
               return_value=str(p1.path)), \
         patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "list"])
    assert result.exit_code == 0
    assert "✓" in result.output


def test_profiles_show_found(tmp_path: Path) -> None:
    p1 = _make_profile("vanilla", tmp_path / "vanilla")
    p1.path.mkdir()
    (p1.path / "system.img").write_bytes(b"x" * 1024 * 1024)

    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.scan_profiles", return_value=[p1]), \
         patch("waydroid_toolkit.cli.commands.profiles.get_active_profile", return_value=None), \
         patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "show", "vanilla"])
    assert result.exit_code == 0
    assert "vanilla" in result.output
    assert "system.img" in result.output


def test_profiles_show_not_found(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.scan_profiles", return_value=[]), \
         patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "show", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_profiles_active_set(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.get_active_profile",
               return_value="/home/user/waydroid-images/vanilla"):
        result = runner.invoke(cli, ["profiles", "active"])
    assert result.exit_code == 0
    assert "vanilla" in result.output


def test_profiles_active_none() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.get_active_profile",
               return_value=None):
        result = runner.invoke(cli, ["profiles", "active"])
    assert result.exit_code != 0
    assert "No active" in result.output


def test_profiles_switch_success(tmp_path: Path) -> None:
    p1 = _make_profile("gapps", tmp_path / "gapps")

    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.scan_profiles", return_value=[p1]), \
         patch("waydroid_toolkit.cli.commands.profiles.switch_profile") as mock_switch, \
         patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "switch", "gapps"])
    assert result.exit_code == 0
    mock_switch.assert_called_once()
    assert "gapps" in result.output


def test_profiles_switch_not_found(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.scan_profiles", return_value=[]), \
         patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "switch", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_profiles_switch_failure(tmp_path: Path) -> None:
    p1 = _make_profile("gapps", tmp_path / "gapps")

    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles.scan_profiles", return_value=[p1]), \
         patch("waydroid_toolkit.cli.commands.profiles.switch_profile",
               side_effect=RuntimeError("permission denied")), \
         patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "switch", "gapps"])
    assert result.exit_code != 0
    assert "failed" in result.output.lower()


def test_profiles_add_creates_symlink(tmp_path: Path) -> None:
    src = tmp_path / "external" / "waydroid-gapps"
    src.mkdir(parents=True)
    (src / "system.img").touch()
    (src / "vendor.img").touch()

    base = tmp_path / "waydroid-images"
    base.mkdir()

    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", base):
        result = runner.invoke(cli, ["profiles", "add", str(src)])
    assert result.exit_code == 0
    assert (base / "waydroid-gapps").is_symlink()
    assert "Registered" in result.output


def test_profiles_add_custom_name(tmp_path: Path) -> None:
    src = tmp_path / "external" / "waydroid-gapps"
    src.mkdir(parents=True)
    (src / "system.img").touch()
    (src / "vendor.img").touch()

    base = tmp_path / "waydroid-images"
    base.mkdir()

    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", base):
        result = runner.invoke(cli, ["profiles", "add", str(src), "--name", "mygapps"])
    assert result.exit_code == 0
    assert (base / "mygapps").is_symlink()


def test_profiles_add_not_a_directory(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", tmp_path):
        result = runner.invoke(cli, ["profiles", "add", str(tmp_path / "nonexistent")])
    assert result.exit_code != 0
    assert "Not a directory" in result.output


def test_profiles_add_already_exists(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    base = tmp_path / "waydroid-images"
    base.mkdir()
    (base / "src").mkdir()  # already exists

    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.profiles._DEFAULT_BASE", base):
        result = runner.invoke(cli, ["profiles", "add", str(src)])
    assert result.exit_code != 0
    assert "already exists" in result.output
