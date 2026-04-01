"""Tests for the extension registry and base class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.extensions import REGISTRY, get, list_all
from waydroid_toolkit.modules.extensions.base import ExtensionState


def test_registry_contains_expected_extensions() -> None:
    expected = {"gapps", "microg", "magisk", "libhoudini", "libndk"}
    assert expected == set(REGISTRY.keys())


def test_get_known_extension() -> None:
    ext = get("gapps")
    assert ext.meta.id == "gapps"
    assert ext.meta.name


def test_get_unknown_extension_raises() -> None:
    with pytest.raises(KeyError, match="Unknown extension"):
        get("nonexistent")


def test_list_all_returns_all() -> None:
    exts = list_all()
    assert len(exts) == len(REGISTRY)


def test_gapps_conflicts_with_microg() -> None:
    gapps = get("gapps")
    assert "microg" in gapps.meta.conflicts


def test_microg_conflicts_with_gapps() -> None:
    microg = get("microg")
    assert "gapps" in microg.meta.conflicts


def test_libhoudini_conflicts_with_libndk() -> None:
    houdini = get("libhoudini")
    assert "libndk" in houdini.meta.conflicts


def test_extension_state_returns_enum(monkeypatch) -> None:
    ext = get("gapps")
    monkeypatch.setattr(ext, "is_installed", lambda: False)
    assert ext.state() == ExtensionState.NOT_INSTALLED

    monkeypatch.setattr(ext, "is_installed", lambda: True)
    assert ext.state() == ExtensionState.INSTALLED

    monkeypatch.setattr(ext, "is_installed", lambda: (_ for _ in ()).throw(RuntimeError("oops")))
    assert ext.state() == ExtensionState.UNKNOWN


# ── is_installed checks ───────────────────────────────────────────────────────

class TestIsInstalled:
    def test_gapps_not_installed_when_marker_absent(self) -> None:
        ext = get("gapps")
        with patch("waydroid_toolkit.modules.extensions.gapps._MARKER") as mock_marker:
            mock_marker.exists.return_value = False
            assert ext.is_installed() is False

    def test_gapps_installed_when_marker_present(self) -> None:
        ext = get("gapps")
        with patch("waydroid_toolkit.modules.extensions.gapps._MARKER") as mock_marker:
            mock_marker.exists.return_value = True
            assert ext.is_installed() is True

    def test_microg_not_installed_when_marker_absent(self) -> None:
        ext = get("microg")
        with patch("waydroid_toolkit.modules.extensions.microg._MICROG_MARKER") as mock_marker:
            mock_marker.exists.return_value = False
            assert ext.is_installed() is False

    def test_magisk_not_installed_when_marker_absent(self) -> None:
        ext = get("magisk")
        with patch("waydroid_toolkit.modules.extensions.magisk._MAGISK_MARKER") as mock_marker:
            mock_marker.exists.return_value = False
            assert ext.is_installed() is False

    def test_libhoudini_not_installed_when_marker_absent(self) -> None:
        ext = get("libhoudini")
        with patch("waydroid_toolkit.modules.extensions.arm_translation._HOUDINI_MARKER") as m:
            m.exists.return_value = False
            assert ext.is_installed() is False

    def test_libndk_not_installed_when_marker_absent(self) -> None:
        ext = get("libndk")
        with patch("waydroid_toolkit.modules.extensions.arm_translation._NDK_MARKER") as m:
            m.exists.return_value = False
            assert ext.is_installed() is False


# ── install / uninstall ───────────────────────────────────────────────────────

class TestGAppsInstall:
    def test_raises_when_overlay_disabled(self) -> None:
        ext = get("gapps")
        with patch("waydroid_toolkit.modules.extensions.gapps.require_root"):
            with patch("waydroid_toolkit.modules.extensions.gapps.is_overlay_enabled", return_value=False):
                with pytest.raises(RuntimeError, match="mount_overlays"):
                    ext.install()

    def test_uninstall_removes_marker(self) -> None:
        ext = get("gapps")
        with patch("waydroid_toolkit.modules.extensions.gapps.require_root"):
            with patch("waydroid_toolkit.modules.extensions.gapps._MARKER") as mock_marker:
                mock_marker.exists.return_value = True
                with patch("waydroid_toolkit.modules.extensions.gapps.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    ext.uninstall()
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("rm" in c for c in cmds)


class TestMicroGInstall:
    def test_raises_when_overlay_disabled(self) -> None:
        ext = get("microg")
        with patch("waydroid_toolkit.modules.extensions.microg.require_root"):
            with patch("waydroid_toolkit.modules.extensions.microg.is_overlay_enabled", return_value=False):
                with pytest.raises(RuntimeError, match="mount_overlays"):
                    ext.install()

    def test_uninstall_calls_rm(self) -> None:
        ext = get("microg")
        with patch("waydroid_toolkit.modules.extensions.microg.require_root"):
            with patch("waydroid_toolkit.modules.extensions.microg.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                ext.uninstall()
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("rm" in c for c in cmds)


class TestMagiskInstall:
    def test_raises_when_overlay_disabled(self) -> None:
        ext = get("magisk")
        with patch("waydroid_toolkit.modules.extensions.magisk.require_root"):
            with patch("waydroid_toolkit.modules.extensions.magisk.is_overlay_enabled", return_value=False):
                with pytest.raises(RuntimeError, match="mount_overlays"):
                    ext.install()

    def test_raises_when_waydroid_not_running(self) -> None:
        from waydroid_toolkit.core.waydroid import SessionState
        ext = get("magisk")
        with patch("waydroid_toolkit.modules.extensions.magisk.require_root"):
            with patch("waydroid_toolkit.modules.extensions.magisk.is_overlay_enabled", return_value=True):
                with patch("waydroid_toolkit.modules.extensions.magisk.get_session_state",
                           return_value=SessionState.STOPPED):
                    with pytest.raises(RuntimeError, match="running"):
                        ext.install()


# ── conflict metadata ─────────────────────────────────────────────────────────

class TestConflicts:
    def test_all_extensions_have_id(self) -> None:
        for ext in list_all():
            assert ext.meta.id

    def test_all_extensions_have_description(self) -> None:
        for ext in list_all():
            assert ext.meta.description

    def test_magisk_has_no_conflicts(self) -> None:
        assert get("magisk").meta.conflicts == []
