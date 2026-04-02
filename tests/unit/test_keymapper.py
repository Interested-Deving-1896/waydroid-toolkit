"""Tests for the KeyMapper extension."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.extensions.keymapper import (
    KeyMapperExtension,
    _apk_installed,
    _daemon_on_path,
    _remove_systemd_unit,
    _write_systemd_unit,
)

# ── Meta ──────────────────────────────────────────────────────────────────────

class TestMeta:
    def test_id(self) -> None:
        assert KeyMapperExtension().meta.id == "keymapper"

    def test_does_not_require_root(self) -> None:
        assert KeyMapperExtension().meta.requires_root is False

    def test_registered(self) -> None:
        from waydroid_toolkit.modules.extensions import get
        assert get("keymapper").meta.id == "keymapper"


# ── is_installed ──────────────────────────────────────────────────────────────

class TestIsInstalled:
    def test_true_when_daemon_and_apk_present(self) -> None:
        ext = KeyMapperExtension()
        with patch("waydroid_toolkit.modules.extensions.keymapper._daemon_on_path",
                   return_value=True), \
             patch("waydroid_toolkit.modules.extensions.keymapper._apk_installed",
                   return_value=True):
            assert ext.is_installed() is True

    def test_false_when_daemon_missing(self) -> None:
        ext = KeyMapperExtension()
        with patch("waydroid_toolkit.modules.extensions.keymapper._daemon_on_path",
                   return_value=False), \
             patch("waydroid_toolkit.modules.extensions.keymapper._apk_installed",
                   return_value=True):
            assert ext.is_installed() is False

    def test_false_when_apk_missing(self) -> None:
        ext = KeyMapperExtension()
        with patch("waydroid_toolkit.modules.extensions.keymapper._daemon_on_path",
                   return_value=True), \
             patch("waydroid_toolkit.modules.extensions.keymapper._apk_installed",
                   return_value=False):
            assert ext.is_installed() is False


# ── _daemon_on_path ───────────────────────────────────────────────────────────

class TestDaemonOnPath:
    def test_true_when_binary_found(self) -> None:
        with patch("shutil.which", return_value="/usr/local/bin/waydroid-input-bridge"):
            assert _daemon_on_path() is True

    def test_false_when_binary_missing(self) -> None:
        with patch("shutil.which", return_value=None):
            assert _daemon_on_path() is False


# ── _apk_installed ────────────────────────────────────────────────────────────

class TestApkInstalled:
    def test_true_when_package_listed(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "package:id.waydroid.inputbridge\n"
        with patch("subprocess.run", return_value=mock_result):
            assert _apk_installed() is True

    def test_false_when_package_absent(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            assert _apk_installed() is False

    def test_false_on_exception(self) -> None:
        with patch("subprocess.run", side_effect=Exception("adb not found")):
            assert _apk_installed() is False


# ── _write_systemd_unit ───────────────────────────────────────────────────────

class TestWriteSystemdUnit:
    def test_creates_unit_file(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.extensions.keymapper._SYSTEMD_USER_DIR",
                   tmp_path), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            _write_systemd_unit()
        unit = tmp_path / "waydroid-input-bridge.service"
        assert unit.exists()
        assert "ExecStart=waydroid-input-bridge" in unit.read_text()

    def test_calls_systemctl_enable(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.extensions.keymapper._SYSTEMD_USER_DIR",
                   tmp_path), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            _write_systemd_unit()
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("enable" in c for c in cmds)


# ── _remove_systemd_unit ──────────────────────────────────────────────────────

class TestRemoveSystemdUnit:
    def test_removes_unit_file(self, tmp_path: Path) -> None:
        unit = tmp_path / "waydroid-input-bridge.service"
        unit.write_text("[Unit]\n")
        with patch("waydroid_toolkit.modules.extensions.keymapper._SYSTEMD_USER_DIR",
                   tmp_path), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)):
            _remove_systemd_unit()
        assert not unit.exists()

    def test_calls_systemctl_disable(self, tmp_path: Path) -> None:
        unit = tmp_path / "waydroid-input-bridge.service"
        unit.write_text("[Unit]\n")
        with patch("waydroid_toolkit.modules.extensions.keymapper._SYSTEMD_USER_DIR",
                   tmp_path), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            _remove_systemd_unit()
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("disable" in c for c in cmds)


# ── install ───────────────────────────────────────────────────────────────────

class TestInstall:
    def _mock_urlopen(self, content: bytes = b"fake-apk") -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.read.return_value = content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_installs_daemon_apk_and_unit(self, tmp_path: Path) -> None:
        ext = KeyMapperExtension()
        messages: list[str] = []

        with patch("waydroid_toolkit.modules.extensions.keymapper._pip_install") as mock_pip, \
             patch("urllib.request.urlopen", return_value=self._mock_urlopen()), \
             patch("waydroid_toolkit.modules.extensions.keymapper._CACHE_DIR", tmp_path), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)), \
             patch("waydroid_toolkit.modules.extensions.keymapper._write_systemd_unit") as mock_unit:
            ext.install(progress=messages.append)

        mock_pip.assert_called_once()
        mock_unit.assert_called_once()
        assert messages

    def test_raises_when_adb_missing(self, tmp_path: Path) -> None:
        ext = KeyMapperExtension()

        def _run_side_effect(cmd, **kwargs):
            if "adb" in cmd and "install" in cmd:
                raise FileNotFoundError("adb not found")
            return MagicMock(returncode=0)

        with patch("waydroid_toolkit.modules.extensions.keymapper._pip_install"), \
             patch("urllib.request.urlopen", return_value=self._mock_urlopen()), \
             patch("waydroid_toolkit.modules.extensions.keymapper._CACHE_DIR", tmp_path), \
             patch("subprocess.run", side_effect=_run_side_effect):
            with pytest.raises(RuntimeError, match="adb not found"):
                ext.install()

    def test_raises_when_adb_install_fails(self, tmp_path: Path) -> None:
        ext = KeyMapperExtension()

        def _run_side_effect(cmd, **kwargs):
            if "install" in cmd and "adb" in cmd[0]:
                raise subprocess.CalledProcessError(1, cmd)
            return MagicMock(returncode=0)

        with patch("waydroid_toolkit.modules.extensions.keymapper._pip_install"), \
             patch("urllib.request.urlopen", return_value=self._mock_urlopen()), \
             patch("waydroid_toolkit.modules.extensions.keymapper._CACHE_DIR", tmp_path), \
             patch("subprocess.run", side_effect=_run_side_effect):
            with pytest.raises(RuntimeError, match="APK installation failed"):
                ext.install()


# ── uninstall ─────────────────────────────────────────────────────────────────

class TestUninstall:
    def test_removes_unit_uninstalls_apk_and_daemon(self) -> None:
        ext = KeyMapperExtension()
        messages: list[str] = []

        with patch("waydroid_toolkit.modules.extensions.keymapper._remove_systemd_unit") as mock_unit, \
             patch("subprocess.run", return_value=MagicMock(returncode=0)), \
             patch("waydroid_toolkit.modules.extensions.keymapper._pip_uninstall") as mock_pip:
            ext.uninstall(progress=messages.append)

        mock_unit.assert_called_once()
        mock_pip.assert_called_once()
        assert messages
