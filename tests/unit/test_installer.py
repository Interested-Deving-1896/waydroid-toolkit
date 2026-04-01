"""Tests for the installer module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.installer.installer import (
    ImageType,
    init_waydroid,
    install_package,
    is_waydroid_installed,
    setup_repo,
    uninstall_waydroid,
)
from waydroid_toolkit.utils.distro import Distro

# ── is_waydroid_installed ─────────────────────────────────────────────────────

class TestIsWaydroidInstalled:
    def test_true_when_binary_found(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.shutil.which", return_value="/usr/bin/waydroid"):
            assert is_waydroid_installed() is True

    def test_false_when_binary_missing(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.shutil.which", return_value=None):
            assert is_waydroid_installed() is False


# ── setup_repo ────────────────────────────────────────────────────────────────

class TestSetupRepo:
    def test_runs_repo_script_for_ubuntu(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            setup_repo(Distro.UBUNTU)
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "waydro.id" in cmd

    def test_noop_for_arch(self) -> None:
        # Arch has no repo setup script
        with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
            setup_repo(Distro.ARCH)
        assert not mock_run.called

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            setup_repo(Distro.UBUNTU, progress=messages.append)
        assert len(messages) >= 1


# ── install_package ───────────────────────────────────────────────────────────

class TestInstallPackage:
    @pytest.mark.parametrize("distro,expected_pm", [
        (Distro.UBUNTU,   "apt"),
        (Distro.DEBIAN,   "apt"),
        (Distro.FEDORA,   "dnf"),
        (Distro.ARCH,     "pacman"),
        (Distro.OPENSUSE, "zypper"),
    ])
    def test_uses_correct_package_manager(self, distro: Distro, expected_pm: str) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                install_package(distro)
        cmd = " ".join(mock_run.call_args[0][0])
        assert expected_pm in cmd
        assert "waydroid" in cmd

    def test_raises_for_unknown_distro(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with pytest.raises(NotImplementedError):
                install_package(Distro.UNKNOWN)

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                install_package(Distro.UBUNTU, progress=messages.append)
        assert len(messages) >= 1


# ── init_waydroid ─────────────────────────────────────────────────────────────

class TestInitWaydroid:
    def test_calls_waydroid_init(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                init_waydroid()
        cmd = " ".join(mock_run.call_args[0][0])
        assert "waydroid" in cmd
        assert "init" in cmd

    def test_passes_vanilla_image_type(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                init_waydroid(image_type=ImageType.VANILLA)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "VANILLA" in cmd

    def test_passes_gapps_image_type(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                init_waydroid(image_type=ImageType.GAPPS)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "GAPPS" in cmd

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                init_waydroid(progress=messages.append)
        assert len(messages) >= 1


# ── uninstall_waydroid ────────────────────────────────────────────────────────

class TestUninstallWaydroid:
    @pytest.mark.parametrize("distro,expected_pm", [
        (Distro.UBUNTU,   "apt"),
        (Distro.FEDORA,   "dnf"),
        (Distro.ARCH,     "pacman"),
    ])
    def test_removes_package(self, distro: Distro, expected_pm: str) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                uninstall_waydroid(distro)
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any(expected_pm in c for c in cmds)

    def test_stops_session_before_removal(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                uninstall_waydroid(Distro.UBUNTU)
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("session" in c and "stop" in c for c in cmds)
