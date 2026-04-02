"""Tests for the Widevine L3 extension."""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.extensions.widevine import (
    WidevineExtension,
    _detect_arch,
    install_widevine,
)


# ── WidevineExtension meta ────────────────────────────────────────────────────

class TestMeta:
    def test_id_is_widevine(self) -> None:
        assert WidevineExtension().meta.id == "widevine"

    def test_name_contains_android_version(self) -> None:
        assert "11" in WidevineExtension("11").meta.name
        assert "13" in WidevineExtension("13").meta.name

    def test_requires_root(self) -> None:
        assert WidevineExtension().meta.requires_root is True

    def test_invalid_version_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            WidevineExtension("99")

    def test_registered_in_registry(self) -> None:
        from waydroid_toolkit.modules.extensions import get
        ext = get("widevine")
        assert ext.meta.id == "widevine"


# ── _detect_arch ──────────────────────────────────────────────────────────────

class TestDetectArch:
    def test_x86_64(self) -> None:
        with patch("platform.machine", return_value="x86_64"):
            assert _detect_arch() == "x86_64"

    def test_aarch64(self) -> None:
        with patch("platform.machine", return_value="aarch64"):
            assert _detect_arch() == "arm64-v8a"

    def test_unknown_defaults_to_x86_64(self) -> None:
        with patch("platform.machine", return_value="riscv64"):
            assert _detect_arch() == "x86_64"


# ── install_widevine ──────────────────────────────────────────────────────────

def _make_widevine_zip(tmp_path: Path, sha: str = "abc123") -> Path:
    """Build a minimal Widevine zip with the expected directory structure."""
    zip_path = tmp_path / "widevine.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        base = f"vendor_google_proprietary_widevine-prebuilt-{sha}/prebuilts/"
        zf.writestr(base + "lib64/libwvhidl.so", b"fake-lib")
        zf.writestr(base + "lib64/libwvaidl.so", b"fake-lib")
        zf.writestr(base + "lib/libwvhidl.so", b"fake-lib")
        zf.writestr(base + "bin/move_widevine_data.sh", b"#!/bin/sh")
    return zip_path


class TestInstallWidevine:
    def test_calls_sudo_mkdir_and_cp(self, tmp_path: Path) -> None:
        zip_path = _make_widevine_zip(tmp_path)
        overlay = tmp_path / "overlay" / "vendor"
        overlay.mkdir(parents=True)

        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            install_widevine(zip_path, overlay, "11")

        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("mkdir" in c for c in cmds)
        assert any("cp" in c for c in cmds)

    def test_android_13_creates_symlink(self, tmp_path: Path) -> None:
        zip_path = _make_widevine_zip(tmp_path)
        overlay = tmp_path / "overlay" / "vendor"
        overlay.mkdir(parents=True)

        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            install_widevine(zip_path, overlay, "13")

        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("ln" in c and "libprotobuf" in c for c in cmds)

    def test_android_11_no_symlink(self, tmp_path: Path) -> None:
        zip_path = _make_widevine_zip(tmp_path)
        overlay = tmp_path / "overlay" / "vendor"
        overlay.mkdir(parents=True)

        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            install_widevine(zip_path, overlay, "11")

        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert not any("libprotobuf" in c for c in cmds)

    def test_raises_on_missing_prebuilts(self, tmp_path: Path) -> None:
        zip_path = tmp_path / "bad.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("some-dir/README.txt", "no prebuilts here")

        with pytest.raises(RuntimeError, match="prebuilts"):
            install_widevine(zip_path, tmp_path / "vendor", "11")

    def test_progress_called(self, tmp_path: Path) -> None:
        zip_path = _make_widevine_zip(tmp_path)
        overlay = tmp_path / "overlay" / "vendor"
        overlay.mkdir(parents=True)
        messages: list[str] = []

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            install_widevine(zip_path, overlay, "11", progress=messages.append)

        assert messages


# ── WidevineExtension.install ─────────────────────────────────────────────────

class TestWidevineInstall:
    def test_raises_when_overlay_disabled(self) -> None:
        ext = WidevineExtension()
        with patch("waydroid_toolkit.modules.extensions.widevine.require_root"), \
             patch("waydroid_toolkit.modules.extensions.widevine.is_overlay_enabled",
                   return_value=False):
            with pytest.raises(RuntimeError, match="mount_overlays"):
                ext.install()

    def test_raises_on_unsupported_arch_version_combo(self) -> None:
        ext = WidevineExtension("13")
        with patch("waydroid_toolkit.modules.extensions.widevine.require_root"), \
             patch("waydroid_toolkit.modules.extensions.widevine.is_overlay_enabled",
                   return_value=True), \
             patch("waydroid_toolkit.modules.extensions.widevine._detect_arch",
                   return_value="arm64-v8a"):
            with pytest.raises(RuntimeError, match="No Widevine package"):
                ext.install()

    def test_uses_cached_zip_when_md5_matches(self, tmp_path: Path) -> None:
        from waydroid_toolkit.modules.extensions.widevine import _SOURCES
        ext = WidevineExtension("11")
        _, expected_md5 = _SOURCES["x86_64"]["11"]
        cache = tmp_path / "widevine-11-x86_64.zip"
        cache.write_bytes(b"fake")

        with patch("waydroid_toolkit.modules.extensions.widevine.require_root"), \
             patch("waydroid_toolkit.modules.extensions.widevine.is_overlay_enabled",
                   return_value=True), \
             patch("waydroid_toolkit.modules.extensions.widevine._detect_arch",
                   return_value="x86_64"), \
             patch("waydroid_toolkit.modules.extensions.widevine._CACHE_DIR", tmp_path), \
             patch("waydroid_toolkit.modules.extensions.widevine._md5",
                   return_value=expected_md5), \
             patch("waydroid_toolkit.modules.extensions.widevine.download") as mock_dl, \
             patch("waydroid_toolkit.modules.extensions.widevine.subprocess.run",
                   return_value=MagicMock(returncode=0)), \
             patch("waydroid_toolkit.modules.extensions.widevine.install_widevine"):
            messages: list[str] = []
            ext.install(progress=messages.append)

        mock_dl.assert_not_called()
        assert any("cached" in m for m in messages)

    def test_md5_mismatch_raises_and_deletes(self, tmp_path: Path) -> None:
        ext = WidevineExtension("11")
        cache = tmp_path / "widevine-11-x86_64.zip"
        cache.write_bytes(b"corrupt")

        with patch("waydroid_toolkit.modules.extensions.widevine.require_root"), \
             patch("waydroid_toolkit.modules.extensions.widevine.is_overlay_enabled",
                   return_value=True), \
             patch("waydroid_toolkit.modules.extensions.widevine._detect_arch",
                   return_value="x86_64"), \
             patch("waydroid_toolkit.modules.extensions.widevine._CACHE_DIR", tmp_path), \
             patch("waydroid_toolkit.modules.extensions.widevine.download"):
            with pytest.raises(RuntimeError, match="MD5 mismatch"):
                ext.install()
        assert not cache.exists()


# ── WidevineExtension.uninstall ───────────────────────────────────────────────

class TestWidevineUninstall:
    def test_removes_present_targets(self) -> None:
        ext = WidevineExtension()
        with patch("waydroid_toolkit.modules.extensions.widevine.require_root"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run, \
             patch("pathlib.Path.exists", return_value=True):
            ext.uninstall()
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("rm" in c for c in cmds)

    def test_skips_absent_targets(self) -> None:
        ext = WidevineExtension()
        with patch("waydroid_toolkit.modules.extensions.widevine.require_root"), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run, \
             patch("pathlib.Path.exists", return_value=False):
            ext.uninstall()
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert not any("rm" in c for c in cmds)
