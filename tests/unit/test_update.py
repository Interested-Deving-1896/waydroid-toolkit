"""Tests for wdt update."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.update import _version_gt, cmd as update_cmd


class TestVersionGt:
    def test_newer_patch(self) -> None:
        assert _version_gt("0.2.1", "0.2.0") is True

    def test_newer_minor(self) -> None:
        assert _version_gt("0.3.0", "0.2.9") is True

    def test_newer_major(self) -> None:
        assert _version_gt("1.0.0", "0.9.9") is True

    def test_equal_is_not_gt(self) -> None:
        assert _version_gt("1.0.0", "1.0.0") is False

    def test_older_is_not_gt(self) -> None:
        assert _version_gt("0.1.0", "0.2.0") is False

    def test_strips_v_prefix(self) -> None:
        assert _version_gt("v1.1.0", "v1.0.0") is True


class TestUpdateCheck:
    def test_up_to_date(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.update._current_version", return_value="1.0.0"):
            with patch("waydroid_toolkit.cli.commands.update._fetch_release",
                       return_value={"tag_name": "v1.0.0", "body": ""}):
                result = runner.invoke(update_cmd, ["check"])
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_update_available(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.update._current_version", return_value="0.1.0"):
            with patch("waydroid_toolkit.cli.commands.update._fetch_release",
                       return_value={"tag_name": "v0.2.0", "body": "Bug fixes"}):
                result = runner.invoke(update_cmd, ["check"])
        assert result.exit_code == 0
        assert "Update available" in result.output
        assert "0.2.0" in result.output

    def test_network_error_handled(self) -> None:
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.update._current_version", return_value="0.1.0"):
            with patch("waydroid_toolkit.cli.commands.update._fetch_release",
                       side_effect=Exception("timeout")):
                result = runner.invoke(update_cmd, ["check"])
        assert result.exit_code == 0
        assert "Could not reach" in result.output
