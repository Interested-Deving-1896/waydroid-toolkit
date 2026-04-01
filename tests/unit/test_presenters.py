"""Tests for GUI presenter functions and BasePage toast helpers.

Presenters gather data from the domain layer and return plain dataclasses.
No GTK is required — these run in any environment.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from waydroid_toolkit.core.waydroid import SessionState
from waydroid_toolkit.gui.presenters import (
    StatusData,
    get_backup_entries,
    get_device_info_data,
    get_extension_rows,
    get_image_profile_rows,
    get_status_data,
)
from waydroid_toolkit.modules.extensions.base import ExtensionState

# ── get_status_data ───────────────────────────────────────────────────────────

class TestGetStatusData:
    def _patch_all(
        self,
        installed: bool = True,
        initialized: bool = True,
        state: SessionState = SessionState.RUNNING,
        images_path: str = "/images",
        mount_overlays: bool = True,
        adb_ok: bool = True,
        adb_conn: bool = True,
    ):
        from waydroid_toolkit.core.waydroid import WaydroidConfig
        cfg = WaydroidConfig(images_path=images_path, mount_overlays=mount_overlays)
        return [
            patch("waydroid_toolkit.gui.presenters.is_installed", return_value=installed),
            patch("waydroid_toolkit.gui.presenters.is_initialized", return_value=initialized),
            patch("waydroid_toolkit.gui.presenters.get_session_state", return_value=state),
            patch("waydroid_toolkit.gui.presenters.WaydroidConfig.load", return_value=cfg),
            patch("waydroid_toolkit.gui.presenters.adb_available", return_value=adb_ok),
            patch("waydroid_toolkit.gui.presenters.adb_connected", return_value=adb_conn),
        ]

    def test_returns_status_data_instance(self) -> None:
        patches = self._patch_all()
        for p in patches:
            p.start()
        try:
            result = get_status_data()
        finally:
            for p in patches:
                p.stop()
        assert isinstance(result, StatusData)

    def test_installed_true(self) -> None:
        patches = self._patch_all(installed=True)
        for p in patches:
            p.start()
        try:
            result = get_status_data()
        finally:
            for p in patches:
                p.stop()
        assert result.installed is True

    def test_installed_false_skips_initialized_and_state(self) -> None:
        patches = self._patch_all(installed=False)
        for p in patches:
            p.start()
        try:
            result = get_status_data()
        finally:
            for p in patches:
                p.stop()
        assert result.initialized is False
        assert result.session_state == SessionState.UNKNOWN

    def test_adb_connected_false_when_adb_unavailable(self) -> None:
        patches = self._patch_all(adb_ok=False, adb_conn=True)
        for p in patches:
            p.start()
        try:
            result = get_status_data()
        finally:
            for p in patches:
                p.stop()
        # adb_connected should not be called when adb is unavailable
        assert result.adb_connected is False

    def test_images_path_propagated(self) -> None:
        patches = self._patch_all(images_path="/custom/images")
        for p in patches:
            p.start()
        try:
            result = get_status_data()
        finally:
            for p in patches:
                p.stop()
        assert result.images_path == "/custom/images"

    def test_mount_overlays_propagated(self) -> None:
        patches = self._patch_all(mount_overlays=False)
        for p in patches:
            p.start()
        try:
            result = get_status_data()
        finally:
            for p in patches:
                p.stop()
        assert result.mount_overlays is False


# ── get_backup_entries ────────────────────────────────────────────────────────

class TestGetBackupEntries:
    def test_returns_empty_when_no_backups(self, tmp_path: Path) -> None:
        result = get_backup_entries(tmp_path)
        assert result == []

    def test_returns_entry_per_archive(self, tmp_path: Path) -> None:
        for name in ["waydroid_backup_20240101_120000.tar.gz",
                     "waydroid_backup_20240201_090000.tar.gz"]:
            (tmp_path / name).write_bytes(b"x" * 1024)
        result = get_backup_entries(tmp_path)
        assert len(result) == 2

    def test_entry_has_correct_name(self, tmp_path: Path) -> None:
        (tmp_path / "waydroid_backup_20240101_120000.tar.gz").write_bytes(b"x" * 2048)
        result = get_backup_entries(tmp_path)
        assert result[0].name == "waydroid_backup_20240101_120000.tar.gz"

    def test_entry_size_mb_calculated(self, tmp_path: Path) -> None:
        data = b"x" * (1024 * 1024)  # exactly 1 MB
        (tmp_path / "waydroid_backup_20240101_120000.tar.gz").write_bytes(data)
        result = get_backup_entries(tmp_path)
        assert abs(result[0].size_mb - 1.0) < 0.01

    def test_entry_path_is_absolute(self, tmp_path: Path) -> None:
        (tmp_path / "waydroid_backup_20240101_120000.tar.gz").write_bytes(b"x")
        result = get_backup_entries(tmp_path)
        assert result[0].path.is_absolute()

    def test_sorted_newest_first(self, tmp_path: Path) -> None:
        names = [
            "waydroid_backup_20240101_120000.tar.gz",
            "waydroid_backup_20240301_090000.tar.gz",
            "waydroid_backup_20240201_150000.tar.gz",
        ]
        for name in names:
            (tmp_path / name).write_bytes(b"x")
        result = get_backup_entries(tmp_path)
        assert result[0].name == "waydroid_backup_20240301_090000.tar.gz"


# ── get_extension_rows ────────────────────────────────────────────────────────

class TestGetExtensionRows:
    def test_returns_one_row_per_extension(self) -> None:
        with patch("waydroid_toolkit.gui.presenters.list_extensions") as mock_list:
            mock_ext = MagicMock()
            mock_ext.meta.id = "gapps"
            mock_ext.meta.name = "Google Apps"
            mock_ext.meta.description = "GApps"
            mock_ext.meta.conflicts = ["microg"]
            mock_ext.state.return_value = ExtensionState.NOT_INSTALLED
            mock_list.return_value = [mock_ext]
            result = get_extension_rows()
        assert len(result) == 1
        assert result[0].ext_id == "gapps"

    def test_installed_state_propagated(self) -> None:
        with patch("waydroid_toolkit.gui.presenters.list_extensions") as mock_list:
            mock_ext = MagicMock()
            mock_ext.meta.id = "magisk"
            mock_ext.meta.name = "Magisk"
            mock_ext.meta.description = "Root"
            mock_ext.meta.conflicts = []
            mock_ext.state.return_value = ExtensionState.INSTALLED
            mock_list.return_value = [mock_ext]
            result = get_extension_rows()
        assert result[0].state == ExtensionState.INSTALLED

    def test_conflicts_propagated(self) -> None:
        with patch("waydroid_toolkit.gui.presenters.list_extensions") as mock_list:
            mock_ext = MagicMock()
            mock_ext.meta.id = "gapps"
            mock_ext.meta.name = "GApps"
            mock_ext.meta.description = ""
            mock_ext.meta.conflicts = ["microg"]
            mock_ext.state.return_value = ExtensionState.NOT_INSTALLED
            mock_list.return_value = [mock_ext]
            result = get_extension_rows()
        assert "microg" in result[0].conflicts

    def test_returns_all_real_extensions(self) -> None:
        rows = get_extension_rows()
        ids = {r.ext_id for r in rows}
        assert {"gapps", "microg", "magisk", "libhoudini", "libndk"} == ids


# ── get_image_profile_rows ────────────────────────────────────────────────────

class TestGetImageProfileRows:
    def _make_profile(self, tmp_path: Path, name: str):
        from waydroid_toolkit.modules.images.manager import ImageProfile
        d = tmp_path / name
        d.mkdir()
        (d / "system.img").touch()
        (d / "vendor.img").touch()
        return ImageProfile(name=name, path=d)

    def test_returns_empty_when_no_profiles(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.gui.presenters.scan_profiles", return_value=[]):
            with patch("waydroid_toolkit.gui.presenters.get_active_profile", return_value=None):
                result = get_image_profile_rows()
        assert result == []

    def test_returns_one_row_per_profile(self, tmp_path: Path) -> None:
        profiles = [self._make_profile(tmp_path, n) for n in ("vanilla", "gapps")]
        with patch("waydroid_toolkit.gui.presenters.scan_profiles", return_value=profiles):
            with patch("waydroid_toolkit.gui.presenters.get_active_profile", return_value=None):
                result = get_image_profile_rows()
        assert len(result) == 2

    def test_active_profile_marked(self, tmp_path: Path) -> None:
        profile = self._make_profile(tmp_path, "vanilla")
        with patch("waydroid_toolkit.gui.presenters.scan_profiles", return_value=[profile]):
            with patch("waydroid_toolkit.gui.presenters.get_active_profile",
                       return_value=str(profile.path)):
                result = get_image_profile_rows()
        assert result[0].is_active is True

    def test_inactive_profile_not_marked(self, tmp_path: Path) -> None:
        profile = self._make_profile(tmp_path, "vanilla")
        with patch("waydroid_toolkit.gui.presenters.scan_profiles", return_value=[profile]):
            with patch("waydroid_toolkit.gui.presenters.get_active_profile",
                       return_value="/other/path"):
                result = get_image_profile_rows()
        assert result[0].is_active is False

    def test_no_active_profile_all_inactive(self, tmp_path: Path) -> None:
        profiles = [self._make_profile(tmp_path, n) for n in ("a", "b")]
        with patch("waydroid_toolkit.gui.presenters.scan_profiles", return_value=profiles):
            with patch("waydroid_toolkit.gui.presenters.get_active_profile", return_value=None):
                result = get_image_profile_rows()
        assert all(not r.is_active for r in result)


# ── get_device_info_data ──────────────────────────────────────────────────────

class TestGetDeviceInfoData:
    def test_delegates_to_get_device_info(self) -> None:
        expected = {"android_version": "13", "sdk_version": "33"}
        with patch("waydroid_toolkit.gui.presenters.get_device_info", return_value=expected):
            result = get_device_info_data()
        assert result == expected

    def test_returns_dict(self) -> None:
        with patch("waydroid_toolkit.gui.presenters.get_device_info", return_value={}):
            result = get_device_info_data()
        assert isinstance(result, dict)



