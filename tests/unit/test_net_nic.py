"""Tests for wdt net nic add/remove/list."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.net import nic_add, nic_remove, nic_list


def _make_run(returncode: int = 0, stdout: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


class TestNicAdd:
    def test_add_success(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.net._container_name", return_value="waydroid"), \
             patch("subprocess.run", return_value=_make_run(0)):
            result = runner.invoke(nic_add, ["eth1"])
        assert result.exit_code == 0
        assert "added" in result.output.lower()

    def test_add_custom_network(self) -> None:
        runner = CliRunner()
        calls = []
        def _run(args, **_kw):
            calls.append(args)
            return _make_run(0)
        with patch("waydroid_toolkit.cli.commands.net._container_name", return_value="waydroid"), \
             patch("subprocess.run", side_effect=_run):
            result = runner.invoke(nic_add, ["eth1", "--network", "mybr0"])
        assert result.exit_code == 0
        assert any("parent=mybr0" in a for a in calls[0])

    def test_add_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.net._container_name", return_value="waydroid"), \
             patch("subprocess.run", return_value=_make_run(1)):
            result = runner.invoke(nic_add, ["eth1"])
        assert result.exit_code != 0


class TestNicRemove:
    def test_remove_success(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.net._container_name", return_value="waydroid"), \
             patch("subprocess.run", return_value=_make_run(0)):
            result = runner.invoke(nic_remove, ["eth1"])
        assert result.exit_code == 0
        assert "removed" in result.output.lower()

    def test_remove_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.net._container_name", return_value="waydroid"), \
             patch("subprocess.run", return_value=_make_run(1)):
            result = runner.invoke(nic_remove, ["eth1"])
        assert result.exit_code != 0


class TestNicList:
    def test_no_nics(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.net._container_name", return_value="waydroid"), \
             patch("subprocess.run", return_value=_make_run(0, "")):
            result = runner.invoke(nic_list, [])
        assert result.exit_code == 0
        assert "No NIC" in result.output

    def test_lists_nics(self) -> None:
        runner = CliRunner()
        device_list = "eth1  nic\n"

        def _run(args, **_kw):
            if "list" in args:
                return _make_run(0, device_list)
            return _make_run(0, "bridged")

        with patch("waydroid_toolkit.cli.commands.net._container_name", return_value="waydroid"), \
             patch("subprocess.run", side_effect=_run):
            result = runner.invoke(nic_list, [])
        assert result.exit_code == 0
        assert "eth1" in result.output
