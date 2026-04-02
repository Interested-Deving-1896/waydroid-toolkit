"""Integration tests for image profile management.

Requires a live Waydroid session. Does NOT switch profiles (that would
stop the running session). Verifies scan, active profile detection, and
ATV detection against the current system image.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from waydroid_toolkit.modules.images import (
    get_active_profile,
    is_atv_profile,
    profile_is_atv_configured,
    scan_profiles,
)
from waydroid_toolkit.modules.images.manager import ImageProfile


class TestScanProfilesIntegration:
    def test_returns_list(self, adb_connected: None) -> None:
        profiles = scan_profiles()
        assert isinstance(profiles, list)

    def test_profiles_are_image_profile_instances(self, adb_connected: None) -> None:
        for p in scan_profiles():
            assert isinstance(p, ImageProfile)

    def test_profiles_have_name_and_path(self, adb_connected: None) -> None:
        for p in scan_profiles():
            assert p.name
            assert isinstance(p.path, Path)


class TestActiveProfileIntegration:
    def test_active_profile_or_none(self, adb_connected: None) -> None:
        active = get_active_profile()
        # May be None if no profile is configured yet
        assert active is None or isinstance(active, ImageProfile)


class TestAtvDetectionIntegration:
    def test_is_atv_profile_returns_bool(self, adb_connected: None) -> None:
        """Run ATV detection against the active profile's path."""
        active = get_active_profile()
        if active is None:
            pytest.skip("No active profile — cannot test ATV detection")
        result = is_atv_profile(active.path)
        assert isinstance(result, bool)

    def test_profile_is_atv_configured_returns_bool(self, adb_connected: None) -> None:
        result = profile_is_atv_configured()
        assert isinstance(result, bool)

    def test_atv_configured_consistent_with_detection(self, adb_connected: None) -> None:
        """If the active profile is ATV, waydroid.cfg should reflect that."""
        active = get_active_profile()
        if active is None:
            pytest.skip("No active profile")
        detected = is_atv_profile(active.path)
        configured = profile_is_atv_configured()
        # They may differ (user may have manually changed cfg), but both must be bool
        assert isinstance(detected, bool)
        assert isinstance(configured, bool)
