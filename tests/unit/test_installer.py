"""Tests for the installer module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.installer.installer import (
    ImageType,
    _stage_images,
    _unstage_images,
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
        (Distro.VOID,     "xbps-install"),
        (Distro.ALPINE,   "apk"),
        (Distro.GENTOO,   "emerge"),
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

    def test_nixos_raises_with_helpful_message(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with pytest.raises(NotImplementedError, match="configuration.nix"):
                install_package(Distro.NIXOS)

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                install_package(Distro.UBUNTU, progress=messages.append)
        assert len(messages) >= 1


# ── init_waydroid ─────────────────────────────────────────────────────────────

_PATCH_BUNDLED = "waydroid_toolkit.modules.installer.bundled_apps.install_bundled_apps"


class TestInitWaydroid:
    def test_calls_waydroid_init(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                with patch(_PATCH_BUNDLED, return_value=[]):
                    mock_run.return_value = MagicMock(returncode=0)
                    init_waydroid()
        cmd = " ".join(mock_run.call_args[0][0])
        assert "waydroid" in cmd
        assert "init" in cmd

    def test_passes_vanilla_image_type(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                with patch(_PATCH_BUNDLED, return_value=[]):
                    mock_run.return_value = MagicMock(returncode=0)
                    init_waydroid(image_type=ImageType.VANILLA)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "VANILLA" in cmd

    def test_passes_gapps_image_type(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                with patch(_PATCH_BUNDLED, return_value=[]):
                    mock_run.return_value = MagicMock(returncode=0)
                    init_waydroid(image_type=ImageType.GAPPS)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "GAPPS" in cmd

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                with patch(_PATCH_BUNDLED, return_value=[]):
                    mock_run.return_value = MagicMock(returncode=0)
                    init_waydroid(progress=messages.append)
        assert len(messages) >= 1

    def test_no_bundled_apps_skips_install(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                with patch(_PATCH_BUNDLED) as mock_bundled:
                    mock_run.return_value = MagicMock(returncode=0)
                    init_waydroid(install_apps=False)
        mock_bundled.assert_not_called()

    def test_bundled_apps_called_by_default(self) -> None:
        with patch("waydroid_toolkit.modules.installer.installer.require_root"):
            with patch("waydroid_toolkit.modules.installer.installer.subprocess.run") as mock_run:
                with patch(_PATCH_BUNDLED, return_value=[]) as mock_bundled:
                    mock_run.return_value = MagicMock(returncode=0)
                    init_waydroid()
        mock_bundled.assert_called_once()


# ── uninstall_waydroid ────────────────────────────────────────────────────────

class TestUninstallWaydroid:
    @pytest.mark.parametrize("distro,expected_pm", [
        (Distro.UBUNTU,   "apt"),
        (Distro.FEDORA,   "dnf"),
        (Distro.ARCH,     "pacman"),
        (Distro.VOID,     "xbps-remove"),
        (Distro.ALPINE,   "apk"),
        (Distro.GENTOO,   "emerge"),
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


# ── _stage_images ─────────────────────────────────────────────────────────────

_PATCH_BUNDLED = "waydroid_toolkit.modules.installer.bundled_apps.install_bundled_apps"
_PATCH_RUN     = "waydroid_toolkit.modules.installer.installer.subprocess.run"
_PATCH_ROOT    = "waydroid_toolkit.modules.installer.installer.require_root"
_PATCH_LINK    = "waydroid_toolkit.modules.installer.installer.os.link"
_PATCH_STAGE   = "waydroid_toolkit.modules.installer.installer._stage_images"
_PATCH_UNSTAGE = "waydroid_toolkit.modules.installer.installer._unstage_images"


class TestStageImages:
    def test_stages_both_images(self, tmp_path: Path) -> None:
        system = tmp_path / "system.img"
        vendor = tmp_path / "vendor.img"
        system.write_bytes(b"system")
        vendor.write_bytes(b"vendor")

        with patch(_PATCH_RUN, return_value=MagicMock(returncode=0)) as mock_run:
            with patch(_PATCH_LINK) as mock_link:
                _stage_images(system, vendor)

        run_cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("mkdir" in c for c in run_cmds)
        assert any("system.img" in c for c in run_cmds)
        assert any("vendor.img" in c for c in run_cmds)
        assert mock_link.call_count == 2

    def test_falls_back_to_copy_on_link_error(self, tmp_path: Path) -> None:
        system = tmp_path / "system.img"
        vendor = tmp_path / "vendor.img"
        system.write_bytes(b"system")
        vendor.write_bytes(b"vendor")

        with patch(_PATCH_RUN, return_value=MagicMock(returncode=0)) as mock_run:
            with patch(_PATCH_LINK, side_effect=OSError("cross-device")):
                _stage_images(system, vendor)

        run_cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("cp" in c for c in run_cmds)

    def test_progress_called_for_each_image(self, tmp_path: Path) -> None:
        system = tmp_path / "system.img"
        vendor = tmp_path / "vendor.img"
        system.write_bytes(b"s")
        vendor.write_bytes(b"v")
        messages: list[str] = []

        with patch(_PATCH_RUN, return_value=MagicMock(returncode=0)):
            with patch(_PATCH_LINK):
                _stage_images(system, vendor, progress=messages.append)

        assert any("system.img" in m for m in messages)
        assert any("vendor.img" in m for m in messages)


class TestUnstageImages:
    def test_removes_staged_files(self) -> None:
        with patch(_PATCH_RUN, return_value=MagicMock(returncode=0)) as mock_run:
            _unstage_images()

        run_cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("system.img" in c for c in run_cmds)
        assert any("vendor.img" in c for c in run_cmds)
        assert any("rmdir" in c for c in run_cmds)

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch(_PATCH_RUN, return_value=MagicMock(returncode=0)):
            _unstage_images(progress=messages.append)
        assert len(messages) >= 1


# ── init_waydroid with custom images ─────────────────────────────────────────

class TestInitWaydroidCustomImages:
    def test_raises_when_only_system_img_given(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="both be provided or both omitted"):
            init_waydroid(system_img=tmp_path / "system.img")

    def test_raises_when_only_vendor_img_given(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="both be provided or both omitted"):
            init_waydroid(vendor_img=tmp_path / "vendor.img")

    def test_stages_and_unstages_on_success(self, tmp_path: Path) -> None:
        system = tmp_path / "system.img"
        vendor = tmp_path / "vendor.img"
        system.write_bytes(b"s")
        vendor.write_bytes(b"v")

        with patch(_PATCH_ROOT):
            with patch(_PATCH_RUN, return_value=MagicMock(returncode=0)):
                with patch(_PATCH_BUNDLED, return_value=[]):
                    with patch(_PATCH_STAGE) as mock_stage:
                        with patch(_PATCH_UNSTAGE) as mock_unstage:
                            init_waydroid(
                                system_img=system,
                                vendor_img=vendor,
                                install_apps=False,
                            )

        mock_stage.assert_called_once_with(system, vendor, None)
        mock_unstage.assert_called_once()

    def test_unstages_even_on_waydroid_init_failure(self, tmp_path: Path) -> None:
        system = tmp_path / "system.img"
        vendor = tmp_path / "vendor.img"
        system.write_bytes(b"s")
        vendor.write_bytes(b"v")

        with patch(_PATCH_ROOT):
            with patch(_PATCH_RUN, side_effect=subprocess.CalledProcessError(1, "waydroid")):
                with patch(_PATCH_STAGE):
                    with patch(_PATCH_UNSTAGE) as mock_unstage:
                        with pytest.raises(subprocess.CalledProcessError):
                            init_waydroid(
                                system_img=system,
                                vendor_img=vendor,
                                install_apps=False,
                            )

        mock_unstage.assert_called_once()

    def test_no_staging_when_no_images_given(self) -> None:
        with patch(_PATCH_ROOT):
            with patch(_PATCH_RUN, return_value=MagicMock(returncode=0)):
                with patch(_PATCH_BUNDLED, return_value=[]):
                    with patch(_PATCH_STAGE) as mock_stage:
                        init_waydroid(install_apps=False)

        mock_stage.assert_not_called()

