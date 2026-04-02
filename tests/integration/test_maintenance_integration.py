"""Integration tests for maintenance tools.

Requires a live Waydroid session + ADB. Skipped automatically otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from waydroid_toolkit.modules.maintenance.tools import (
    get_device_info,
    get_logcat,
    pull_file,
    push_file,
    take_screenshot,
)


class TestDeviceInfoIntegration:
    def test_returns_all_keys(self, adb_connected: None) -> None:
        info = get_device_info()
        for key in ("android_version", "sdk_version", "product_model", "cpu_abi"):
            assert key in info

    def test_android_version_is_numeric(self, adb_connected: None) -> None:
        info = get_device_info()
        version = info["android_version"]
        assert version != "unavailable"
        assert version.replace(".", "").isdigit()

    def test_sdk_version_is_integer(self, adb_connected: None) -> None:
        info = get_device_info()
        sdk = info["sdk_version"]
        assert sdk.isdigit()
        assert int(sdk) >= 30  # Waydroid ships Android 11+ (API 30)


class TestScreenshotIntegration:
    def test_creates_png_file(self, adb_connected: None, tmp_path: Path) -> None:
        dest = tmp_path / "integration_screenshot.png"
        result = take_screenshot(dest)
        assert result == dest
        assert dest.exists()
        assert dest.stat().st_size > 0

    def test_png_has_valid_header(self, adb_connected: None, tmp_path: Path) -> None:
        dest = tmp_path / "header_check.png"
        take_screenshot(dest)
        header = dest.read_bytes()[:8]
        assert header == b"\x89PNG\r\n\x1a\n"


class TestFileTransferIntegration:
    def test_push_and_pull_roundtrip(self, adb_connected: None, tmp_path: Path) -> None:
        content = "waydroid-toolkit integration test\n"
        src = tmp_path / "push_src.txt"
        src.write_text(content)
        remote = "/sdcard/wdt_integration_push.txt"
        dest = tmp_path / "pull_dest.txt"

        push_file(src, remote)
        pull_file(remote, dest)

        assert dest.read_text() == content

    def test_push_nonexistent_raises(self, adb_connected: None) -> None:
        with pytest.raises(Exception):
            push_file(Path("/nonexistent/file.txt"), "/sdcard/nope.txt")


class TestLogcatIntegration:
    def test_returns_non_empty_string(self, adb_connected: None) -> None:
        output = get_logcat(lines=50)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_respects_line_limit(self, adb_connected: None) -> None:
        output = get_logcat(lines=10)
        lines = output.splitlines()
        assert len(lines) <= 10
