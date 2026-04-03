"""Tests for wdt shell command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli


def test_shell_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["shell", "--help"])
    assert result.exit_code == 0
    assert "enter" in result.output
    assert "root" in result.output
    assert "exec" in result.output


def test_shell_enter_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["shell", "enter", "--help"])
    assert result.exit_code == 0
    assert "--user" in result.output
    assert "--shell" in result.output


def test_shell_exec_runs_command() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.shell.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell", "exec", "--", "waydroid", "status"])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "incus" in args
    assert "exec" in args
    assert "waydroid" in args
    assert "status" in args


def test_shell_exec_with_user() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.shell.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell", "exec", "--user", "1000", "--", "id"])
    assert result.exit_code == 0
    args = mock_run.call_args[0][0]
    assert "--user" in args
    assert "1000" in args


def test_shell_exec_propagates_exit_code() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.shell.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=42)
        result = runner.invoke(cli, ["shell", "exec", "--", "false"])
    assert result.exit_code == 42


def test_shell_root_uses_execvp() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.shell.os.execvp") as mock_exec:
        mock_exec.side_effect = SystemExit(0)
        result = runner.invoke(cli, ["shell", "root"])
    mock_exec.assert_called_once()
    args = mock_exec.call_args[0]
    assert args[0] == "incus"
    assert "exec" in args[1]
    assert "/bin/bash" in args[1]


def test_shell_enter_uses_execvp() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.shell.os.execvp") as mock_exec:
        mock_exec.side_effect = SystemExit(0)
        result = runner.invoke(cli, ["shell", "enter"])
    mock_exec.assert_called_once()
    args = mock_exec.call_args[0]
    assert args[0] == "incus"
    assert "/bin/bash" in args[1]
