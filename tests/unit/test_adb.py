"""Tests for the ADB interface module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from waydroid_toolkit.core.adb import (
    connect,
    disconnect,
    install_apk,
    is_available,
    is_connected,
    list_packages,
    logcat,
    pull,
    push,
    screenshot,
    shell,
    uninstall_package,
)

_TARGET = "192.168.250.1:5555"


# ── is_available ──────────────────────────────────────────────────────────────

class TestIsAvailable:
    def test_true_when_adb_found(self) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert is_available() is True

    def test_false_when_adb_missing(self) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run", side_effect=FileNotFoundError):
            assert is_available() is False


# ── connect ───────────────────────────────────────────────────────────────────

class TestConnect:
    """connect() checks session state before each attempt."""

    def _running(self):
        from waydroid_toolkit.core.waydroid import SessionState
        return SessionState.RUNNING

    def _stopped(self):
        from waydroid_toolkit.core.waydroid import SessionState
        return SessionState.STOPPED

    # get_session_state is imported lazily inside connect(); patch at source.
    _GSS = "waydroid_toolkit.core.waydroid.get_session_state"

    def test_returns_true_on_connected_output(self) -> None:
        with patch(self._GSS, return_value=self._running()):
            with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
                with patch("waydroid_toolkit.core.adb.time.sleep"):
                    mock_run.return_value = MagicMock(returncode=0, stdout="connected to 192.168.250.1:5555")
                    assert connect(retries=1) is True

    def test_returns_false_after_all_retries_fail(self) -> None:
        with patch(self._GSS, return_value=self._running()):
            with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
                with patch("waydroid_toolkit.core.adb.time.sleep"):
                    mock_run.return_value = MagicMock(returncode=1, stdout="failed")
                    assert connect(retries=3, delay=0) is False
            assert mock_run.call_count == 3

    def test_skips_adb_when_session_not_running(self) -> None:
        with patch(self._GSS, return_value=self._stopped()):
            with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
                with patch("waydroid_toolkit.core.adb.time.sleep"):
                    result = connect(retries=2, delay=0)
        assert result is False
        # adb connect should never be called when session is stopped
        assert not any("connect" in " ".join(c[0][0]) for c in mock_run.call_args_list)

    def test_succeeds_on_second_retry(self) -> None:
        responses = [
            MagicMock(returncode=1, stdout="failed"),
            MagicMock(returncode=0, stdout="connected to 192.168.250.1:5555"),
        ]
        with patch(self._GSS, return_value=self._running()):
            with patch("waydroid_toolkit.core.adb.subprocess.run", side_effect=responses):
                with patch("waydroid_toolkit.core.adb.time.sleep"):
                    assert connect(retries=3, delay=0) is True

    def test_already_connected_output_counts_as_success(self) -> None:
        with patch(self._GSS, return_value=self._running()):
            with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
                with patch("waydroid_toolkit.core.adb.time.sleep"):
                    mock_run.return_value = MagicMock(returncode=0, stdout="already connected to 192.168.250.1:5555")
                    assert connect(retries=1) is True

    def test_sleeps_between_retries(self) -> None:
        with patch(self._GSS, return_value=self._running()):
            with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
                with patch("waydroid_toolkit.core.adb.time.sleep") as mock_sleep:
                    mock_run.return_value = MagicMock(returncode=1, stdout="failed")
                    connect(retries=2, delay=1.5)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(1.5)


# ── disconnect ────────────────────────────────────────────────────────────────

class TestDisconnect:
    def test_calls_adb_disconnect(self) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            disconnect()
        cmd = " ".join(mock_run.call_args[0][0])
        assert "disconnect" in cmd
        assert _TARGET in cmd


# ── is_connected ──────────────────────────────────────────────────────────────

class TestIsConnected:
    def test_true_when_target_in_devices(self) -> None:
        output = f"List of devices attached\n{_TARGET}\tdevice\n"
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output)
            assert is_connected() is True

    def test_false_when_target_absent(self) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="List of devices attached\n")
            assert is_connected() is False


# ── shell ─────────────────────────────────────────────────────────────────────

class TestShell:
    def test_passes_command_to_adb_shell(self) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="12")
            shell("getprop ro.build.version.sdk")
        cmd = mock_run.call_args[0][0]
        assert "shell" in cmd
        assert "getprop" in " ".join(cmd)

    def test_uses_waydroid_target(self) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            shell("true")
        cmd = mock_run.call_args[0][0]
        assert _TARGET in cmd


# ── install_apk ───────────────────────────────────────────────────────────────

class TestInstallApk:
    def test_calls_adb_install(self, tmp_path: Path) -> None:
        apk = tmp_path / "app.apk"
        apk.write_bytes(b"PK")
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Success")
            install_apk(apk)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "install" in cmd
        assert str(apk) in cmd

    def test_passes_replace_flag(self, tmp_path: Path) -> None:
        apk = tmp_path / "app.apk"
        apk.write_bytes(b"PK")
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Success")
            install_apk(apk)
        cmd = mock_run.call_args[0][0]
        assert "-r" in cmd


# ── uninstall_package ─────────────────────────────────────────────────────────

class TestUninstallPackage:
    def test_calls_adb_uninstall(self) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Success")
            uninstall_package("com.example.app")
        cmd = " ".join(mock_run.call_args[0][0])
        assert "uninstall" in cmd
        assert "com.example.app" in cmd


# ── list_packages ─────────────────────────────────────────────────────────────

class TestListPackages:
    def test_parses_package_lines(self) -> None:
        output = "package:com.example.one\npackage:com.example.two\n"
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output)
            result = list_packages()
        assert result == ["com.example.one", "com.example.two"]

    def test_ignores_non_package_lines(self) -> None:
        output = "package:com.example.app\nWarning: some warning\n"
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=output)
            result = list_packages()
        assert result == ["com.example.app"]

    def test_returns_empty_on_no_output(self) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            result = list_packages()
        assert result == []


# ── push / pull ───────────────────────────────────────────────────────────────

class TestPushPull:
    def test_push_includes_source_and_dest(self, tmp_path: Path) -> None:
        src = tmp_path / "file.txt"
        src.write_text("data")
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            push(src, "/sdcard/file.txt")
        cmd = " ".join(mock_run.call_args[0][0])
        assert "push" in cmd
        assert str(src) in cmd
        assert "/sdcard/file.txt" in cmd

    def test_pull_includes_source_and_dest(self, tmp_path: Path) -> None:
        dest = tmp_path / "out.txt"
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            pull("/sdcard/file.txt", dest)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "pull" in cmd
        assert "/sdcard/file.txt" in cmd
        assert str(dest) in cmd


# ── screenshot ────────────────────────────────────────────────────────────────

class TestScreenshot:
    def test_returns_dest_path(self, tmp_path: Path) -> None:
        dest = tmp_path / "shot.png"
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            # Patch open so we don't actually write
            with patch("builtins.open", MagicMock()):
                result = screenshot(dest)
        assert result == dest

    def test_uses_default_path_when_dest_none(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.core.adb.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("waydroid_toolkit.core.adb.Path.home", return_value=tmp_path):
                with patch("builtins.open", MagicMock()):
                    result = screenshot(None)
        assert result.suffix == ".png"
        assert "screenshot_" in result.name


# ── logcat ────────────────────────────────────────────────────────────────────

class TestLogcat:
    def test_returns_popen_handle(self) -> None:
        mock_proc = MagicMock(spec=subprocess.Popen)
        with patch("waydroid_toolkit.core.adb.subprocess.Popen", return_value=mock_proc):
            result = logcat()
        assert result is mock_proc

    def test_errors_only_flag(self) -> None:
        mock_proc = MagicMock(spec=subprocess.Popen)
        with patch("waydroid_toolkit.core.adb.subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_proc
            logcat(errors_only=True)
        cmd = " ".join(mock_popen.call_args[0][0])
        assert "*:E" in cmd

    def test_tag_filter(self) -> None:
        mock_proc = MagicMock(spec=subprocess.Popen)
        with patch("waydroid_toolkit.core.adb.subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_proc
            logcat(tag="ActivityManager")
        cmd = " ".join(mock_popen.call_args[0][0])
        assert "ActivityManager:V" in cmd
        assert "*:S" in cmd

    def test_no_filter_by_default(self) -> None:
        mock_proc = MagicMock(spec=subprocess.Popen)
        with patch("waydroid_toolkit.core.adb.subprocess.Popen") as mock_popen:
            mock_popen.return_value = mock_proc
            logcat()
        cmd = mock_popen.call_args[0][0]
        # No extra filter args beyond the base command
        assert "*:E" not in " ".join(cmd)
        assert "*:S" not in " ".join(cmd)
