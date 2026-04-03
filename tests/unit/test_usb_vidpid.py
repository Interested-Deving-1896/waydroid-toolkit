"""Tests for wdt usb attach VID:PID shorthand."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.usb import usb_attach


def _make_run(returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    return m


class TestUsbAttachShorthand:
    def test_vidpid_shorthand_accepted(self) -> None:
        runner = CliRunner()
        calls = []
        def _run(args, **_kw):
            calls.append(args)
            return _make_run(0)
        with patch("waydroid_toolkit.cli.commands.usb._container_name", return_value="waydroid"), \
             patch("subprocess.run", side_effect=_run):
            result = runner.invoke(usb_attach, ["046d:c52b"])
        assert result.exit_code == 0
        assert any("vendorid=046d" in a for a in calls[0])
        assert any("productid=c52b" in a for a in calls[0])

    def test_two_arg_form_still_works(self) -> None:
        runner = CliRunner()
        calls = []
        def _run(args, **_kw):
            calls.append(args)
            return _make_run(0)
        with patch("waydroid_toolkit.cli.commands.usb._container_name", return_value="waydroid"), \
             patch("subprocess.run", side_effect=_run):
            result = runner.invoke(usb_attach, ["046d", "c52b"])
        assert result.exit_code == 0
        assert any("vendorid=046d" in a for a in calls[0])
        assert any("productid=c52b" in a for a in calls[0])

    def test_missing_product_id_errors(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.usb._container_name", return_value="waydroid"):
            result = runner.invoke(usb_attach, ["046d"])
        assert result.exit_code != 0

    def test_custom_dev_name(self) -> None:
        runner = CliRunner()
        calls = []
        def _run(args, **_kw):
            calls.append(args)
            return _make_run(0)
        with patch("waydroid_toolkit.cli.commands.usb._container_name", return_value="waydroid"), \
             patch("subprocess.run", side_effect=_run):
            result = runner.invoke(usb_attach, ["046d:c52b", "--dev-name", "myusb"])
        assert result.exit_code == 0
        assert "myusb" in calls[0]
