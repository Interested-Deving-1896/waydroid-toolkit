"""Tests for wdt backend set (alias for wdt backend switch) — change B."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.backend import cmd as backend_cmd
from waydroid_toolkit.core.container import BackendType


def _mock_backend(available: bool, version: str = "1.0.0", btype: BackendType = BackendType.INCUS) -> MagicMock:
    b = MagicMock()
    b.is_available.return_value = available
    info = MagicMock()
    info.backend_type = btype
    info.version = version
    b.get_info.return_value = info
    return b


class TestBackendSet:
    def test_set_incus_success(self) -> None:
        runner = CliRunner()
        mock_incus = _mock_backend(True, "6.0.0", BackendType.INCUS)

        with patch("waydroid_toolkit.cli.commands.backend.IncusBackend", return_value=mock_incus):
            with patch("waydroid_toolkit.cli.commands.backend.set_active_backend") as mock_set:
                result = runner.invoke(backend_cmd, ["set", "incus"])

        assert result.exit_code == 0
        mock_set.assert_called_once_with(BackendType.INCUS)
        assert "incus" in result.output.lower()

    def test_set_lxc_success(self) -> None:
        runner = CliRunner()
        mock_lxc = _mock_backend(True, "5.0.0", BackendType.LXC)

        with patch("waydroid_toolkit.cli.commands.backend.LxcBackend", return_value=mock_lxc):
            with patch("waydroid_toolkit.cli.commands.backend.set_active_backend") as mock_set:
                result = runner.invoke(backend_cmd, ["set", "lxc"])

        assert result.exit_code == 0
        mock_set.assert_called_once_with(BackendType.LXC)

    def test_set_unavailable_backend_exits_nonzero(self) -> None:
        runner = CliRunner()
        mock_incus = _mock_backend(False)

        with patch("waydroid_toolkit.cli.commands.backend.IncusBackend", return_value=mock_incus):
            with patch("waydroid_toolkit.cli.commands.backend.set_active_backend") as mock_set:
                result = runner.invoke(backend_cmd, ["set", "incus"])

        assert result.exit_code != 0
        mock_set.assert_not_called()

    def test_set_and_switch_are_equivalent(self) -> None:
        """Both 'set' and 'switch' call _do_switch with the same argument."""
        runner = CliRunner()
        mock_incus = _mock_backend(True, "6.0.0", BackendType.INCUS)

        with patch("waydroid_toolkit.cli.commands.backend.IncusBackend", return_value=mock_incus):
            with patch("waydroid_toolkit.cli.commands.backend.set_active_backend") as mock_set:
                r_switch = runner.invoke(backend_cmd, ["switch", "incus"])
                r_set = runner.invoke(backend_cmd, ["set", "incus"])

        assert r_switch.exit_code == r_set.exit_code == 0
        assert mock_set.call_count == 2
        assert mock_set.call_args_list[0] == mock_set.call_args_list[1]

    def test_set_invalid_backend_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(backend_cmd, ["set", "docker"])
        assert result.exit_code != 0

    def test_set_incus_shows_incus_setup_hint(self) -> None:
        runner = CliRunner()
        mock_incus = _mock_backend(True, "6.0.0", BackendType.INCUS)

        with patch("waydroid_toolkit.cli.commands.backend.IncusBackend", return_value=mock_incus):
            with patch("waydroid_toolkit.cli.commands.backend.set_active_backend"):
                result = runner.invoke(backend_cmd, ["set", "incus"])

        assert "incus-setup" in result.output
