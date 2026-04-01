"""Tests for the image profile manager."""

from pathlib import Path

from waydroid_toolkit.modules.images.manager import ImageProfile, scan_profiles


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
