"""Tests for wdt net (port forwarding)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.net import cmd as net_cmd

_CT = "waydroid"


def _patch_container(name: str = _CT):
    return patch("waydroid_toolkit.cli.commands.net._container_name", return_value=name)


class TestNetForward:
    def test_forward_adds_proxy_device(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch("waydroid_toolkit.cli.commands.net.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(net_cmd, ["forward", "8080"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "proxy" in args
        assert "listen=tcp:0.0.0.0:8080" in args
        assert "connect=tcp:127.0.0.1:8080" in args

    def test_forward_different_container_port(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch("waydroid_toolkit.cli.commands.net.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(net_cmd, ["forward", "8080", "80"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "connect=tcp:127.0.0.1:80" in args

    def test_forward_udp_proto(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch("waydroid_toolkit.cli.commands.net.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(net_cmd, ["forward", "5353", "--proto", "udp"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "listen=udp:0.0.0.0:5353" in args

    def test_forward_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch("waydroid_toolkit.cli.commands.net.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                result = runner.invoke(net_cmd, ["forward", "8080"])
        assert result.exit_code != 0


class TestNetUnforward:
    def test_unforward_removes_device(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch("waydroid_toolkit.cli.commands.net.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(net_cmd, ["unforward", "fwd-8080"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "remove" in args
        assert "fwd-8080" in args

    def test_unforward_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch("waydroid_toolkit.cli.commands.net.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                result = runner.invoke(net_cmd, ["unforward", "fwd-8080"])
        assert result.exit_code != 0


class TestNetList:
    def test_list_shows_proxy_devices(self) -> None:
        runner = CliRunner()

        def fake_run(cmd, **kw):
            m = MagicMock(returncode=0)
            if "list" in cmd:
                m.stdout = "fwd-8080  proxy\n"
            elif "listen" in cmd:
                m.stdout = "tcp:0.0.0.0:8080\n"
            else:
                m.stdout = "tcp:127.0.0.1:8080\n"
            return m

        with _patch_container():
            with patch("waydroid_toolkit.cli.commands.net.subprocess.run", side_effect=fake_run):
                result = runner.invoke(net_cmd, ["list"])
        assert result.exit_code == 0
        assert "fwd-8080" in result.output

    def test_list_no_proxies_shows_message(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch("waydroid_toolkit.cli.commands.net.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="eth0  nic\n")
                result = runner.invoke(net_cmd, ["list"])
        assert result.exit_code == 0
        assert "No port forwards" in result.output
