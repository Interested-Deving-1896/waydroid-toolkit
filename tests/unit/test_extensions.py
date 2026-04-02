"""Tests for the extension registry and base class."""

from __future__ import annotations

from pathlib import Path
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
            with patch("waydroid_toolkit.modules.extensions.gapps.is_overlay_enabled",
                       return_value=False):
                with pytest.raises(RuntimeError, match="mount_overlays"):
                    ext.install()

    def test_raises_on_unsupported_android_version(self) -> None:
        from waydroid_toolkit.modules.extensions.gapps import GAppsExtension
        with pytest.raises(ValueError, match="Unsupported"):
            GAppsExtension(android_version="99")

    def test_android_13_meta_mentions_mindthegapps(self) -> None:
        from waydroid_toolkit.modules.extensions.gapps import GAppsExtension
        ext = GAppsExtension(android_version="13")
        assert "MindTheGapps" in ext.meta.name

    def test_android_11_meta_mentions_opengapps(self) -> None:
        from waydroid_toolkit.modules.extensions.gapps import GAppsExtension
        ext = GAppsExtension(android_version="11")
        assert "OpenGApps" in ext.meta.name

    def test_md5_mismatch_raises_and_deletes_cache(self, tmp_path: Path) -> None:
        from waydroid_toolkit.modules.extensions.gapps import GAppsExtension
        ext = GAppsExtension(android_version="11")
        bad_zip = tmp_path / "gapps-11-x86_64.zip"
        bad_zip.write_bytes(b"corrupt")

        with patch("waydroid_toolkit.modules.extensions.gapps.require_root"), \
             patch("waydroid_toolkit.modules.extensions.gapps.is_overlay_enabled",
                   return_value=True), \
             patch("waydroid_toolkit.modules.extensions.gapps.detect_arch",
                   return_value="x86_64"), \
             patch("waydroid_toolkit.modules.extensions.gapps._CACHE_DIR", tmp_path), \
             patch("waydroid_toolkit.modules.extensions.gapps.download"):
            with pytest.raises(RuntimeError, match="MD5 mismatch"):
                ext.install()
        assert not bad_zip.exists()

    def test_uses_cached_zip_when_md5_matches(self, tmp_path: Path) -> None:
        from waydroid_toolkit.modules.extensions.gapps import _SOURCES, GAppsExtension
        ext = GAppsExtension(android_version="11")
        _, expected_md5 = _SOURCES["11"]["x86_64"]

        # Write a file whose MD5 matches the catalogue entry
        cache = tmp_path / "gapps-11-x86_64.zip"
        # We can't reproduce the real MD5 without the real file, so patch _md5
        with patch("waydroid_toolkit.modules.extensions.gapps.require_root"), \
             patch("waydroid_toolkit.modules.extensions.gapps.is_overlay_enabled",
                   return_value=True), \
             patch("waydroid_toolkit.modules.extensions.gapps.detect_arch",
                   return_value="x86_64"), \
             patch("waydroid_toolkit.modules.extensions.gapps._CACHE_DIR", tmp_path), \
             patch("waydroid_toolkit.modules.extensions.gapps._md5",
                   return_value=expected_md5), \
             patch("waydroid_toolkit.modules.extensions.gapps.download") as mock_dl, \
             patch("waydroid_toolkit.modules.extensions.gapps.subprocess.run",
                   return_value=MagicMock(returncode=0)), \
             patch("waydroid_toolkit.modules.extensions.gapps.install_opengapps_11"):
            cache.write_bytes(b"fake")
            messages: list[str] = []
            ext.install(progress=messages.append)

        mock_dl.assert_not_called()
        assert any("cached" in m for m in messages)

    def test_uninstall_removes_overlay_targets(self) -> None:
        ext = get("gapps")
        with patch("waydroid_toolkit.modules.extensions.gapps.require_root"), \
             patch("waydroid_toolkit.modules.extensions.gapps.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run, \
             patch("pathlib.Path.exists", return_value=True):
            ext.uninstall()
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("rm" in c for c in cmds)

    def test_uninstall_skips_absent_targets(self) -> None:
        ext = get("gapps")
        with patch("waydroid_toolkit.modules.extensions.gapps.require_root"), \
             patch("waydroid_toolkit.modules.extensions.gapps.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run, \
             patch("pathlib.Path.exists", return_value=False):
            ext.uninstall()
        # No rm calls when nothing exists
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert not any("rm" in c for c in cmds)


class TestGAppsHelpers:
    def test_detect_arch_x86_64(self) -> None:
        from waydroid_toolkit.modules.extensions.gapps import detect_arch
        with patch("platform.machine", return_value="x86_64"):
            assert detect_arch() == "x86_64"

    def test_detect_arch_aarch64(self) -> None:
        from waydroid_toolkit.modules.extensions.gapps import detect_arch
        with patch("platform.machine", return_value="aarch64"):
            assert detect_arch() == "arm64-v8a"

    def test_detect_arch_arm(self) -> None:
        from waydroid_toolkit.modules.extensions.gapps import detect_arch
        with patch("platform.machine", return_value="armv7l"):
            assert detect_arch() == "armeabi-v7a"

    def test_check_lzip_raises_when_missing(self) -> None:
        from waydroid_toolkit.modules.extensions.gapps import _check_lzip
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="lzip"):
                _check_lzip()

    def test_check_lzip_passes_when_present(self) -> None:
        from waydroid_toolkit.modules.extensions.gapps import _check_lzip
        with patch("shutil.which", return_value="/usr/bin/lzip"):
            _check_lzip()  # must not raise

    def test_install_mindthegapps_13_copies_system_tree(self, tmp_path: Path) -> None:
        import zipfile as zf

        from waydroid_toolkit.modules.extensions.gapps import install_mindthegapps_13

        # Build a minimal MindTheGapps zip: system/priv-app/GmsCore/GmsCore.apk
        zip_path = tmp_path / "mtg.zip"
        with zf.ZipFile(zip_path, "w") as z:
            z.writestr("system/priv-app/GmsCore/GmsCore.apk", b"fake-apk")

        overlay_system = tmp_path / "overlay" / "system"
        overlay_system.mkdir(parents=True)

        with patch("waydroid_toolkit.modules.extensions.gapps.subprocess.run",
                   return_value=MagicMock(returncode=0)) as mock_run:
            install_mindthegapps_13(zip_path, overlay_system)

        # sudo mkdir -p and sudo cp should have been called
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("mkdir" in c for c in cmds)
        assert any("cp" in c for c in cmds)

    def test_install_mindthegapps_13_raises_on_missing_system_dir(
        self, tmp_path: Path
    ) -> None:
        import zipfile as zf

        from waydroid_toolkit.modules.extensions.gapps import install_mindthegapps_13

        zip_path = tmp_path / "bad.zip"
        with zf.ZipFile(zip_path, "w") as z:
            z.writestr("README.txt", "no system dir here")

        with pytest.raises(RuntimeError, match="system/"):
            install_mindthegapps_13(zip_path, tmp_path / "overlay")


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
