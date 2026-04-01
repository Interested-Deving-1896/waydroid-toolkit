"""Tests for the Waydroid core interface."""

from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.core.waydroid import SessionState, WaydroidConfig, get_session_state, is_installed


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
