"""Tests for wdt container export and import commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.container import cmd as container_cmd
from waydroid_toolkit.core.container import BackendType


def _make_backend(status: str = "stopped") -> MagicMock:
    b = MagicMock()
    info = MagicMock()
    info.container_name = "waydroid"
    info.backend_type = BackendType.INCUS
    info.version = "6.0.0"
    b.get_info.return_value = info
    return b


def _incus_info_json(status: str = "stopped") -> str:
    return json.dumps({"status": status})


class TestContainerExport:
    def test_export_publishes_image(self, tmp_path: Path) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout=_incus_info_json("stopped")
                )
                result = runner.invoke(
                    container_cmd, ["export", "--alias", "waydroid-golden"]
                )
        assert result.exit_code == 0
        # publish call should be present
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("publish" in c for c in calls)

    def test_export_with_output_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        out = str(tmp_path / "waydroid.tar.gz")
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout=_incus_info_json("stopped")
                )
                result = runner.invoke(
                    container_cmd,
                    ["export", "--alias", "waydroid-golden", "--output", out],
                )
        assert result.exit_code == 0
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("export" in c for c in calls)

    def test_export_stops_and_restarts_running_container(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout=_incus_info_json("running")
                )
                result = runner.invoke(
                    container_cmd, ["export", "--alias", "waydroid-golden"]
                )
        assert result.exit_code == 0
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("stop" in c for c in calls)
        assert any("start" in c for c in calls)

    def test_export_container_not_found(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="")
                result = runner.invoke(
                    container_cmd, ["export", "--alias", "waydroid-golden"]
                )
        assert result.exit_code != 0


class TestContainerImport:
    def test_import_from_file(self, tmp_path: Path) -> None:
        archive = tmp_path / "waydroid.tar.gz"
        archive.write_bytes(b"fake")
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(
                    container_cmd,
                    ["import", "--from", str(archive), "--alias", "waydroid-golden"],
                )
        assert result.exit_code == 0
        calls = [str(c) for c in mock_run.call_args_list]
        assert any("import" in c for c in calls)
        assert any("waydroid-golden" in c for c in calls)

    def test_import_without_alias(self, tmp_path: Path) -> None:
        archive = tmp_path / "waydroid.tar.gz"
        archive.write_bytes(b"fake")
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(
                    container_cmd, ["import", "--from", str(archive)]
                )
        assert result.exit_code == 0
