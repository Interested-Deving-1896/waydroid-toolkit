"""Tests for the image profile manager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.images.manager import (
    ImageProfile,
    get_active_profile,
    scan_profiles,
    switch_profile,
)


def _make_profile(base: Path, name: str) -> Path:
    d = base / name
    d.mkdir(parents=True)
    (d / "system.img").touch()
    (d / "vendor.img").touch()
    return d


def test_scan_profiles_empty(tmp_path: Path) -> None:
    assert scan_profiles(tmp_path) == []


def test_scan_profiles_finds_valid(tmp_path: Path) -> None:
    _make_profile(tmp_path, "vanilla")
    _make_profile(tmp_path, "gapps")
    profiles = scan_profiles(tmp_path)
    assert len(profiles) == 2
    names = {p.name for p in profiles}
    assert names == {"vanilla", "gapps"}


def test_scan_profiles_ignores_incomplete(tmp_path: Path) -> None:
    # Only system.img, no vendor.img
    d = tmp_path / "broken"
    d.mkdir()
    (d / "system.img").touch()
    assert scan_profiles(tmp_path) == []


def test_scan_profiles_nested(tmp_path: Path) -> None:
    nested = tmp_path / "category" / "androidtv"
    nested.mkdir(parents=True)
    (nested / "system.img").touch()
    (nested / "vendor.img").touch()
    profiles = scan_profiles(tmp_path)
    assert len(profiles) == 1
    assert profiles[0].name == "androidtv"


def test_image_profile_is_valid(tmp_path: Path) -> None:
    path = _make_profile(tmp_path, "test")
    p = ImageProfile(name="test", path=path)
    assert p.is_valid is True


def test_image_profile_invalid_missing_vendor(tmp_path: Path) -> None:
    d = tmp_path / "bad"
    d.mkdir()
    (d / "system.img").touch()
    p = ImageProfile(name="bad", path=d)
    assert p.is_valid is False


# ── get_active_profile ────────────────────────────────────────────────────────

class TestGetActiveProfile:
    def test_returns_none_when_images_path_empty(self) -> None:
        with patch("waydroid_toolkit.modules.images.manager.WaydroidConfig.load") as mock_load:
            mock_load.return_value = MagicMock(images_path="")
            assert get_active_profile() is None

    def test_returns_path_when_set(self) -> None:
        with patch("waydroid_toolkit.modules.images.manager.WaydroidConfig.load") as mock_load:
            mock_load.return_value = MagicMock(images_path="/home/user/waydroid-images/vanilla")
            assert get_active_profile() == "/home/user/waydroid-images/vanilla"


# ── switch_profile ────────────────────────────────────────────────────────────

class TestSwitchProfile:
    def _valid_profile(self, tmp_path: Path, name: str = "vanilla") -> ImageProfile:
        d = tmp_path / name
        d.mkdir()
        (d / "system.img").touch()
        (d / "vendor.img").touch()
        return ImageProfile(name=name, path=d)

    def test_raises_for_invalid_profile(self, tmp_path: Path) -> None:
        bad = ImageProfile(name="bad", path=tmp_path / "nonexistent")
        with patch("waydroid_toolkit.modules.images.manager.require_root"):
            with pytest.raises(ValueError, match="missing"):
                switch_profile(bad)

    def test_stops_running_session(self, tmp_path: Path) -> None:
        from waydroid_toolkit.core.waydroid import SessionState
        profile = self._valid_profile(tmp_path)
        with patch("waydroid_toolkit.modules.images.manager.require_root"):
            with patch("waydroid_toolkit.modules.images.manager.get_session_state",
                       return_value=SessionState.RUNNING):
                with patch("waydroid_toolkit.modules.images.manager.run_waydroid") as mock_wd:
                    with patch("waydroid_toolkit.modules.images.manager._set_images_path"):
                        with patch("waydroid_toolkit.modules.images.manager._link_profile_data"):
                            with patch("waydroid_toolkit.modules.images.manager.subprocess.run"):
                                switch_profile(profile)
        mock_wd.assert_called_once_with("session", "stop", sudo=True)

    def test_does_not_stop_when_not_running(self, tmp_path: Path) -> None:
        from waydroid_toolkit.core.waydroid import SessionState
        profile = self._valid_profile(tmp_path)
        with patch("waydroid_toolkit.modules.images.manager.require_root"):
            with patch("waydroid_toolkit.modules.images.manager.get_session_state",
                       return_value=SessionState.STOPPED):
                with patch("waydroid_toolkit.modules.images.manager.run_waydroid") as mock_wd:
                    with patch("waydroid_toolkit.modules.images.manager._set_images_path"):
                        with patch("waydroid_toolkit.modules.images.manager._link_profile_data"):
                            switch_profile(profile)
        mock_wd.assert_not_called()

    def test_calls_set_images_path(self, tmp_path: Path) -> None:
        from waydroid_toolkit.core.waydroid import SessionState
        profile = self._valid_profile(tmp_path)
        with patch("waydroid_toolkit.modules.images.manager.require_root"):
            with patch("waydroid_toolkit.modules.images.manager.get_session_state",
                       return_value=SessionState.STOPPED):
                with patch("waydroid_toolkit.modules.images.manager._set_images_path") as mock_set:
                    with patch("waydroid_toolkit.modules.images.manager._link_profile_data"):
                        switch_profile(profile)
        mock_set.assert_called_once_with(profile.path)
