"""Tests for wdt config command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli


def _patch_config(tmp_path: Path):
    """Patch config file location to a temp directory."""
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_file = cfg_dir / "config.yaml"
    return (
        patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir),
        patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file),
    )


def test_config_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "show" in result.output
    assert "edit" in result.output
    assert "init" in result.output
    assert "path" in result.output
    assert "get" in result.output
    assert "set" in result.output


def test_config_init_creates_file(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_file = cfg_dir / "config.yaml"
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        result = runner.invoke(cli, ["config", "init"])
    assert result.exit_code == 0
    assert cfg_file.exists()
    assert "backend" in cfg_file.read_text()


def test_config_init_no_overwrite_without_force(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "config.yaml"
    cfg_file.write_text("existing: true\n")
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        result = runner.invoke(cli, ["config", "init"])
    assert result.exit_code == 0
    assert "existing: true" in cfg_file.read_text()


def test_config_init_force_overwrites(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "config.yaml"
    cfg_file.write_text("existing: true\n")
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        result = runner.invoke(cli, ["config", "init", "--force"])
    assert result.exit_code == 0
    assert "existing: true" not in cfg_file.read_text()


def test_config_show_no_file(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_file = cfg_dir / "config.yaml"
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "No config" in result.output


def test_config_show_existing_file(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "config.yaml"
    cfg_file.write_text("backend: incus\nlog_level: debug\n")
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "backend" in result.output


def test_config_path_output(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_file = cfg_dir / "config.yaml"
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        result = runner.invoke(cli, ["config", "path"])
    assert result.exit_code == 0
    # Rich may wrap long paths — collapse whitespace before checking
    flat = "".join(result.output.split())
    assert "config.yaml" in flat


def test_config_set_and_get(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_file = cfg_dir / "config.yaml"
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        set_result = runner.invoke(cli, ["config", "set", "backend", "incus"])
        assert set_result.exit_code == 0
        get_result = runner.invoke(cli, ["config", "get", "backend"])
    assert get_result.exit_code == 0
    assert "incus" in get_result.output


def test_config_get_missing_key(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "config.yaml"
    cfg_file.write_text("backend: incus\n")
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        result = runner.invoke(cli, ["config", "get", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "Key not found" in result.output


def test_config_get_no_file(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "waydroid-toolkit"
    cfg_file = cfg_dir / "config.yaml"
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.config._CONFIG_DIR", cfg_dir), \
         patch("waydroid_toolkit.cli.commands.config._CONFIG_FILE", cfg_file):
        result = runner.invoke(cli, ["config", "get", "backend"])
    assert result.exit_code != 0


def test_config_backup_delete_confirmed(tmp_path: Path) -> None:
    """Verify backup delete command works (wired through backup, not config)."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    archive = backup_dir / "waydroid_backup_20240101_120000.tar.gz"
    archive.write_bytes(b"data")
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.backup.DEFAULT_BACKUP_DIR", backup_dir):
        result = runner.invoke(
            cli, ["backup", "delete", "waydroid_backup_20240101_120000.tar.gz"],
            input="y\n",
        )
    assert result.exit_code == 0
    assert not archive.exists()
    assert "Deleted" in result.output


def test_config_backup_delete_not_found(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.backup.DEFAULT_BACKUP_DIR", tmp_path):
        result = runner.invoke(
            cli, ["backup", "delete", "nonexistent.tar.gz"],
            input="y\n",
        )
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "not found" in result.output
