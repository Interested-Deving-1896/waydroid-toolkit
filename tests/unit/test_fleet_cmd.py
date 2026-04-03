"""Tests for wdt fleet command."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli

_INSTANCES = [
    {"name": "waydroid", "type": "container", "status": "Running",
     "state": {"network": {"eth0": {"addresses": [
         {"family": "inet", "address": "10.0.0.2"}
     ]}}}},
    {"name": "waydroid2", "type": "container", "status": "Stopped",
     "state": {"network": {}}},
]


def _mock_run(stdout: str = "", returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


def test_fleet_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["fleet", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "start-all" in result.output
    assert "stop-all" in result.output


def test_fleet_list_shows_instances() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(json.dumps(_INSTANCES))
        result = runner.invoke(cli, ["fleet", "list"])
    assert result.exit_code == 0
    assert "waydroid" in result.output
    assert "waydroid2" in result.output


def test_fleet_list_empty() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run("[]")
        result = runner.invoke(cli, ["fleet", "list"])
    assert result.exit_code == 0
    assert "No instances" in result.output


def test_fleet_start_all_starts_stopped() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_run(json.dumps(_INSTANCES)),  # list call
            _mock_run(),                         # start waydroid2
        ]
        result = runner.invoke(cli, ["fleet", "start-all"])
    assert result.exit_code == 0
    # Only the stopped instance should be started
    calls = mock_run.call_args_list
    start_calls = [c for c in calls if "start" in str(c)]
    assert any("waydroid2" in str(c) for c in start_calls)


def test_fleet_start_all_none_stopped() -> None:
    running_only = [_INSTANCES[0]]
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(json.dumps(running_only))
        result = runner.invoke(cli, ["fleet", "start-all"])
    assert result.exit_code == 0
    assert "No stopped" in result.output


def test_fleet_stop_all_stops_running() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_run(json.dumps(_INSTANCES)),  # list call
            _mock_run(),                         # stop waydroid
        ]
        result = runner.invoke(cli, ["fleet", "stop-all"])
    assert result.exit_code == 0
    calls = mock_run.call_args_list
    stop_calls = [c for c in calls if "stop" in str(c)]
    assert any("waydroid" in str(c) for c in stop_calls)


def test_fleet_stop_all_force_flag() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_run(json.dumps(_INSTANCES)),
            _mock_run(),
        ]
        result = runner.invoke(cli, ["fleet", "stop-all", "--force"])
    assert result.exit_code == 0
    calls = mock_run.call_args_list
    assert any("--force" in str(c) for c in calls)


def test_fleet_status_shows_summary() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(json.dumps(_INSTANCES))
        result = runner.invoke(cli, ["fleet", "status"])
    assert result.exit_code == 0
    assert "Running" in result.output or "Stopped" in result.output


def test_fleet_exec_runs_in_running_instances() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_run(json.dumps(_INSTANCES)),   # list call
            _mock_run("ok\n"),                    # exec in waydroid
        ]
        result = runner.invoke(cli, ["fleet", "exec", "--", "waydroid", "status"])
    assert result.exit_code == 0
    calls = mock_run.call_args_list
    exec_calls = [c for c in calls if "exec" in str(c)]
    assert any("waydroid" in str(c) for c in exec_calls)


def test_fleet_exec_no_running() -> None:
    stopped_only = [_INSTANCES[1]]
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.fleet.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(json.dumps(stopped_only))
        result = runner.invoke(cli, ["fleet", "exec", "--", "echo", "hi"])
    assert result.exit_code == 0
    assert "No running" in result.output
