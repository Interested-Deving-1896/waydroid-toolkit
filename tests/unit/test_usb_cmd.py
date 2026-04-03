"""Tests for wdt usb (USB passthrough)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.usb import cmd as usb_cmd

_CT = "waydroid"
_PATCH = "waydroid_toolkit.cli.commands.usb"


def _patch_container():
    return patch(f"{_PATCH}._container_name", return_value=_CT)


class TestUsbAttach:
    def test_attach_adds_usb_device(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(usb_cmd, ["attach", "046d", "c52b"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "usb" in args
        assert "vendorid=046d" in args
        assert "productid=c52b" in args

    def test_attach_custom_dev_name(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(usb_cmd, ["attach", "046d", "c52b", "--dev-name", "myusb"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "myusb" in args

    def test_attach_default_dev_name(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                runner.invoke(usb_cmd, ["attach", "046d", "c52b"])
        args = mock_run.call_args[0][0]
        assert "usb-046d-c52b" in args

    def test_attach_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                result = runner.invoke(usb_cmd, ["attach", "046d", "c52b"])
        assert result.exit_code != 0


class TestUsbDetach:
    def test_detach_removes_device(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(usb_cmd, ["detach", "usb-046d-c52b"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "remove" in args
        assert "usb-046d-c52b" in args

    def test_detach_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                result = runner.invoke(usb_cmd, ["detach", "usb-046d-c52b"])
        assert result.exit_code != 0


class TestUsbList:
    def test_list_shows_usb_devices(self) -> None:
        runner = CliRunner()

        def fake_run(cmd, **kw):
            m = MagicMock(returncode=0)
            if "list" in cmd:
                m.stdout = "usb-046d-c52b  usb\n"
            elif "vendorid" in cmd:
                m.stdout = "046d\n"
            else:
                m.stdout = "c52b\n"
            return m

        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run", side_effect=fake_run):
                result = runner.invoke(usb_cmd, ["list"])
        assert result.exit_code == 0
        assert "usb-046d-c52b" in result.output

    def test_list_no_devices_shows_message(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="eth0  nic\n")
                result = runner.invoke(usb_cmd, ["list"])
        assert result.exit_code == 0
        assert "No USB" in result.output


class TestUsbListHost:
    def test_list_host_parses_lsusb(self) -> None:
        runner = CliRunner()
        lsusb_out = "Bus 001 Device 003: ID 046d:c52b Logitech Unifying Receiver\n"
        with patch(f"{_PATCH}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=lsusb_out)
            result = runner.invoke(usb_cmd, ["list-host"])
        assert result.exit_code == 0
        assert "046d:c52b" in result.output

    def test_list_host_no_lsusb_fallback(self) -> None:
        runner = CliRunner()
        with patch(f"{_PATCH}.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            result = runner.invoke(usb_cmd, ["list-host"])
        assert result.exit_code == 0
        assert "lsusb not found" in result.output
