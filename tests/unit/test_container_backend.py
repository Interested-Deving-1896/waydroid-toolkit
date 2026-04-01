"""Tests for the container backend abstraction."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.core.container import BackendType, ContainerState
from waydroid_toolkit.core.container.incus_backend import (
    ANDROID_ENV,
    IncusBackend,
    SessionConfig,
    _glob_char_devices,
    _static_char_devices,
    _static_disk_mounts,
)
from waydroid_toolkit.core.container.lxc_backend import LxcBackend
from waydroid_toolkit.core.container.selector import detect, get_active, set_active

# ── ANDROID_ENV ───────────────────────────────────────────────────────────────


class TestAndroidEnv:
    def test_path_contains_system_bin(self) -> None:
        assert "/system/bin" in ANDROID_ENV["PATH"]

    def test_android_root_set(self) -> None:
        assert ANDROID_ENV["ANDROID_ROOT"] == "/system"

    def test_android_data_set(self) -> None:
        assert ANDROID_ENV["ANDROID_DATA"] == "/data"

    def test_bootclasspath_contains_core_oj(self) -> None:
        assert "core-oj.jar" in ANDROID_ENV["BOOTCLASSPATH"]


# ── Device descriptors ────────────────────────────────────────────────────────


class TestDeviceDescriptors:
    def test_static_char_devices_includes_binder(self) -> None:
        names = [d.name for d in _static_char_devices()]
        assert "binder" in names
        assert "vndbinder" in names
        assert "hwbinder" in names

    def test_static_char_devices_includes_ashmem(self) -> None:
        names = [d.name for d in _static_char_devices()]
        assert "ashmem" in names

    def test_static_char_devices_no_duplicates(self) -> None:
        names = [d.name for d in _static_char_devices()]
        assert len(names) == len(set(names))

    def test_glob_char_devices_returns_list(self) -> None:
        # No real /dev/dri/renderD* in CI — just verify it returns a list
        result = _glob_char_devices()
        assert isinstance(result, list)

    def test_glob_char_devices_uses_correct_prefix(self, tmp_path: Path) -> None:
        fake_render = tmp_path / "renderD128"
        fake_render.touch()
        with patch(
            "waydroid_toolkit.core.container.incus_backend.glob.glob",
            side_effect=lambda p: [str(fake_render)] if "renderD*" in p else [],
        ):
            devices = _glob_char_devices()
        assert any(d.name.startswith("dri_render_") for d in devices)

    def test_static_disk_mounts_includes_tmpfs(self) -> None:
        sources = [m.source for m in _static_disk_mounts()]
        assert "tmpfs" in sources

    def test_static_disk_mounts_includes_vendor(self) -> None:
        paths = [m.path for m in _static_disk_mounts()]
        assert "/vendor_extra" in paths

    def test_static_disk_mounts_includes_wslg(self) -> None:
        names = [m.name for m in _static_disk_mounts()]
        assert "wslg" in names


# ── LxcBackend ────────────────────────────────────────────────────────────────

class TestLxcBackend:
    def test_backend_type(self) -> None:
        assert LxcBackend().backend_type == BackendType.LXC

    def test_is_available_true(self) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value="/usr/bin/lxc-start"):
            assert LxcBackend().is_available() is True

    def test_is_available_false(self) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value=None):
            assert LxcBackend().is_available() is False

    @pytest.mark.parametrize("stdout,expected", [
        ("State: RUNNING\n", ContainerState.RUNNING),
        ("State: STOPPED\n", ContainerState.STOPPED),
        ("State: FROZEN\n",  ContainerState.FROZEN),
        ("State: UNKNOWN\n", ContainerState.UNKNOWN),
        ("",                 ContainerState.UNKNOWN),
    ])
    def test_get_state(self, stdout: str, expected: ContainerState) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value="/usr/bin/lxc-info"):
            with patch("waydroid_toolkit.core.container.lxc_backend.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=stdout)
                assert LxcBackend().get_state() == expected

    def test_get_state_binary_missing(self) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value=None):
            assert LxcBackend().get_state() == ContainerState.UNKNOWN

    def test_get_state_timeout(self) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value="/usr/bin/lxc-info"):
            with patch(
                "waydroid_toolkit.core.container.lxc_backend.subprocess.run",
                side_effect=subprocess.TimeoutExpired("lxc-info", 5),
            ):
                assert LxcBackend().get_state() == ContainerState.UNKNOWN

    def test_execute_calls_lxc_attach(self) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output")
            LxcBackend().execute(["getprop", "ro.build.version.release"])
            call_args = mock_run.call_args[0][0]
            assert "lxc-attach" in call_args
            assert "-n" in call_args
            assert "waydroid" in call_args
            assert "getprop" in call_args

    def test_get_info_returns_backend_info(self) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value="/usr/bin/lxc-info"):
            with patch("waydroid_toolkit.core.container.lxc_backend.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="4.0.12\n")
                info = LxcBackend().get_info()
        assert info.backend_type == BackendType.LXC
        assert info.version == "4.0.12"
        assert info.container_name == "waydroid"


# ── IncusBackend ──────────────────────────────────────────────────────────────

class TestIncusBackend:
    def test_backend_type(self) -> None:
        assert IncusBackend().backend_type == BackendType.INCUS

    def test_is_available_true(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value="/usr/bin/incus"):
            assert IncusBackend().is_available() is True

    def test_is_available_false(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value=None):
            assert IncusBackend().is_available() is False

    @pytest.mark.parametrize("status_str,expected", [
        ("running", ContainerState.RUNNING),
        ("stopped", ContainerState.STOPPED),
        ("frozen",  ContainerState.FROZEN),
        ("unknown", ContainerState.UNKNOWN),
    ])
    def test_get_state(self, status_str: str, expected: ContainerState) -> None:
        payload = json.dumps({"status": status_str})
        with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value="/usr/bin/incus"):
            with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=payload)
                assert IncusBackend().get_state() == expected

    def test_get_state_bad_json(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value="/usr/bin/incus"):
            with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="not-json")
                assert IncusBackend().get_state() == ContainerState.UNKNOWN

    def test_get_state_nonzero_returncode(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value="/usr/bin/incus"):
            with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="")
                assert IncusBackend().get_state() == ContainerState.UNKNOWN

    def test_get_state_binary_missing(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value=None):
            assert IncusBackend().get_state() == ContainerState.UNKNOWN

    def test_execute_calls_incus_exec(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output")
            IncusBackend().execute(["getprop", "ro.build.version.release"])
            call_args = mock_run.call_args[0][0]
            assert "incus" in call_args
            assert "exec" in call_args
            assert "waydroid" in call_args
            assert "getprop" in call_args

    def test_execute_passes_android_env(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            IncusBackend().execute(["true"])
            flat = " ".join(mock_run.call_args[0][0])
            assert "ANDROID_ROOT=/system" in flat
            assert "PATH=" in flat

    def test_execute_passes_uid_gid(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            IncusBackend().execute(["true"], uid=1000, gid=1000)
            flat = " ".join(mock_run.call_args[0][0])
            assert "--user" in flat
            assert "1000:1000" in flat

    def test_execute_uid_defaults_gid_to_uid(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            IncusBackend().execute(["true"], uid=500)
            flat = " ".join(mock_run.call_args[0][0])
            assert "500:500" in flat

    def test_execute_disable_apparmor(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            IncusBackend().execute(["true"], disable_apparmor=True)
            flat = " ".join(mock_run.call_args[0][0])
            assert "--disable-apparmor" in flat

    def test_execute_no_disable_apparmor_by_default(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            IncusBackend().execute(["true"])
            flat = " ".join(mock_run.call_args[0][0])
            assert "--disable-apparmor" not in flat

    def test_execute_extra_env_merged(self) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            IncusBackend().execute(["true"], extra_env={"MY_VAR": "hello"})
            flat = " ".join(mock_run.call_args[0][0])
            assert "MY_VAR=hello" in flat

    def test_configure_session_adds_devices(self) -> None:
        session = SessionConfig(
            wayland_host_socket="/run/user/1000/wayland-0",
            wayland_container_socket="/run/waydroid-session/wayland-0",
            pulse_host_socket="/run/user/1000/pulse/native",
            pulse_container_socket="/run/waydroid-session/pulse/native",
            waydroid_data="/home/user/.local/share/waydroid/data",
            xdg_runtime_dir="/run/waydroid-session",
        )
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            IncusBackend().configure_session(session)
        # Each device: one remove attempt + one add call
        # command: ["incus", "config", "device", "add", CONTAINER, NAME, ...]
        add_calls = [
            c for c in mock_run.call_args_list
            if len(c[0][0]) > 3 and c[0][0][3] == "add"
        ]
        device_names = [c[0][0][5] for c in add_calls]
        assert "session_wayland" in device_names
        assert "session_pulse" in device_names
        assert "session_data" in device_names
        assert "session_xdg_tmpfs" in device_names

    def test_remove_session_devices_removes_all(self) -> None:
        session = SessionConfig(
            wayland_host_socket="/run/user/1000/wayland-0",
            wayland_container_socket="/run/waydroid-session/wayland-0",
            pulse_host_socket="/run/user/1000/pulse/native",
            pulse_container_socket="/run/waydroid-session/pulse/native",
            waydroid_data="/home/user/.local/share/waydroid/data",
            xdg_runtime_dir="/run/waydroid-session",
        )
        with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            IncusBackend().remove_session_devices(session)
        remove_calls = [
            c for c in mock_run.call_args_list
            if "remove" in c[0][0]
        ]
        assert len(remove_calls) == 4

    def test_get_info_parses_client_version(self) -> None:
        version_output = "Client version: 6.1\nServer version: 6.1\n"
        with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value="/usr/bin/incus"):
            with patch("waydroid_toolkit.core.container.incus_backend.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=version_output)
                info = IncusBackend().get_info()
        assert info.backend_type == BackendType.INCUS
        assert info.version == "6.1"
        assert info.container_name == "waydroid"

    def test_setup_from_lxc_raises_without_config(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.core.container.incus_backend._LXC_CONFIG_PATH", tmp_path / "nonexistent"):
            with pytest.raises(RuntimeError, match="LXC config not found"):
                IncusBackend().setup_from_lxc()

    def test_collect_raw_lxc_directives(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config"
        cfg.write_text(
            "lxc.mount.entry = /dev/binder dev/binder none bind,create=file 0 0\n"
            "lxc.seccomp.profile = /var/lib/lxc/waydroid/waydroid.seccomp\n"
            "lxc.net.0.type = none\n"  # should NOT be included
        )
        backend = IncusBackend()
        with patch("waydroid_toolkit.core.container.incus_backend._LXC_CONFIG_PATH", cfg):
            with patch("waydroid_toolkit.core.container.incus_backend._LXC_NODES_PATH", tmp_path / "nx"):
                with patch("waydroid_toolkit.core.container.incus_backend._LXC_SESSION_PATH", tmp_path / "nx2"):
                    result = backend._collect_raw_lxc_directives()
        assert "lxc.mount.entry" in result
        assert "lxc.seccomp.profile" in result
        assert "lxc.net.0.type" not in result


# ── Selector ──────────────────────────────────────────────────────────────────

class TestSelector:
    def test_detect_prefers_lxc(self) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value="/usr/bin/lxc-start"):
            backend = detect()
        assert backend.backend_type == BackendType.LXC

    def test_detect_falls_back_to_incus(self) -> None:
        # Patch is_available on the backend instances that selector.detect() creates
        with patch.object(LxcBackend, "is_available", return_value=False):
            with patch.object(IncusBackend, "is_available", return_value=True):
                backend = detect()
        assert backend.backend_type == BackendType.INCUS

    def test_detect_raises_when_none_available(self) -> None:
        with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value=None):
            with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value=None):
                with pytest.raises(RuntimeError, match="No container backend found"):
                    detect()

    def test_set_and_get_active(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        with patch("waydroid_toolkit.core.container.selector._CONFIG_PATH", config_file):
            with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value="/usr/bin/lxc-start"):
                set_active(BackendType.LXC)
                assert config_file.exists()
                backend = get_active()
        assert backend.backend_type == BackendType.LXC

    def test_get_active_falls_back_to_detect_on_empty_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        with patch("waydroid_toolkit.core.container.selector._CONFIG_PATH", config_file):
            with patch("waydroid_toolkit.core.container.lxc_backend.shutil.which", return_value="/usr/bin/lxc-start"):
                backend = get_active()
        assert backend.backend_type == BackendType.LXC

    def test_get_active_raises_if_configured_backend_unavailable(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        with patch("waydroid_toolkit.core.container.selector._CONFIG_PATH", config_file):
            with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value="/usr/bin/incus"):
                set_active(BackendType.INCUS)
            # Now make incus unavailable
            with patch("waydroid_toolkit.core.container.incus_backend.shutil.which", return_value=None):
                with pytest.raises(RuntimeError, match="not available"):
                    get_active()
