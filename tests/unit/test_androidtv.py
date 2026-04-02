"""Tests for waydroid_toolkit.modules.images.androidtv."""

from __future__ import annotations

import configparser
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.images.androidtv import (
    _ATV_PROPS,
    _STANDARD_PROPS,
    apply_atv_props,
    apply_standard_props,
    get_current_props,
    is_atv_profile,
    profile_is_atv_configured,
)


# ---------------------------------------------------------------------------
# is_atv_profile
# ---------------------------------------------------------------------------

class TestIsAtvProfile:
    def test_detects_via_build_prop(self, tmp_path: Path) -> None:
        system_img = tmp_path / "system.img"
        system_img.touch()
        mock_result = MagicMock()
        mock_result.stdout = "ro.build.characteristics=tv\nro.product.model=Chromecast\n"
        with patch("subprocess.run", return_value=mock_result):
            assert is_atv_profile(tmp_path) is True

    def test_standard_build_prop_returns_false(self, tmp_path: Path) -> None:
        system_img = tmp_path / "system.img"
        system_img.touch()
        mock_result = MagicMock()
        mock_result.stdout = "ro.build.characteristics=phone\nro.product.model=Pixel\n"
        with patch("subprocess.run", return_value=mock_result):
            assert is_atv_profile(tmp_path) is False

    def test_falls_back_to_name_when_debugfs_missing(self, tmp_path: Path) -> None:
        system_img = tmp_path / "system.img"
        system_img.touch()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            # Name doesn't contain tv/atv
            assert is_atv_profile(tmp_path) is False

    def test_name_heuristic_tv(self, tmp_path: Path) -> None:
        atv_dir = tmp_path / "waydroid-tv"
        atv_dir.mkdir()
        # No system.img → goes straight to name heuristic
        assert is_atv_profile(atv_dir) is True

    def test_name_heuristic_atv(self, tmp_path: Path) -> None:
        atv_dir = tmp_path / "atv-lineage"
        atv_dir.mkdir()
        assert is_atv_profile(atv_dir) is True

    def test_name_heuristic_androidtv(self, tmp_path: Path) -> None:
        atv_dir = tmp_path / "androidtv-11"
        atv_dir.mkdir()
        assert is_atv_profile(atv_dir) is True

    def test_name_heuristic_standard(self, tmp_path: Path) -> None:
        std_dir = tmp_path / "lineage-20"
        std_dir.mkdir()
        assert is_atv_profile(std_dir) is False

    def test_timeout_falls_back_to_name(self, tmp_path: Path) -> None:
        system_img = tmp_path / "system.img"
        system_img.touch()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("debugfs", 10)):
            assert is_atv_profile(tmp_path) is False

    def test_no_system_img_uses_name(self, tmp_path: Path) -> None:
        # No system.img present
        assert is_atv_profile(tmp_path) is False


# ---------------------------------------------------------------------------
# _write_props / apply_atv_props / apply_standard_props
# ---------------------------------------------------------------------------

class TestWriteProps:
    def _make_cfg(self, tmp_path: Path, content: str = "") -> Path:
        cfg = tmp_path / "waydroid.cfg"
        cfg.write_text(content)
        return cfg

    def _read_cfg(self, cfg_path: Path) -> configparser.ConfigParser:
        parser = configparser.ConfigParser()
        parser.read(cfg_path)
        return parser

    def test_apply_atv_props_writes_all_keys(self, tmp_path: Path) -> None:
        cfg = self._make_cfg(tmp_path)
        with patch("subprocess.run") as mock_run:
            # Simulate sudo mv by actually moving the tmp file
            def fake_run(cmd, **_kwargs):
                if cmd[0] == "sudo" and cmd[1] == "mv":
                    Path(cmd[2]).rename(cmd[3])
                return MagicMock(returncode=0)
            mock_run.side_effect = fake_run
            apply_atv_props(cfg_path=cfg)

        parser = self._read_cfg(cfg)
        assert "properties" in parser
        for key, value in _ATV_PROPS.items():
            assert parser["properties"].get(key) == value

    def test_apply_standard_props_writes_all_keys(self, tmp_path: Path) -> None:
        cfg = self._make_cfg(tmp_path)
        with patch("subprocess.run") as mock_run:
            def fake_run(cmd, **_kwargs):
                if cmd[0] == "sudo" and cmd[1] == "mv":
                    Path(cmd[2]).rename(cmd[3])
                return MagicMock(returncode=0)
            mock_run.side_effect = fake_run
            apply_standard_props(cfg_path=cfg)

        parser = self._read_cfg(cfg)
        assert "properties" in parser
        for key, value in _STANDARD_PROPS.items():
            assert parser["properties"].get(key) == value

    def test_preserves_existing_sections(self, tmp_path: Path) -> None:
        existing = "[waydroid]\nname = test\n"
        cfg = self._make_cfg(tmp_path, existing)
        with patch("subprocess.run") as mock_run:
            def fake_run(cmd, **_kwargs):
                if cmd[0] == "sudo" and cmd[1] == "mv":
                    Path(cmd[2]).rename(cmd[3])
                return MagicMock(returncode=0)
            mock_run.side_effect = fake_run
            apply_atv_props(cfg_path=cfg)

        parser = self._read_cfg(cfg)
        assert parser["waydroid"]["name"] == "test"
        assert parser["properties"]["ro.build.characteristics"] == "tv"

    def test_creates_properties_section_if_missing(self, tmp_path: Path) -> None:
        cfg = self._make_cfg(tmp_path, "[waydroid]\nname = x\n")
        with patch("subprocess.run") as mock_run:
            def fake_run(cmd, **_kwargs):
                if cmd[0] == "sudo" and cmd[1] == "mv":
                    Path(cmd[2]).rename(cmd[3])
                return MagicMock(returncode=0)
            mock_run.side_effect = fake_run
            apply_atv_props(cfg_path=cfg)

        parser = self._read_cfg(cfg)
        assert "properties" in parser

    def test_cfg_does_not_exist_creates_it(self, tmp_path: Path) -> None:
        cfg = tmp_path / "nonexistent.cfg"
        with patch("subprocess.run") as mock_run:
            def fake_run(cmd, **_kwargs):
                if cmd[0] == "sudo" and cmd[1] == "mv":
                    Path(cmd[2]).rename(cmd[3])
                return MagicMock(returncode=0)
            mock_run.side_effect = fake_run
            apply_atv_props(cfg_path=cfg)

        assert cfg.exists()
        parser = self._read_cfg(cfg)
        assert parser["properties"]["persist.waydroid.width"] == "1920"


# ---------------------------------------------------------------------------
# get_current_props
# ---------------------------------------------------------------------------

class TestGetCurrentProps:
    def test_returns_empty_strings_when_no_cfg(self, tmp_path: Path) -> None:
        cfg = tmp_path / "missing.cfg"
        props = get_current_props(cfg_path=cfg)
        assert all(v == "" for v in props.values())

    def test_returns_values_from_cfg(self, tmp_path: Path) -> None:
        cfg = tmp_path / "waydroid.cfg"
        cfg.write_text("[properties]\nro.build.characteristics = tv\n")
        props = get_current_props(cfg_path=cfg)
        assert props["ro.build.characteristics"] == "tv"

    def test_returns_all_atv_keys(self, tmp_path: Path) -> None:
        cfg = tmp_path / "waydroid.cfg"
        cfg.write_text("")
        props = get_current_props(cfg_path=cfg)
        assert set(props.keys()) == set(_ATV_PROPS.keys())


# ---------------------------------------------------------------------------
# profile_is_atv_configured
# ---------------------------------------------------------------------------

class TestProfileIsAtvConfigured:
    def test_true_when_tv_characteristic_set(self, tmp_path: Path) -> None:
        cfg = tmp_path / "waydroid.cfg"
        cfg.write_text("[properties]\nro.build.characteristics = tv\n")
        assert profile_is_atv_configured(cfg_path=cfg) is True

    def test_false_when_characteristic_is_default(self, tmp_path: Path) -> None:
        cfg = tmp_path / "waydroid.cfg"
        cfg.write_text("[properties]\nro.build.characteristics = default\n")
        assert profile_is_atv_configured(cfg_path=cfg) is False

    def test_false_when_no_cfg(self, tmp_path: Path) -> None:
        cfg = tmp_path / "missing.cfg"
        assert profile_is_atv_configured(cfg_path=cfg) is False
