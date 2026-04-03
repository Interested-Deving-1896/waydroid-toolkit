"""Tests for wdt container start/stop/list."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.container import container_start, container_stop, container_list


def _make_run(returncode: int = 0, stdout: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def _patch_backend(ct_name: str = "waydroid") -> list:
    info = MagicMock()
    info.container_name = ct_name
    backend = MagicMock()
    backend.get_info.return_value = info
    return [patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=backend)]


class TestContainerStart:
    def test_start_success(self) -> None:
        runner = CliRunner()
        patches = _patch_backend()
        for p in patches:
            p.start()
        with patch("subprocess.run", return_value=_make_run(0)):
            result = runner.invoke(container_start, [])
        for p in patches:
            p.stop()
        assert result.exit_code == 0
        assert "Started" in result.output

    def test_start_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        patches = _patch_backend()
        for p in patches:
            p.start()
        with patch("subprocess.run", return_value=_make_run(1)):
            result = runner.invoke(container_start, [])
        for p in patches:
            p.stop()
        assert result.exit_code != 0


class TestContainerStop:
    def test_stop_success(self) -> None:
        runner = CliRunner()
        patches = _patch_backend()
        for p in patches:
            p.start()
        with patch("subprocess.run", return_value=_make_run(0)):
            result = runner.invoke(container_stop, [])
        for p in patches:
            p.stop()
        assert result.exit_code == 0
        assert "Stopped" in result.output

    def test_stop_force_flag(self) -> None:
        runner = CliRunner()
        patches = _patch_backend()
        for p in patches:
            p.start()
        calls = []
        def _run(args, **_kw):
            calls.append(args)
            return _make_run(0)
        with patch("subprocess.run", side_effect=_run):
            result = runner.invoke(container_stop, ["--force"])
        for p in patches:
            p.stop()
        assert result.exit_code == 0
        assert "--force" in calls[0]

    def test_stop_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        patches = _patch_backend()
        for p in patches:
            p.start()
        with patch("subprocess.run", return_value=_make_run(1)):
            result = runner.invoke(container_stop, [])
        for p in patches:
            p.stop()
        assert result.exit_code != 0


class TestContainerList:
    def test_empty_when_no_containers(self) -> None:
        runner = CliRunner()
        with patch("subprocess.run", return_value=_make_run(0, "[]")):
            result = runner.invoke(container_list, [])
        assert result.exit_code == 0
        assert "No containers" in result.output

    def test_lists_containers(self) -> None:
        import json
        instances = json.dumps([
            {"name": "waydroid", "type": "container", "status": "Running",
             "state": {"network": {}}},
        ])
        runner = CliRunner()
        with patch("subprocess.run", return_value=_make_run(0, instances)):
            result = runner.invoke(container_list, [])
        assert result.exit_code == 0
        assert "waydroid" in result.output

    def test_filters_vms(self) -> None:
        import json
        instances = json.dumps([
            {"name": "vm1", "type": "virtual-machine", "status": "Running",
             "state": {"network": {}}},
        ])
        runner = CliRunner()
        with patch("subprocess.run", return_value=_make_run(0, instances)):
            result = runner.invoke(container_list, [])
        assert result.exit_code == 0
        assert "No containers" in result.output

    def test_incus_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with patch("subprocess.run", return_value=_make_run(1)):
            result = runner.invoke(container_list, [])
        assert result.exit_code != 0
