"""Tests for wdt doctor — change C."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from waydroid_toolkit.cli.commands.doctor import cmd as doctor_cmd
from waydroid_toolkit.core.container import BackendType


def _make_backend_info(btype: BackendType = BackendType.INCUS, version: str = "6.0.0") -> MagicMock:
    info = MagicMock()
    info.backend_type = btype
    info.version = version
    return info


def _make_backend(btype: BackendType = BackendType.INCUS, version: str = "6.0.0") -> MagicMock:
    b = MagicMock()
    b.get_info.return_value = _make_backend_info(btype, version)
    return b


def _patch_all(
    *,
    waydroid_bin: str | None = "/usr/bin/waydroid",
    waydroid_init: bool = True,
    backend: MagicMock | None = None,
    incus_bin: str | None = "/usr/bin/incus",
    incus_container_ok: bool = True,
    modules: dict[str, bool] | None = None,
    devices: dict[str, bool] | None = None,
    adb_bin: str | None = "/usr/bin/adb",
    adb_connected: bool = True,
    audio: tuple[str, str] = ("pipewire", "/run/user/1000/pipewire-0"),
):
    """Return a context-manager stack that patches all external calls in doctor."""
    if backend is None:
        backend = _make_backend()
    if modules is None:
        modules = {"binder_linux": True, "ashmem_linux": True}
    if devices is None:
        devices = {
            "/dev/binder": True,
            "/dev/ashmem": True,
            "/dev/dri/renderD128": True,
            "/dev/dma_heap/system": True,
            "/dev/dma_heap/system-uncached": True,
        }

    def _which(cmd: str) -> str | None:
        return {
            "waydroid": waydroid_bin,
            "incus": incus_bin,
            "adb": adb_bin,
        }.get(cmd)

    def _module_loaded(name: str) -> bool:
        return modules.get(name, False)

    def _device_exists(path: str) -> bool:
        return devices.get(path, False)

    incus_run = MagicMock()
    incus_run.returncode = 0 if incus_container_ok else 1

    patches = [
        patch("waydroid_toolkit.cli.commands.doctor.shutil.which", side_effect=_which),
        patch("waydroid_toolkit.cli.commands.doctor._module_loaded", side_effect=_module_loaded),
        patch("waydroid_toolkit.cli.commands.doctor._device_exists", side_effect=_device_exists),
        patch("waydroid_toolkit.cli.commands.doctor._audio_socket", return_value=audio),
        patch("waydroid_toolkit.core.waydroid.is_initialized", return_value=waydroid_init),
        patch("waydroid_toolkit.cli.commands.doctor.subprocess.run", return_value=incus_run),
        patch("waydroid_toolkit.core.container.get_active", return_value=backend),
    ]
    if adb_bin:
        patches.append(
            patch("waydroid_toolkit.core.adb.is_connected", return_value=adb_connected)
        )
    return patches


class TestDoctorCommand:
    def _run(self, extra_args: list[str] | None = None, **kwargs) -> tuple[object, list]:
        runner = CliRunner()
        patches = _patch_all(**kwargs)
        ctx_managers = [p.start() for p in patches]
        try:
            result = runner.invoke(doctor_cmd, extra_args or [])
        finally:
            for p in patches:
                p.stop()
        return result, ctx_managers

    def test_all_ok_exits_zero(self) -> None:
        result, _ = self._run()
        assert result.exit_code == 0

    def test_missing_waydroid_exits_nonzero(self) -> None:
        result, _ = self._run(waydroid_bin=None)
        assert result.exit_code != 0

    def test_missing_incus_binary_exits_nonzero(self) -> None:
        result, _ = self._run(incus_bin=None)
        assert result.exit_code != 0

    def test_missing_binder_module_exits_nonzero(self) -> None:
        result, _ = self._run(modules={"binder_linux": False, "ashmem_linux": True})
        assert result.exit_code != 0

    def test_missing_binder_device_exits_nonzero(self) -> None:
        result, _ = self._run(devices={
            "/dev/binder": False,
            "/dev/ashmem": True,
            "/dev/dri/renderD128": True,
            "/dev/dma_heap/system": True,
            "/dev/dma_heap/system-uncached": True,
        })
        assert result.exit_code != 0

    def test_lxc_backend_with_incus_available_shows_warning(self) -> None:
        lxc_backend = _make_backend(BackendType.LXC, "5.0.0")
        result, _ = self._run(backend=lxc_backend)
        assert result.exit_code == 0  # warning, not failure
        assert "warn" in result.output.lower() or "lxc" in result.output.lower()

    def test_no_audio_socket_is_warning_not_failure(self) -> None:
        result, _ = self._run(audio=("none", ""))
        # Missing audio is a warning, not a hard failure — exit 0
        assert result.exit_code == 0

    def test_json_output_is_valid(self) -> None:
        result, _ = self._run(extra_args=["--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert all("check" in row and "status" in row for row in data)

    def test_json_output_contains_expected_checks(self) -> None:
        result, _ = self._run(extra_args=["--json"])
        data = json.loads(result.output)
        check_names = [row["check"] for row in data]
        assert any("waydroid" in c for c in check_names)
        assert any("backend" in c for c in check_names)
        assert any("binder" in c for c in check_names)
        assert any("adb" in c for c in check_names)

    def test_incus_container_missing_exits_nonzero(self) -> None:
        result, _ = self._run(incus_container_ok=False)
        assert result.exit_code != 0

    def test_fix_hints_present_on_failure(self) -> None:
        result, _ = self._run(waydroid_bin=None, extra_args=["--json"])
        data = json.loads(result.output)
        waydroid_row = next(r for r in data if r["check"] == "waydroid binary")
        assert "wdt install" in waydroid_row["fix"]


class TestInstallBackendOption:
    """Tests for --backend flag on wdt install (change A)."""

    def test_install_defaults_to_incus(self) -> None:
        from waydroid_toolkit.cli.commands.install import cmd as install_cmd

        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.install.detect_distro") as mock_distro, \
             patch("waydroid_toolkit.cli.commands.install.Installer") as mock_installer_cls, \
             patch("waydroid_toolkit.cli.commands.install.IncusBackend") as mock_incus_cls, \
             patch("waydroid_toolkit.cli.commands.install.set_active_backend") as mock_set, \
             patch("waydroid_toolkit.cli.commands.install.LxcBackend"):
            from waydroid_toolkit.utils.distro import Distro
            mock_distro.return_value = Distro.UBUNTU
            mock_installer = MagicMock()
            mock_installer_cls.return_value = mock_installer
            mock_incus = MagicMock()
            mock_incus.is_available.return_value = True
            mock_incus_cls.return_value = mock_incus
            mock_incus.get_info.return_value = _make_backend_info()

            result = runner.invoke(install_cmd, [])

        mock_set.assert_called_once_with(BackendType.INCUS)
        assert result.exit_code == 0

    def test_install_lxc_backend_flag(self) -> None:
        from waydroid_toolkit.cli.commands.install import cmd as install_cmd

        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.install.detect_distro") as mock_distro, \
             patch("waydroid_toolkit.cli.commands.install.Installer") as mock_installer_cls, \
             patch("waydroid_toolkit.cli.commands.install.LxcBackend") as mock_lxc_cls, \
             patch("waydroid_toolkit.cli.commands.install.set_active_backend") as mock_set, \
             patch("waydroid_toolkit.cli.commands.install.IncusBackend"):
            from waydroid_toolkit.utils.distro import Distro
            mock_distro.return_value = Distro.UBUNTU
            mock_installer = MagicMock()
            mock_installer_cls.return_value = mock_installer
            mock_lxc = MagicMock()
            mock_lxc.is_available.return_value = True
            mock_lxc_cls.return_value = mock_lxc
            mock_lxc.get_info.return_value = _make_backend_info(BackendType.LXC)

            result = runner.invoke(install_cmd, ["--backend", "lxc"])

        mock_set.assert_called_once_with(BackendType.LXC)
        assert result.exit_code == 0

    def test_install_warns_when_backend_unavailable(self) -> None:
        from waydroid_toolkit.cli.commands.install import cmd as install_cmd

        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.install.detect_distro") as mock_distro, \
             patch("waydroid_toolkit.cli.commands.install.Installer") as mock_installer_cls, \
             patch("waydroid_toolkit.cli.commands.install.IncusBackend") as mock_incus_cls, \
             patch("waydroid_toolkit.cli.commands.install.set_active_backend") as mock_set, \
             patch("waydroid_toolkit.cli.commands.install.LxcBackend"):
            from waydroid_toolkit.utils.distro import Distro
            mock_distro.return_value = Distro.UBUNTU
            mock_installer = MagicMock()
            mock_installer_cls.return_value = mock_installer
            mock_incus = MagicMock()
            mock_incus.is_available.return_value = False
            mock_incus_cls.return_value = mock_incus

            result = runner.invoke(install_cmd, ["--backend", "incus"])

        mock_set.assert_not_called()
        assert "Warning" in result.output or "warning" in result.output.lower()
