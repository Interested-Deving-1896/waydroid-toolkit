"""Tests for the maintenance tools module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.maintenance.tools import (
    DEFAULT_BLOAT,
    clear_app_data,
    debloat,
    freeze_app,
    get_device_info,
    get_logcat,
    launch_app,
    pull_file,
    push_file,
    record_screen,
    reset_display,
    set_density,
    set_resolution,
    stream_logcat,
    take_screenshot,
    unfreeze_app,
)

# ── Display settings ──────────────────────────────────────────────────────────

class TestDisplaySettings:
    def test_set_resolution_calls_waydroid_prop(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.run_waydroid") as mock_wd:
            set_resolution(1920, 1080)
        calls = [" ".join(c[0]) for c in mock_wd.call_args_list]
        assert any("1920" in c for c in calls)
        assert any("1080" in c for c in calls)

    def test_set_resolution_sets_both_dimensions(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.run_waydroid") as mock_wd:
            set_resolution(2560, 1440)
        assert mock_wd.call_count == 2

    def test_set_density_calls_waydroid_prop(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.run_waydroid") as mock_wd:
            set_density(240)
        calls = [" ".join(c[0]) for c in mock_wd.call_args_list]
        assert any("240" in c for c in calls)

    def test_reset_display_clears_all_three_props(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.run_waydroid") as mock_wd:
            reset_display()
        assert mock_wd.call_count == 3
        all_args = " ".join(" ".join(c[0]) for c in mock_wd.call_args_list)
        assert "width" in all_args
        assert "height" in all_args
        assert "density" in all_args


# ── Device info ───────────────────────────────────────────────────────────────

class TestGetDeviceInfo:
    def test_returns_dict_with_expected_keys(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0, stdout="value\n")
            info = get_device_info()
        assert "android_version" in info
        assert "sdk_version" in info
        assert "product_model" in info
        assert "cpu_abi" in info

    def test_unavailable_on_adb_failure(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=1, stdout="")
            info = get_device_info()
        assert all(v == "unavailable" for v in info.values())

    def test_strips_whitespace_from_values(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0, stdout="  13  \n")
            info = get_device_info()
        assert all(v == "13" for v in info.values())


# ── Screenshot / screen record ────────────────────────────────────────────────

class TestScreenshot:
    def test_delegates_to_adb_screenshot(self, tmp_path: Path) -> None:
        dest = tmp_path / "shot.png"
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.screenshot",
                   return_value=dest) as mock_ss:
            result = take_screenshot(dest)
        mock_ss.assert_called_once_with(dest)
        assert result == dest


class TestRecordScreen:
    def test_returns_dest_path(self, tmp_path: Path) -> None:
        dest = tmp_path / "rec.mp4"
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0)
            with patch("waydroid_toolkit.modules.maintenance.tools.adb.pull") as mock_pull:
                mock_pull.return_value = MagicMock(returncode=0)
                result = record_screen(dest=dest, duration_seconds=5)
        assert result == dest

    def test_uses_default_path_when_none(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0)
            with patch("waydroid_toolkit.modules.maintenance.tools.adb.pull") as mock_pull:
                mock_pull.return_value = MagicMock(returncode=0)
                with patch("waydroid_toolkit.modules.maintenance.tools.Path.home",
                           return_value=tmp_path):
                    result = record_screen(duration_seconds=5)
        assert result.suffix == ".mp4"
        assert "recording_" in result.name


# ── File transfer ─────────────────────────────────────────────────────────────

class TestFileTransfer:
    def test_push_file_succeeds(self, tmp_path: Path) -> None:
        src = tmp_path / "file.txt"
        src.write_text("data")
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.push") as mock_push:
            mock_push.return_value = MagicMock(returncode=0)
            push_file(src, "/sdcard/file.txt")
        mock_push.assert_called_once_with(src, "/sdcard/file.txt")

    def test_push_file_raises_on_failure(self, tmp_path: Path) -> None:
        src = tmp_path / "file.txt"
        src.write_text("data")
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.push") as mock_push:
            mock_push.return_value = MagicMock(returncode=1, stderr="error")
            with pytest.raises(RuntimeError, match="Push failed"):
                push_file(src, "/sdcard/file.txt")

    def test_pull_file_succeeds(self, tmp_path: Path) -> None:
        dest = tmp_path / "out.txt"
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.pull") as mock_pull:
            mock_pull.return_value = MagicMock(returncode=0)
            pull_file("/sdcard/file.txt", dest)
        mock_pull.assert_called_once_with("/sdcard/file.txt", dest)

    def test_pull_file_raises_on_failure(self, tmp_path: Path) -> None:
        dest = tmp_path / "out.txt"
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.pull") as mock_pull:
            mock_pull.return_value = MagicMock(returncode=1, stderr="error")
            with pytest.raises(RuntimeError, match="Pull failed"):
                pull_file("/sdcard/file.txt", dest)


# ── Logcat streaming ──────────────────────────────────────────────────────────

class TestStreamLogcat:
    def test_yields_lines_from_proc(self) -> None:
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["line one\n", "line two\n"])
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.logcat",
                   return_value=mock_proc):
            lines = list(stream_logcat())
        assert lines == ["line one", "line two"]
        mock_proc.terminate.assert_called_once()

    def test_terminates_proc_on_exception(self) -> None:
        mock_proc = MagicMock()

        def _bad_iter():
            yield "line\n"
            raise RuntimeError("stream error")

        mock_proc.stdout = _bad_iter()
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.logcat",
                   return_value=mock_proc):
            with pytest.raises(RuntimeError):
                list(stream_logcat())
        mock_proc.terminate.assert_called_once()

    def test_passes_tag_and_errors_only(self) -> None:
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.logcat",
                   return_value=mock_proc) as mock_logcat:
            list(stream_logcat(tag="MyTag", errors_only=True))
        mock_logcat.assert_called_once_with(tag="MyTag", errors_only=True)


class TestGetLogcat:
    def _mock_logcat(self, lines: list[str]) -> MagicMock:
        proc = MagicMock()
        proc.stdout = iter(line + "\n" for line in lines)
        return proc

    def test_returns_joined_string(self) -> None:
        proc = self._mock_logcat(["alpha", "beta", "gamma"])
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.logcat",
                   return_value=proc):
            result = get_logcat()
        assert result == "alpha\nbeta\ngamma"

    def test_respects_lines_limit(self) -> None:
        proc = self._mock_logcat([f"line{i}" for i in range(100)])
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.logcat",
                   return_value=proc):
            result = get_logcat(lines=10)
        assert result.count("\n") == 9  # 10 lines → 9 newlines
        assert result.startswith("line0")
        assert result.endswith("line9")

    def test_empty_output_returns_empty_string(self) -> None:
        proc = self._mock_logcat([])
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.logcat",
                   return_value=proc):
            result = get_logcat()
        assert result == ""

    def test_passes_tag_and_errors_only(self) -> None:
        proc = self._mock_logcat([])
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.logcat",
                   return_value=proc) as mock_logcat:
            get_logcat(tag="WDT", errors_only=True)
        mock_logcat.assert_called_once_with(tag="WDT", errors_only=True)


# ── App management ────────────────────────────────────────────────────────────

class TestAppManagement:
    def test_freeze_app_calls_pm_disable(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0, stdout="")
            freeze_app("com.example.app")
        cmd = mock_shell.call_args[0][0]
        assert "disable" in cmd
        assert "com.example.app" in cmd

    def test_freeze_app_raises_on_failure(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=1, stderr="error")
            with pytest.raises(RuntimeError, match="freeze"):
                freeze_app("com.example.app")

    def test_unfreeze_app_calls_pm_enable(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0, stdout="")
            unfreeze_app("com.example.app")
        cmd = mock_shell.call_args[0][0]
        assert "enable" in cmd
        assert "com.example.app" in cmd

    def test_unfreeze_app_raises_on_failure(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=1, stderr="error")
            with pytest.raises(RuntimeError, match="unfreeze"):
                unfreeze_app("com.example.app")

    def test_clear_app_data_calls_pm_clear(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0)
            clear_app_data("com.example.app")
        cmd = mock_shell.call_args[0][0]
        assert "clear" in cmd
        assert "com.example.app" in cmd

    def test_clear_app_data_cache_only(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0)
            clear_app_data("com.example.app", cache_only=True)
        cmd = mock_shell.call_args[0][0]
        assert "trim-caches" in cmd

    def test_launch_app_calls_monkey(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0)
            launch_app("com.example.app")
        cmd = mock_shell.call_args[0][0]
        assert "monkey" in cmd
        assert "com.example.app" in cmd


# ── Debloater ─────────────────────────────────────────────────────────────────

class TestDebloat:
    def test_removes_listed_packages(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0, stdout="Success")
            removed = debloat(["com.android.email", "com.android.calendar"])
        assert "com.android.email" in removed
        assert "com.android.calendar" in removed

    def test_skips_failed_packages(self) -> None:
        def _side_effect(cmd: str) -> MagicMock:
            if "email" in cmd:
                return MagicMock(returncode=1, stdout="Failure")
            return MagicMock(returncode=0, stdout="Success")

        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell",
                   side_effect=_side_effect):
            removed = debloat(["com.android.email", "com.android.calendar"])
        assert "com.android.email" not in removed
        assert "com.android.calendar" in removed

    def test_uses_default_bloat_list_when_none_given(self) -> None:
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0, stdout="Success")
            removed = debloat()
        assert len(removed) == len(DEFAULT_BLOAT)

    def test_calls_progress(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.maintenance.tools.adb.shell") as mock_shell:
            mock_shell.return_value = MagicMock(returncode=0, stdout="Success")
            debloat(["com.android.email"], progress=messages.append)
        assert len(messages) == 1
        assert "com.android.email" in messages[0]
