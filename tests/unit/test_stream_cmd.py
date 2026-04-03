"""Unit tests for wdt stream CLI commands."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli


class TestStreamCheck:
    def test_all_present(self):
        runner = CliRunner()
        with patch(
            "waydroid_toolkit.modules.streaming.stream.check_dependencies",
            return_value={"adb": True, "scrcpy": True, "ws-scrcpy": False},
        ):
            result = runner.invoke(cli, ["stream", "check"])
        # ws-scrcpy missing → exit 1, but adb+scrcpy present shown
        assert "adb" in result.output
        assert "scrcpy" in result.output

    def test_missing_deps_exits_1(self):
        runner = CliRunner()
        with patch(
            "waydroid_toolkit.modules.streaming.stream.check_dependencies",
            return_value={"adb": False, "scrcpy": False, "ws-scrcpy": False},
        ):
            result = runner.invoke(cli, ["stream", "check"])
        assert result.exit_code == 1
        assert "sudo apt install" in result.output


class TestStreamStatus:
    def test_no_pid_file(self, tmp_path):
        runner = CliRunner()
        with patch(
            "waydroid_toolkit.cli.commands.stream._PID_FILE",
            tmp_path / "stream.pid",
        ):
            result = runner.invoke(cli, ["stream", "status"])
        assert result.exit_code == 0
        assert "No stream session" in result.output

    def test_running_pid(self, tmp_path):
        pid_file = tmp_path / "stream.pid"
        pid_file.write_text(str(os.getpid()))
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.stream._PID_FILE", pid_file):
            result = runner.invoke(cli, ["stream", "status"])
        assert result.exit_code == 0
        assert "running" in result.output.lower()

    def test_dead_pid_cleans_up(self, tmp_path):
        pid_file = tmp_path / "stream.pid"
        pid_file.write_text("999999999")
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.stream._PID_FILE", pid_file):
            result = runner.invoke(cli, ["stream", "status"])
        assert result.exit_code == 0
        assert not pid_file.exists()


class TestStreamStop:
    def test_stop_running_session(self, tmp_path):
        pid_file = tmp_path / "stream.pid"
        pid_file.write_text("12345")
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.stream._PID_FILE", pid_file):
            with patch("os.kill") as mock_kill:
                result = runner.invoke(cli, ["stream", "stop"])
        assert result.exit_code == 0
        assert "stopped" in result.output.lower()
        assert not pid_file.exists()

    def test_stop_no_session(self, tmp_path):
        runner = CliRunner()
        with patch(
            "waydroid_toolkit.cli.commands.stream._PID_FILE",
            tmp_path / "stream.pid",
        ):
            result = runner.invoke(cli, ["stream", "stop"])
        assert result.exit_code == 0
        assert "No stream session" in result.output


class TestStreamStart:
    def test_start_success(self, tmp_path):
        pid_file = tmp_path / "stream.pid"
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.stream._PID_FILE", pid_file):
            with patch(
                "waydroid_toolkit.modules.streaming.stream.start_stream"
            ) as mock_start:
                from waydroid_toolkit.modules.streaming.stream import StreamConfig, StreamSession
                mock_start.return_value = StreamSession(
                    config=StreamConfig(), pid=9999, adb_serial="192.168.240.112:5555"
                )
                result = runner.invoke(cli, ["stream", "start"])
        assert result.exit_code == 0
        assert "9999" in result.output

    def test_start_missing_scrcpy_exits_1(self, tmp_path):
        pid_file = tmp_path / "stream.pid"
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.stream._PID_FILE", pid_file):
            with patch(
                "waydroid_toolkit.modules.streaming.stream.start_stream",
                side_effect=FileNotFoundError("scrcpy not found"),
            ):
                result = runner.invoke(cli, ["stream", "start"])
        assert result.exit_code == 1
        assert "Missing dependency" in result.output

    def test_start_already_running_exits_1(self, tmp_path):
        pid_file = tmp_path / "stream.pid"
        pid_file.write_text(str(os.getpid()))  # current process = "running"
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.stream._PID_FILE", pid_file):
            result = runner.invoke(cli, ["stream", "start"])
        assert result.exit_code == 1
        assert "already running" in result.output
