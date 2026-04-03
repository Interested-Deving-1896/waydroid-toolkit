"""Tests for wdt host-exec."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.host_exec import cmd


def _make_run(returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    return m


class TestHostExec:
    def test_runs_command_in_container(self) -> None:
        runner = CliRunner()
        calls = []
        def _run(args, **_kw):
            calls.append(args)
            return _make_run(0)
        with patch("waydroid_toolkit.cli.commands.host_exec._container_name",
                   return_value="waydroid"), \
             patch("waydroid_toolkit.cli.commands.host_exec.subprocess.run", side_effect=_run):
            # Use -- to prevent Click treating subsequent args as options
            runner.invoke(cmd, ["--", "ls", "-la"])
        assert len(calls) == 1
        assert "incus" in calls[0]
        assert "exec" in calls[0]
        assert "waydroid" in calls[0]

    def test_custom_container_flag(self) -> None:
        runner = CliRunner()
        calls = []
        def _run(args, **_kw):
            calls.append(args)
            return _make_run(0)
        with patch("waydroid_toolkit.cli.commands.host_exec._container_name",
                   return_value="waydroid"), \
             patch("waydroid_toolkit.cli.commands.host_exec.subprocess.run", side_effect=_run):
            runner.invoke(cmd, ["--container", "myct", "ls"])
        assert "myct" in calls[0]

    def test_no_command_errors(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.exit_code != 0

    def test_exit_code_propagated(self) -> None:
        runner = CliRunner()
        exit_codes: list[int] = []
        real_exit = __import__("sys").exit

        def _capturing_exit(code: int) -> None:
            exit_codes.append(code)
            real_exit(code)

        with patch("waydroid_toolkit.cli.commands.host_exec._container_name",
                   return_value="waydroid"), \
             patch("subprocess.run", return_value=_make_run(42)), \
             patch("waydroid_toolkit.cli.commands.host_exec.sys.exit",
                   side_effect=_capturing_exit):
            runner.invoke(cmd, ["false"])
        assert exit_codes[0] == 42
