"""Integration tests for the Waydroid core interface.

Requires a live Waydroid session. Skipped automatically when unavailable.
See conftest.py for skip conditions.
"""

from __future__ import annotations

from waydroid_toolkit.core.waydroid import (
    SessionState,
    WaydroidConfig,
    get_android_id,
    get_session_state,
    is_initialized,
    is_installed,
    shell,
)


class TestWaydroidCoreIntegration:
    def test_is_installed(self) -> None:
        assert is_installed() is True

    def test_is_initialized(self) -> None:
        assert is_initialized() is True

    def test_session_state_is_running(self) -> None:
        assert get_session_state() == SessionState.RUNNING

    def test_config_has_images_path(self) -> None:
        cfg = WaydroidConfig.load()
        assert cfg.images_path != ""

    def test_shell_getprop(self) -> None:
        result = shell("getprop ro.product.cpu.abi")
        assert result.returncode == 0
        assert result.stdout.strip() in ("x86_64", "arm64-v8a", "x86", "armeabi-v7a")

    def test_get_android_id_returns_hex_string(self) -> None:
        android_id = get_android_id()
        # android_id is a 16-char hex string or None if unavailable
        if android_id is not None:
            assert len(android_id) == 16
            int(android_id, 16)  # raises ValueError if not valid hex


class TestPackageManagerIntegration:
    def test_list_packages_via_shell(self) -> None:
        result = shell("pm list packages")
        assert result.returncode == 0
        lines = [ln for ln in result.stdout.splitlines() if ln.startswith("package:")]
        assert len(lines) > 0

    def test_getprop_sdk_version_is_integer(self) -> None:
        result = shell("getprop ro.build.version.sdk")
        sdk = result.stdout.strip()
        assert sdk.isdigit(), f"SDK version not an integer: {sdk!r}"
        assert int(sdk) >= 28  # Waydroid ships Android 11+ (API 30+)
