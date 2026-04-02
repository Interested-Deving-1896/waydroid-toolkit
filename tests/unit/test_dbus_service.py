"""Tests for waydroid_toolkit.modules.dbus.service.

The dbus-python library is not available in CI. All tests exercise the
WdtService public API methods directly (without a real D-Bus connection).
The run() method is tested only to confirm it raises ImportError when
dbus-python is absent.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.dbus.service import (
    BUS_NAME,
    INTERFACE,
    OBJECT_PATH,
    WdtService,
)

# ── Constants ─────────────────────────────────────────────────────────────────

class TestConstants:
    def test_bus_name(self) -> None:
        assert BUS_NAME == "io.github.waydroid_toolkit"

    def test_object_path(self) -> None:
        assert OBJECT_PATH == "/io/github/waydroid_toolkit"

    def test_interface(self) -> None:
        assert INTERFACE == "io.github.waydroid_toolkit.Manager"


# ── get_status ────────────────────────────────────────────────────────────────

class TestGetStatus:
    def test_returns_dict_with_state_and_version(self) -> None:
        svc = WdtService()
        mock_state = MagicMock()
        mock_state.value = "running"
        with patch("waydroid_toolkit.modules.dbus.service.WdtService.get_status",
                   return_value={"state": "running", "version": "0.1.0"}):
            result = svc.get_status()
        assert "state" in result
        assert "version" in result

    def test_state_unknown_on_exception(self) -> None:
        svc = WdtService()
        with patch(
            "waydroid_toolkit.core.waydroid.get_session_state",
            side_effect=RuntimeError("no waydroid"),
        ):
            result = svc.get_status()
        assert result["state"] == "unknown"

    def test_version_matches_package(self) -> None:
        from waydroid_toolkit import __version__
        svc = WdtService()
        with patch("waydroid_toolkit.core.waydroid.get_session_state",
                   side_effect=RuntimeError):
            result = svc.get_status()
        assert result["version"] == __version__


# ── list_profiles ─────────────────────────────────────────────────────────────

class TestListProfiles:
    def test_returns_list_of_dicts(self) -> None:
        from pathlib import Path

        from waydroid_toolkit.modules.images.manager import ImageProfile
        mock_profiles = [
            ImageProfile(name="lineage-20", path=Path("/img/lineage-20")),
            ImageProfile(name="atv-11",     path=Path("/img/atv-11")),
        ]
        svc = WdtService()
        with patch("waydroid_toolkit.modules.images.scan_profiles",
                   return_value=mock_profiles):
            result = svc.list_profiles()
        assert len(result) == 2
        assert result[0]["name"] == "lineage-20"
        assert result[1]["name"] == "atv-11"

    def test_empty_when_no_profiles(self) -> None:
        svc = WdtService()
        with patch("waydroid_toolkit.modules.images.scan_profiles", return_value=[]):
            assert svc.list_profiles() == []


# ── switch_profile ────────────────────────────────────────────────────────────

class TestSwitchProfile:
    def test_returns_true_on_success(self) -> None:
        from pathlib import Path

        from waydroid_toolkit.modules.images.manager import ImageProfile
        mock_profiles = [ImageProfile(name="lineage-20", path=Path("/img/lineage-20"))]
        svc = WdtService()
        with patch("waydroid_toolkit.modules.images.scan_profiles",
                   return_value=mock_profiles):
            with patch("waydroid_toolkit.modules.images.switch_profile"):
                result = svc.switch_profile("lineage-20")
        assert result is True

    def test_returns_false_when_profile_not_found(self) -> None:
        svc = WdtService()
        with patch("waydroid_toolkit.modules.images.scan_profiles", return_value=[]):
            result = svc.switch_profile("nonexistent")
        assert result is False


# ── list_extensions ───────────────────────────────────────────────────────────

class TestListExtensions:
    def test_returns_list_with_id_name_state(self) -> None:
        from waydroid_toolkit.modules.extensions.base import ExtensionState
        mock_ext = MagicMock()
        mock_ext.meta.id = "gapps"
        mock_ext.meta.name = "Google Apps"
        mock_ext.state.return_value = ExtensionState.NOT_INSTALLED
        svc = WdtService()
        with patch("waydroid_toolkit.modules.extensions.list_all",
                   return_value=[mock_ext]):
            result = svc.list_extensions()
        assert len(result) == 1
        assert result[0]["id"] == "gapps"
        assert result[0]["name"] == "Google Apps"
        assert result[0]["state"] == "not_installed"

    def test_returns_empty_list_when_no_extensions(self) -> None:
        svc = WdtService()
        with patch("waydroid_toolkit.modules.extensions.list_all", return_value=[]):
            assert svc.list_extensions() == []


# ── install_extension ─────────────────────────────────────────────────────────

class TestInstallExtension:
    def test_returns_true_on_success(self) -> None:
        svc = WdtService()
        with patch("waydroid_toolkit.modules.extensions.install_with_deps",
                   return_value=["gapps"]):
            result = svc.install_extension("gapps")
        assert result is True

    def test_returns_false_on_exception(self) -> None:
        svc = WdtService()
        with patch("waydroid_toolkit.modules.extensions.install_with_deps",
                   side_effect=RuntimeError("install failed")):
            result = svc.install_extension("gapps")
        assert result is False

    def test_returns_false_on_conflict_error(self) -> None:
        from waydroid_toolkit.modules.extensions.resolver import ConflictError
        svc = WdtService()
        with patch("waydroid_toolkit.modules.extensions.install_with_deps",
                   side_effect=ConflictError("gapps", "microg")):
            result = svc.install_extension("gapps")
        assert result is False


# ── create_snapshot ───────────────────────────────────────────────────────────

class TestCreateSnapshot:
    def test_returns_snapshot_name(self) -> None:
        import datetime

        from waydroid_toolkit.modules.snapshot.backends import SnapshotInfo
        mock_info = SnapshotInfo(
            name="waydroid-20240101_120000-test",
            created=datetime.datetime.now(tz=datetime.UTC),
            backend="zfs",
            source="rpool/waydroid",
        )
        mock_backend = MagicMock()
        mock_backend.create.return_value = mock_info
        svc = WdtService()
        with patch("waydroid_toolkit.modules.snapshot.get_backend",
                   return_value=mock_backend):
            result = svc.create_snapshot("test")
        assert result == "waydroid-20240101_120000-test"
        mock_backend.create.assert_called_once_with("test")

    def test_passes_empty_label(self) -> None:
        import datetime

        from waydroid_toolkit.modules.snapshot.backends import SnapshotInfo
        mock_info = SnapshotInfo(
            name="waydroid-20240101_120000",
            created=datetime.datetime.now(tz=datetime.UTC),
            backend="btrfs",
            source="/var/lib/waydroid",
        )
        mock_backend = MagicMock()
        mock_backend.create.return_value = mock_info
        svc = WdtService()
        with patch("waydroid_toolkit.modules.snapshot.get_backend",
                   return_value=mock_backend):
            svc.create_snapshot()
        mock_backend.create.assert_called_once_with("")


# ── list_snapshots ────────────────────────────────────────────────────────────

class TestListSnapshots:
    def test_returns_list_of_dicts(self) -> None:
        import datetime

        from waydroid_toolkit.modules.snapshot.backends import SnapshotInfo
        now = datetime.datetime.now(tz=datetime.UTC)
        mock_snaps = [
            SnapshotInfo(name="waydroid-20240101_120000", created=now,
                         backend="zfs", source="rpool/waydroid"),
        ]
        mock_backend = MagicMock()
        mock_backend.list.return_value = mock_snaps
        svc = WdtService()
        with patch("waydroid_toolkit.modules.snapshot.get_backend",
                   return_value=mock_backend):
            result = svc.list_snapshots()
        assert len(result) == 1
        assert result[0]["name"] == "waydroid-20240101_120000"
        assert result[0]["backend"] == "zfs"

    def test_returns_empty_when_no_backend(self) -> None:
        svc = WdtService()
        with patch("waydroid_toolkit.modules.snapshot.get_backend",
                   side_effect=RuntimeError("no backend")):
            result = svc.list_snapshots()
        assert result == []


# ── stop ──────────────────────────────────────────────────────────────────────

class TestStop:
    def test_quits_loop_when_running(self) -> None:
        svc = WdtService()
        mock_loop = MagicMock()
        svc._loop = mock_loop
        svc.stop()
        mock_loop.quit.assert_called_once()

    def test_no_op_when_loop_is_none(self) -> None:
        svc = WdtService()
        svc._loop = None
        svc.stop()  # must not raise


# ── run() — ImportError when dbus-python absent ───────────────────────────────

class TestRun:
    def test_raises_import_error_when_dbus_missing(self) -> None:
        import sys
        # Ensure dbus is not importable
        with patch.dict(sys.modules, {"dbus": None,
                                       "dbus.mainloop": None,
                                       "dbus.mainloop.glib": None,
                                       "dbus.service": None}):
            svc = WdtService()
            with pytest.raises(ImportError, match="dbus-python"):
                svc.run()
