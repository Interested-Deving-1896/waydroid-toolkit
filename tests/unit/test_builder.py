"""Tests for the builder module (wdt build / wdt install --from-manifest)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.builder.builder import (
    build_android_image,
    ensure_eggs,
    find_eggs,
    install_eggs,
    read_manifest,
)
from waydroid_toolkit.utils.android_shared import AndroidShared

_VALID_MANIFEST = {
    AndroidShared.MANIFEST_VERSION:    AndroidShared.MANIFEST_SCHEMA_VER,
    AndroidShared.MANIFEST_ARCH:       "x86_64",
    AndroidShared.MANIFEST_VARIANT:    "waydroid",
    AndroidShared.MANIFEST_ANDROID_VER: "14",
    AndroidShared.MANIFEST_SDK_LEVEL:  "34",
    AndroidShared.MANIFEST_BUILD_ID:   "TEST.001",
    AndroidShared.MANIFEST_SYSTEM_IMG: "/tmp/system.img",
    AndroidShared.MANIFEST_BOOT_IMG:   "/tmp/boot.img",
    AndroidShared.MANIFEST_VENDOR_IMG: "",
    AndroidShared.MANIFEST_AVB_SIGNED: False,
    AndroidShared.MANIFEST_AVB_ALGO:   "",
    AndroidShared.MANIFEST_SOURCE_TYPE: "build-output",
    AndroidShared.MANIFEST_BUILT_AT:   "2025-01-01T00:00:00Z",
    AndroidShared.MANIFEST_EGGS_VERSION: "26.2.0",
}


# ── find_eggs / ensure_eggs ───────────────────────────────────────────────────

class TestFindEggs:
    def test_returns_path_when_found(self) -> None:
        with patch("waydroid_toolkit.modules.builder.builder.shutil.which",
                   return_value="/usr/bin/eggs"):
            assert find_eggs() == "/usr/bin/eggs"

    def test_returns_none_when_missing(self) -> None:
        with patch("waydroid_toolkit.modules.builder.builder.shutil.which",
                   return_value=None):
            assert find_eggs() is None


class TestInstallEggs:
    def test_raises_when_npm_missing(self) -> None:
        with patch("waydroid_toolkit.modules.builder.builder.shutil.which",
                   return_value=None):
            with pytest.raises(RuntimeError, match="npm is required"):
                install_eggs()

    def test_raises_on_npm_failure(self) -> None:
        with patch("waydroid_toolkit.modules.builder.builder.shutil.which",
                   side_effect=lambda x: "/usr/bin/npm" if x == "npm" else None):
            with patch("waydroid_toolkit.modules.builder.builder.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="network error")
                with pytest.raises(RuntimeError, match="npm install"):
                    install_eggs()

    def test_raises_when_eggs_not_on_path_after_install(self) -> None:
        with patch("waydroid_toolkit.modules.builder.builder.shutil.which",
                   side_effect=lambda x: "/usr/bin/npm" if x == "npm" else None):
            with patch("waydroid_toolkit.modules.builder.builder.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                with pytest.raises(RuntimeError, match="binary not found"):
                    install_eggs()

    def test_returns_path_on_success(self) -> None:
        def which_side(x: str) -> str | None:
            return "/usr/bin/npm" if x == "npm" else "/usr/local/bin/eggs"

        with patch("waydroid_toolkit.modules.builder.builder.shutil.which",
                   side_effect=which_side):
            with patch("waydroid_toolkit.modules.builder.builder.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                result = install_eggs()
        assert result == "/usr/local/bin/eggs"


class TestEnsureEggs:
    def test_returns_existing_eggs(self) -> None:
        with patch("waydroid_toolkit.modules.builder.builder.find_eggs",
                   return_value="/usr/bin/eggs"):
            assert ensure_eggs() == "/usr/bin/eggs"

    def test_installs_when_missing(self) -> None:
        with patch("waydroid_toolkit.modules.builder.builder.find_eggs",
                   return_value=None):
            with patch("waydroid_toolkit.modules.builder.builder.install_eggs",
                       return_value="/usr/local/bin/eggs") as mock_install:
                result = ensure_eggs()
        assert result == "/usr/local/bin/eggs"
        mock_install.assert_called_once()


# ── read_manifest ─────────────────────────────────────────────────────────────

class TestReadManifest:
    def test_reads_valid_manifest(self, tmp_path: Path) -> None:
        p = tmp_path / "waydroid-image-manifest.json"
        p.write_text(json.dumps(_VALID_MANIFEST))
        result = read_manifest(p)
        assert result[AndroidShared.MANIFEST_ARCH] == "x86_64"
        assert result[AndroidShared.MANIFEST_VARIANT] == "waydroid"

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_manifest(tmp_path / "missing.json")

    def test_raises_on_bad_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("not json {{{")
        with pytest.raises(Exception):
            read_manifest(p)

    def test_raises_on_unsupported_version(self, tmp_path: Path) -> None:
        bad = {**_VALID_MANIFEST, AndroidShared.MANIFEST_VERSION: "99"}
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match="Unsupported manifest version"):
            read_manifest(p)

    def test_raises_on_unknown_variant(self, tmp_path: Path) -> None:
        bad = {**_VALID_MANIFEST, AndroidShared.MANIFEST_VARIANT: "fakeOS"}
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(bad))
        with pytest.raises(ValueError, match="Unknown Android variant"):
            read_manifest(p)


# ── build_android_image ───────────────────────────────────────────────────────

class TestBuildAndroidImage:
    def test_raises_on_unknown_variant(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown variant"):
            build_android_image(tmp_path, variant="fakeOS")

    def test_calls_eggs_with_correct_args(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "waydroid-image-manifest.json"
        manifest_path.write_text(json.dumps(_VALID_MANIFEST))

        with patch("waydroid_toolkit.modules.builder.builder.ensure_eggs",
                   return_value="/usr/bin/eggs"):
            with patch("waydroid_toolkit.modules.builder.builder.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = build_android_image(
                    tmp_path, variant="waydroid", arch="x86_64",
                )

        cmd = mock_run.call_args[0][0]
        assert "android" in cmd
        assert "build" in cmd
        assert "--variant" in cmd
        assert "waydroid" in cmd
        assert result[AndroidShared.MANIFEST_ARCH] == "x86_64"

    def test_avb_flag_forwarded(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "waydroid-image-manifest.json"
        manifest_path.write_text(json.dumps(_VALID_MANIFEST))

        with patch("waydroid_toolkit.modules.builder.builder.ensure_eggs",
                   return_value="/usr/bin/eggs"):
            with patch("waydroid_toolkit.modules.builder.builder.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                build_android_image(tmp_path, avb_sign=True)

        cmd = mock_run.call_args[0][0]
        assert "--avb-sign" in cmd

    def test_raises_on_eggs_failure(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.builder.builder.ensure_eggs",
                   return_value="/usr/bin/eggs"):
            with patch("waydroid_toolkit.modules.builder.builder.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                with pytest.raises(RuntimeError, match="eggs android build failed"):
                    build_android_image(tmp_path)
