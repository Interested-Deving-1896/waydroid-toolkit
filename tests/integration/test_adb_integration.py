"""Integration tests for the ADB interface.

Requires a live Waydroid session. Skipped automatically when unavailable.
See conftest.py for skip conditions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from waydroid_toolkit.core import adb


class TestAdbIntegration:
    """End-to-end ADB operations against a real Waydroid container."""

    def test_is_connected_after_connect(self, adb_connected: None) -> None:
        assert adb.is_connected() is True

    def test_shell_returns_output(self, adb_connected: None) -> None:
        result = adb.shell("getprop ro.build.version.release")
        assert result.returncode == 0
        assert result.stdout.strip() != ""

    def test_shell_android_version_is_numeric(self, adb_connected: None) -> None:
        result = adb.shell("getprop ro.build.version.release")
        version = result.stdout.strip()
        assert version.replace(".", "").isdigit(), f"Unexpected version: {version!r}"

    def test_list_packages_returns_list(self, adb_connected: None) -> None:
        packages = adb.list_packages()
        assert isinstance(packages, list)
        assert len(packages) > 0

    def test_list_packages_contains_android_framework(self, adb_connected: None) -> None:
        packages = adb.list_packages()
        assert any("android" in p.lower() for p in packages)

    def test_screenshot_creates_file(self, adb_connected: None, tmp_path: Path) -> None:
        dest = tmp_path / "integration_shot.png"
        result_path = adb.screenshot(dest)
        assert result_path == dest
        assert dest.exists()
        assert dest.stat().st_size > 0

    def test_push_and_pull_roundtrip(self, adb_connected: None, tmp_path: Path) -> None:
        # Write a file, push it, pull it back, verify contents match
        src = tmp_path / "push_test.txt"
        src.write_text("waydroid-toolkit integration test")
        remote = "/sdcard/wdt_push_test.txt"
        dest = tmp_path / "pulled.txt"

        push_result = adb.push(src, remote)
        assert push_result.returncode == 0

        pull_result = adb.pull(remote, dest)
        assert pull_result.returncode == 0
        assert dest.read_text() == "waydroid-toolkit integration test"

        # Clean up remote file
        adb.shell(f"rm {remote}")

    def test_install_and_uninstall_apk(
        self, adb_connected: None, tmp_path: Path
    ) -> None:
        """Install a minimal valid APK and verify it appears in package list."""
        pytest.importorskip("struct")  # always available — just a guard pattern

        # Use a pre-built minimal APK if available, otherwise skip
        minimal_apk = Path(__file__).parent / "fixtures" / "minimal.apk"
        if not minimal_apk.exists():
            pytest.skip("fixtures/minimal.apk not present — skipping APK install test")

        pkg = "com.waydroidtoolkit.integrationtest"
        install_result = adb.install_apk(minimal_apk)
        assert install_result.returncode == 0

        packages = adb.list_packages()
        assert pkg in packages

        uninstall_result = adb.uninstall_package(pkg)
        assert uninstall_result.returncode == 0

        packages_after = adb.list_packages()
        assert pkg not in packages_after
