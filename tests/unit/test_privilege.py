"""Tests for the privilege / sudo helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.core.privilege import is_root, require_root, sudo_run

# ── is_root ───────────────────────────────────────────────────────────────────

class TestIsRoot:
    def test_true_when_euid_zero(self) -> None:
        with patch("waydroid_toolkit.core.privilege.os.geteuid", return_value=0):
            assert is_root() is True

    def test_false_when_euid_nonzero(self) -> None:
        with patch("waydroid_toolkit.core.privilege.os.geteuid", return_value=1000):
            assert is_root() is False


# ── sudo_run ──────────────────────────────────────────────────────────────────

class TestSudoRun:
    def test_prepends_sudo(self) -> None:
        with patch("waydroid_toolkit.core.privilege.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            sudo_run("ls", "-la")
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "sudo"
        assert "ls" in cmd
        assert "-la" in cmd

    def test_raises_permission_error_when_sudo_missing(self) -> None:
        with patch("waydroid_toolkit.core.privilege.subprocess.run",
                   side_effect=FileNotFoundError):
            with pytest.raises(PermissionError, match="sudo is not available"):
                sudo_run("ls")

    def test_returns_completed_process(self) -> None:
        with patch("waydroid_toolkit.core.privilege.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output")
            result = sudo_run("true")
        assert result.returncode == 0


# ── require_root ──────────────────────────────────────────────────────────────

class TestRequireRoot:
    def test_passes_silently_when_already_root(self) -> None:
        with patch("waydroid_toolkit.core.privilege.is_root", return_value=True):
            require_root("test op")  # should not raise

    def test_passes_when_sudo_available_without_password(self) -> None:
        with patch("waydroid_toolkit.core.privilege.is_root", return_value=False):
            with patch("waydroid_toolkit.core.privilege.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                require_root("test op")  # should not raise

    def test_raises_when_not_root_and_sudo_requires_password(self) -> None:
        with patch("waydroid_toolkit.core.privilege.is_root", return_value=False):
            with patch("waydroid_toolkit.core.privilege.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                with pytest.raises(PermissionError, match="requires root"):
                    require_root("installing Waydroid")

    def test_error_message_includes_operation_name(self) -> None:
        with patch("waydroid_toolkit.core.privilege.is_root", return_value=False):
            with patch("waydroid_toolkit.core.privilege.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                with pytest.raises(PermissionError, match="my special operation"):
                    require_root("my special operation")

    def test_sudo_check_uses_noninteractive_flag(self) -> None:
        with patch("waydroid_toolkit.core.privilege.is_root", return_value=False):
            with patch("waydroid_toolkit.core.privilege.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                require_root()
        cmd = " ".join(mock_run.call_args[0][0])
        assert "sudo" in cmd
        assert "-n" in cmd
