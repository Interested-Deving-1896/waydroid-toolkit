"""Tests for wdt tui."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.tui import cmd, _detect_dialog


class TestDetectDialog:
    def test_finds_dialog(self) -> None:
        with patch("shutil.which", side_effect=lambda p: "/usr/bin/dialog" if p == "dialog" else None):
            assert _detect_dialog() == "dialog"

    def test_falls_back_to_whiptail(self) -> None:
        with patch("shutil.which", side_effect=lambda p: "/usr/bin/whiptail" if p == "whiptail" else None):
            assert _detect_dialog() == "whiptail"

    def test_returns_empty_when_neither_found(self) -> None:
        with patch("shutil.which", return_value=None):
            assert _detect_dialog() == ""


class TestTuiCommand:
    def test_no_dialog_exits_nonzero(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.tui._detect_dialog", return_value=""):
            result = runner.invoke(cmd, [])
        assert result.exit_code != 0
        assert "dialog" in result.output.lower() or "whiptail" in result.output.lower()

    def test_keyboard_interrupt_exits_cleanly(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.tui._detect_dialog", return_value="dialog"), \
             patch("waydroid_toolkit.cli.commands.tui._menu", side_effect=KeyboardInterrupt):
            result = runner.invoke(cmd, [])
        assert result.exit_code == 0

    def test_cmd_has_correct_name(self) -> None:
        assert cmd.name == "tui"
