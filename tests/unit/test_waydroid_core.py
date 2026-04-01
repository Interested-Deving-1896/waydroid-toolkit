"""Tests for the Waydroid core interface."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.core.waydroid import (
    SessionState,
    WaydroidConfig,
    get_android_id,
    get_session_state,
    is_initialized,
    is_installed,
    run_waydroid,
    shell,
)


def test_is_installed_true() -> None:
    with patch("waydroid_toolkit.core.waydroid.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert is_installed() is True


def test_is_installed_false() -> None:
    with patch("waydroid_toolkit.core.waydroid.subprocess.run", side_effect=FileNotFoundError):
        assert is_installed() is False


@pytest.mark.parametrize("stdout,expected", [
    ("Session: RUNNING\nContainer: RUNNING\n", SessionState.RUNNING),
    ("Session: STOPPED\nContainer: STOPPED\n", SessionState.STOPPED),
    ("", SessionState.STOPPED),
])
def test_get_session_state(stdout: str, expected: SessionState) -> None:
    with patch("waydroid_toolkit.core.waydroid.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=stdout)
        assert get_session_state() == expected


def test_get_session_state_not_found() -> None:
    with patch("waydroid_toolkit.core.waydroid.subprocess.run", side_effect=FileNotFoundError):
        assert get_session_state() == SessionState.UNKNOWN


def test_waydroid_config_defaults(tmp_path) -> None:
    cfg = WaydroidConfig()
    assert cfg.images_path == ""
    assert cfg.mount_overlays is True


def test_waydroid_config_load_missing(tmp_path) -> None:
    with patch("waydroid_toolkit.core.waydroid._CFG_PATH", tmp_path / "nonexistent.cfg"):
        cfg = WaydroidConfig.load()
    assert cfg.images_path == ""


def test_waydroid_config_load_parses_values(tmp_path: Path) -> None:
    cfg_file = tmp_path / "waydroid.cfg"
    cfg_file.write_text(
        "[waydroid]\nimages_path = /home/user/images\nmount_overlays = false\n"
    )
    with patch("waydroid_toolkit.core.waydroid._CFG_PATH", cfg_file):
        cfg = WaydroidConfig.load()
    assert cfg.images_path == "/home/user/images"
    assert cfg.mount_overlays is False


def test_waydroid_config_mount_overlays_default_true(tmp_path: Path) -> None:
    cfg_file = tmp_path / "waydroid.cfg"
    cfg_file.write_text("[waydroid]\n")
    with patch("waydroid_toolkit.core.waydroid._CFG_PATH", cfg_file):
        cfg = WaydroidConfig.load()
    assert cfg.mount_overlays is True


# ── run_waydroid ──────────────────────────────────────────────────────────────

def test_run_waydroid_without_sudo() -> None:
    with patch("waydroid_toolkit.core.waydroid.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_waydroid("status")
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "waydroid"
    assert "sudo" not in cmd


def test_run_waydroid_with_sudo() -> None:
    with patch("waydroid_toolkit.core.waydroid.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        run_waydroid("session", "stop", sudo=True)
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "sudo"
    assert "waydroid" in cmd


# ── is_initialized ────────────────────────────────────────────────────────────

def test_is_initialized_false_when_no_images_path() -> None:
    with patch("waydroid_toolkit.core.waydroid.WaydroidConfig.load") as mock_load:
        mock_load.return_value = WaydroidConfig(images_path="")
        assert is_initialized() is False


def test_is_initialized_false_when_images_missing(tmp_path: Path) -> None:
    with patch("waydroid_toolkit.core.waydroid.WaydroidConfig.load") as mock_load:
        mock_load.return_value = WaydroidConfig(images_path=str(tmp_path))
        assert is_initialized() is False


def test_is_initialized_true_when_images_present(tmp_path: Path) -> None:
    (tmp_path / "system.img").touch()
    (tmp_path / "vendor.img").touch()
    with patch("waydroid_toolkit.core.waydroid.WaydroidConfig.load") as mock_load:
        mock_load.return_value = WaydroidConfig(images_path=str(tmp_path))
        assert is_initialized() is True


# ── shell ─────────────────────────────────────────────────────────────────────

def test_shell_routes_through_backend() -> None:
    mock_backend = MagicMock()
    mock_backend.execute.return_value = MagicMock(returncode=0, stdout="result")
    # shell() lazily imports get_active from waydroid_toolkit.core.container;
    # patch the re-export in __init__ so the lazy import resolves to the mock.
    with patch("waydroid_toolkit.core.container.get_active", return_value=mock_backend):
        shell("getprop ro.build.version.release")
    mock_backend.execute.assert_called_once()


def test_shell_falls_back_to_waydroid_cli() -> None:
    with patch("waydroid_toolkit.core.container.get_active",
               side_effect=RuntimeError("no backend")):
        with patch("waydroid_toolkit.core.waydroid.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            shell("getprop ro.build.version.release")
    cmd = " ".join(mock_run.call_args[0][0])
    assert "waydroid" in cmd
    assert "shell" in cmd


# ── get_android_id ────────────────────────────────────────────────────────────

def test_get_android_id_returns_id_on_success() -> None:
    with patch("waydroid_toolkit.core.waydroid.shell") as mock_shell:
        mock_shell.return_value = MagicMock(returncode=0, stdout="android_id|1234567890abcdef\n")
        result = get_android_id()
    assert result == "1234567890abcdef"


def test_get_android_id_returns_none_on_failure() -> None:
    with patch("waydroid_toolkit.core.waydroid.shell") as mock_shell:
        mock_shell.return_value = MagicMock(returncode=1, stdout="")
        result = get_android_id()
    assert result is None
