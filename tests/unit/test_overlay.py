"""Tests for overlay filesystem helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from waydroid_toolkit.utils.overlay import (
    install_file,
    is_overlay_enabled,
    overlay_path,
    remove_file,
)


def test_overlay_path_strips_leading_slash() -> None:
    result = overlay_path("/system/lib/libfoo.so")
    assert not str(result).startswith("//")
    assert result.parts[-3:] == ("system", "lib", "libfoo.so")


def test_overlay_path_no_leading_slash() -> None:
    result = overlay_path("system/lib/libfoo.so")
    assert result.parts[-3:] == ("system", "lib", "libfoo.so")


def test_install_file(tmp_path: Path) -> None:
    src = tmp_path / "libfoo.so"
    src.write_bytes(b"\x7fELF")

    fake_overlay = tmp_path / "overlay"

    with patch("waydroid_toolkit.utils.overlay._OVERLAY_ROOT", fake_overlay):
        dest = install_file(src, "/system/lib/libfoo.so")

    assert dest.exists()
    assert dest.read_bytes() == b"\x7fELF"


def test_remove_file_existing(tmp_path: Path) -> None:
    fake_overlay = tmp_path / "overlay"
    target = fake_overlay / "system" / "lib" / "libfoo.so"
    target.parent.mkdir(parents=True)
    target.touch()

    with patch("waydroid_toolkit.utils.overlay._OVERLAY_ROOT", fake_overlay):
        result = remove_file("/system/lib/libfoo.so")

    assert result is True
    assert not target.exists()


def test_remove_file_nonexistent(tmp_path: Path) -> None:
    fake_overlay = tmp_path / "overlay"
    with patch("waydroid_toolkit.utils.overlay._OVERLAY_ROOT", fake_overlay):
        result = remove_file("/system/lib/nonexistent.so")
    assert result is False


def test_install_file_creates_parent_dirs(tmp_path: Path) -> None:
    src = tmp_path / "libbar.so"
    src.write_bytes(b"\x7fELF")
    fake_overlay = tmp_path / "overlay"
    # Deep nested path — parent dirs must be created
    with patch("waydroid_toolkit.utils.overlay._OVERLAY_ROOT", fake_overlay):
        dest = install_file(src, "/system/vendor/lib64/libbar.so")
    assert dest.exists()
    assert dest.read_bytes() == b"\x7fELF"


def test_overlay_path_root_maps_correctly() -> None:
    result = overlay_path("/")
    # Root maps to the overlay root itself
    from waydroid_toolkit.utils.overlay import _OVERLAY_ROOT
    assert result == _OVERLAY_ROOT


# ── is_overlay_enabled ────────────────────────────────────────────────────────

class TestIsOverlayEnabled:
    # WaydroidConfig is imported lazily inside is_overlay_enabled(); patch at source.
    _PATCH = "waydroid_toolkit.core.waydroid.WaydroidConfig.load"

    def test_true_when_mount_overlays_enabled(self) -> None:
        from waydroid_toolkit.core.waydroid import WaydroidConfig
        with patch(self._PATCH, return_value=WaydroidConfig(mount_overlays=True)):
            assert is_overlay_enabled() is True

    def test_false_when_mount_overlays_disabled(self) -> None:
        from waydroid_toolkit.core.waydroid import WaydroidConfig
        with patch(self._PATCH, return_value=WaydroidConfig(mount_overlays=False)):
            assert is_overlay_enabled() is False
