"""Tests for wdt publish command."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.main import cli


def _mock_run(stdout: str = "", returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


def test_publish_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--help"])
    assert result.exit_code == 0
    assert "create" in result.output
    assert "list" in result.output
    assert "delete" in result.output


def test_publish_create_stopped_container() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.publish.subprocess.run") as mock_run:
        # list call returns STOPPED, then publish succeeds
        mock_run.side_effect = [
            _mock_run("waydroid,STOPPED"),
            _mock_run(),
        ]
        result = runner.invoke(cli, ["publish", "create", "--alias", "waydroid/test"])
    assert result.exit_code == 0
    assert "Published" in result.output


def test_publish_create_running_without_force_stop_fails() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.publish.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run("waydroid,RUNNING")
        result = runner.invoke(cli, ["publish", "create"])
    assert result.exit_code != 0
    assert "running" in result.output.lower() or "RUNNING" in result.output


def test_publish_create_force_stop() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.publish.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_run("waydroid,RUNNING"),  # list
            _mock_run(),                     # stop
            _mock_run(),                     # publish
        ]
        result = runner.invoke(cli, ["publish", "create", "--force-stop"])
    assert result.exit_code == 0
    calls = mock_run.call_args_list
    assert any("stop" in str(c) for c in calls)


def test_publish_list_no_images() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.publish.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run("[]")
        result = runner.invoke(cli, ["publish", "list"])
    assert result.exit_code == 0
    assert "No published" in result.output


def test_publish_list_shows_waydroid_images() -> None:
    images = [
        {
            "aliases": [{"name": "waydroid/v1"}],
            "fingerprint": "abc123def456",
            "size": 512 * 1024 * 1024,
            "created_at": "2024-03-01T00:00:00Z",
            "properties": {"description": "waydroid image"},
        }
    ]
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.publish.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run(json.dumps(images))
        result = runner.invoke(cli, ["publish", "list"])
    assert result.exit_code == 0
    assert "waydroid/v1" in result.output


def test_publish_delete_confirmed() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.publish.subprocess.run") as mock_run:
        mock_run.return_value = _mock_run()
        result = runner.invoke(cli, ["publish", "delete", "waydroid/v1"], input="y\n")
    assert result.exit_code == 0
    assert "Deleted" in result.output


def test_publish_delete_aborted() -> None:
    runner = CliRunner()
    with patch("waydroid_toolkit.cli.commands.publish.subprocess.run") as mock_run:
        result = runner.invoke(cli, ["publish", "delete", "waydroid/v1"], input="n\n")
    assert result.exit_code != 0
    mock_run.assert_not_called()
