"""Unit tests for waydroid_toolkit.modules.streaming.stream"""

from __future__ import annotations

import os
import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.streaming.stream import (
    StreamConfig,
    StreamSession,
    _build_scrcpy_cmd,
    check_dependencies,
    load_pid,
    save_pid,
)


# ── StreamConfig defaults ─────────────────────────────────────────────────────

class TestStreamConfig:
    def test_defaults(self):
        cfg = StreamConfig()
        assert cfg.bitrate == "8M"
        assert cfg.max_fps == 60
        assert cfg.video_codec == "h264"
        assert cfg.audio is True
        assert cfg.keyboard is True
        assert cfg.mouse is True
        assert cfg.gamepad is False
        assert cfg.fullscreen is False
        assert cfg.record_file == ""

    def test_custom_values(self):
        cfg = StreamConfig(bitrate="4M", max_fps=30, video_codec="h265")
        assert cfg.bitrate == "4M"
        assert cfg.max_fps == 30
        assert cfg.video_codec == "h265"


# ── _build_scrcpy_cmd ─────────────────────────────────────────────────────────

class TestBuildScrcpyCmd:
    def _cfg(self, **kwargs) -> StreamConfig:
        return StreamConfig(**kwargs)

    def test_basic_command(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(self._cfg(), "192.168.240.112:5555")
        assert cmd[0] == "scrcpy"
        assert "--serial" in cmd
        assert "192.168.240.112:5555" in cmd
        assert "--video-bit-rate" in cmd
        assert "8M" in cmd

    def test_no_audio_flag(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(self._cfg(audio=False), "serial")
        assert "--no-audio" in cmd

    def test_fullscreen_flag(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(self._cfg(fullscreen=True), "serial")
        assert "--fullscreen" in cmd

    def test_record_flag(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(self._cfg(record_file="out.mp4"), "serial")
        assert "--record" in cmd
        assert "out.mp4" in cmd

    def test_max_size_included_when_nonzero(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(self._cfg(max_size=1280), "serial")
        assert "--max-size" in cmd
        assert "1280" in cmd

    def test_max_size_omitted_when_zero(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(self._cfg(max_size=0), "serial")
        assert "--max-size" not in cmd

    def test_non_h264_codec_included(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(self._cfg(video_codec="h265"), "serial")
        assert "--video-codec" in cmd
        assert "h265" in cmd

    def test_h264_codec_not_repeated(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(self._cfg(video_codec="h264"), "serial")
        assert "--video-codec" not in cmd

    def test_extra_args_appended(self):
        with patch("shutil.which", return_value="/usr/bin/scrcpy"):
            cmd = _build_scrcpy_cmd(
                self._cfg(extra_args=["--no-clipboard"]), "serial"
            )
        assert "--no-clipboard" in cmd

    def test_scrcpy_not_found_raises(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="scrcpy not found"):
                _build_scrcpy_cmd(self._cfg(), "serial")


# ── StreamSession ─────────────────────────────────────────────────────────────

class TestStreamSession:
    def test_is_running_true_when_process_alive(self):
        session = StreamSession(config=StreamConfig(), pid=os.getpid(), adb_serial="serial")
        assert session.is_running() is True

    def test_is_running_false_when_process_gone(self):
        session = StreamSession(config=StreamConfig(), pid=999999999, adb_serial="serial")
        assert session.is_running() is False

    def test_stop_sends_sigterm(self):
        with patch("os.kill") as mock_kill:
            session = StreamSession(config=StreamConfig(), pid=12345, adb_serial="serial")
            session.stop()
        mock_kill.assert_called_once_with(12345, signal.SIGTERM)

    def test_stop_ignores_missing_process(self):
        with patch("os.kill", side_effect=ProcessLookupError):
            session = StreamSession(config=StreamConfig(), pid=12345, adb_serial="serial")
            session.stop()  # should not raise


# ── check_dependencies ────────────────────────────────────────────────────────

class TestCheckDependencies:
    def test_all_present(self):
        with patch("shutil.which", return_value="/usr/bin/tool"):
            deps = check_dependencies()
        assert deps["adb"] is True
        assert deps["scrcpy"] is True

    def test_none_present(self):
        with patch("shutil.which", return_value=None):
            deps = check_dependencies()
        assert deps["adb"] is False
        assert deps["scrcpy"] is False

    def test_partial(self):
        def _which(name):
            return "/usr/bin/adb" if name == "adb" else None

        with patch("shutil.which", side_effect=_which):
            deps = check_dependencies()
        assert deps["adb"] is True
        assert deps["scrcpy"] is False


# ── save_pid / load_pid ───────────────────────────────────────────────────────

class TestPidFile:
    def test_round_trip(self, tmp_path):
        pid_file = tmp_path / "stream.pid"
        session = StreamSession(config=StreamConfig(), pid=42, adb_serial="serial")
        save_pid(session, pid_file)
        assert load_pid(pid_file) == 42

    def test_load_missing_returns_none(self, tmp_path):
        assert load_pid(tmp_path / "nonexistent.pid") is None

    def test_load_invalid_returns_none(self, tmp_path):
        pid_file = tmp_path / "bad.pid"
        pid_file.write_text("not-a-number")
        assert load_pid(pid_file) is None
