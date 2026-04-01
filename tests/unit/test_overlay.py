"""Tests for overlay filesystem helpers."""

from pathlib import Path
from unittest.mock import patch

from waydroid_toolkit.utils.overlay import overlay_path, install_file, remove_file


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
