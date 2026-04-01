"""Smoke tests for the CLI entry point."""

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
