"""Tests for wdt container — snapshot and console CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.container import cmd as container_cmd


def _make_backend(
    snapshot_names: list[str] | None = None,
    raises: type[Exception] | None = None,
) -> MagicMock:
    b = MagicMock()
    if raises is not None:
        b.snapshot_create.side_effect = raises("Incus backend required")
        b.snapshot_list.side_effect = raises("Incus backend required")
        b.snapshot_restore.side_effect = raises("Incus backend required")
        b.snapshot_delete.side_effect = raises("Incus backend required")
        b.console.side_effect = raises("Incus backend required")
    else:
        b.snapshot_list.return_value = snapshot_names or []
    return b


class TestContainerSnapshotCreate:
    def test_create_with_name(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(container_cmd, ["snapshot", "create", "mysnap"])
        assert result.exit_code == 0
        mock_b.snapshot_create.assert_called_once_with("mysnap")
        assert "mysnap" in result.output

    def test_create_without_name_uses_timestamp(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(container_cmd, ["snapshot", "create"])
        assert result.exit_code == 0
        called_name = mock_b.snapshot_create.call_args[0][0]
        assert called_name.startswith("snap-")

    def test_create_lxc_backend_exits_nonzero(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(raises=NotImplementedError)
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(container_cmd, ["snapshot", "create", "s"])
        assert result.exit_code != 0


class TestContainerSnapshotList:
    def test_list_shows_names(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(snapshot_names=["snap1", "snap2"])
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(container_cmd, ["snapshot", "list"])
        assert result.exit_code == 0
        assert "snap1" in result.output
        assert "snap2" in result.output

    def test_list_empty_message(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(snapshot_names=[])
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(container_cmd, ["snapshot", "list"])
        assert result.exit_code == 0
        assert "No snapshots" in result.output

    def test_list_lxc_backend_exits_nonzero(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(raises=NotImplementedError)
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(container_cmd, ["snapshot", "list"])
        assert result.exit_code != 0


class TestContainerSnapshotRestore:
    def test_restore_confirmed(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(
                container_cmd, ["snapshot", "restore", "snap1"], input="y\n"
            )
        assert result.exit_code == 0
        mock_b.snapshot_restore.assert_called_once_with("snap1")

    def test_restore_aborted(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            runner.invoke(
                container_cmd, ["snapshot", "restore", "snap1"], input="n\n"
            )
        mock_b.snapshot_restore.assert_not_called()


class TestContainerSnapshotDelete:
    def test_delete_confirmed(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(
                container_cmd, ["snapshot", "delete", "snap1"], input="y\n"
            )
        assert result.exit_code == 0
        mock_b.snapshot_delete.assert_called_once_with("snap1")

    def test_delete_lxc_backend_exits_nonzero(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(raises=NotImplementedError)
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(
                container_cmd, ["snapshot", "delete", "snap1"], input="y\n"
            )
        assert result.exit_code != 0


class TestContainerConsole:
    def test_console_calls_backend(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend()
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            runner.invoke(container_cmd, ["console"])
        mock_b.console.assert_called_once()

    def test_console_lxc_backend_exits_nonzero(self) -> None:
        runner = CliRunner()
        mock_b = _make_backend(raises=NotImplementedError)
        with patch("waydroid_toolkit.cli.commands.container.get_backend", return_value=mock_b):
            result = runner.invoke(container_cmd, ["console"])
        assert result.exit_code != 0
