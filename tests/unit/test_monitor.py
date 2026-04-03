"""Tests for wdt monitor."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.monitor import cmd as monitor_cmd
from waydroid_toolkit.core.container import BackendType, ContainerState


def _make_backend(state: ContainerState = ContainerState.RUNNING) -> MagicMock:
    b = MagicMock()
    b.get_state.return_value = state
    info = MagicMock()
    info.container_name = "waydroid"
    info.backend_type = BackendType.INCUS
    info.version = "6.0.0"
    b.get_info.return_value = info
    return b


def _incus_info_json(status: str = "running") -> str:
    return json.dumps({
        "status": status,
        "state": {
            "memory": {"usage": 512 * 1024 * 1024, "usage_peak": 768 * 1024 * 1024},
            "cpu": {"usage": 5_000_000_000},
            "network": {
                "eth0": {"counters": {"bytes_received": 10 * 1024 * 1024, "bytes_sent": 2 * 1024 * 1024}},
            },
            "disk": {
                "root": {"usage": 2048 * 1024 * 1024},
            },
        },
    })


class TestMonitorStatus:
    def test_shows_running_state(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(ContainerState.RUNNING)
        with patch("waydroid_toolkit.cli.commands.monitor.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=_incus_info_json())
                result = runner.invoke(monitor_cmd, ["status"])
        assert result.exit_code == 0
        assert "waydroid" in result.output
        assert "running" in result.output

    def test_shows_stopped_state(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(ContainerState.STOPPED)
        with patch("waydroid_toolkit.cli.commands.monitor.get_backend", return_value=mock_b):
            result = runner.invoke(monitor_cmd, ["status"])
        assert result.exit_code == 0
        assert "stopped" in result.output


class TestMonitorStats:
    def test_stats_requires_running(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(ContainerState.STOPPED)
        with patch("waydroid_toolkit.cli.commands.monitor.get_backend", return_value=mock_b):
            result = runner.invoke(monitor_cmd, ["stats"])
        assert result.exit_code != 0

    def test_stats_shows_memory(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(ContainerState.RUNNING)
        with patch("waydroid_toolkit.cli.commands.monitor.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=_incus_info_json())
                result = runner.invoke(monitor_cmd, ["stats"])
        assert result.exit_code == 0
        assert "Memory" in result.output
        assert "MiB" in result.output

    def test_stats_shows_network(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(ContainerState.RUNNING)
        with patch("waydroid_toolkit.cli.commands.monitor.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=_incus_info_json())
                result = runner.invoke(monitor_cmd, ["stats"])
        assert result.exit_code == 0
        assert "eth0" in result.output


class TestMonitorTop:
    def test_top_shows_table(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(ContainerState.RUNNING)
        with patch("waydroid_toolkit.cli.commands.monitor.get_backend", return_value=mock_b):
            result = runner.invoke(monitor_cmd, ["top"])
        assert result.exit_code == 0
        assert "waydroid" in result.output
        assert "running" in result.output
