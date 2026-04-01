"""Integration tests for the package manager module.

Requires a live Waydroid session. Skipped automatically when unavailable.
See conftest.py for skip conditions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from waydroid_toolkit.modules.packages.manager import (
    get_installed_packages,
    install_apk_file,
    remove_package,
)


class TestPackagesIntegration:
    def test_get_installed_packages_returns_list(self, adb_connected: None) -> None:
        packages = get_installed_packages()
        assert isinstance(packages, list)
        assert len(packages) > 0

    def test_installed_packages_are_strings(self, adb_connected: None) -> None:
        packages = get_installed_packages()
        assert all(isinstance(p, str) for p in packages)

    def test_installed_packages_contain_dot(self, adb_connected: None) -> None:
        # All Android package names contain at least one dot
        packages = get_installed_packages()
        assert all("." in p for p in packages)

    def test_install_apk_file_roundtrip(
        self, adb_connected: None, tmp_path: Path
    ) -> None:
        minimal_apk = Path(__file__).parent / "fixtures" / "minimal.apk"
        if not minimal_apk.exists():
            pytest.skip("fixtures/minimal.apk not present")

        pkg = "com.waydroidtoolkit.integrationtest"
        install_apk_file(minimal_apk)

        packages = get_installed_packages()
        assert pkg in packages

        remove_package(pkg)
        packages_after = get_installed_packages()
        assert pkg not in packages_after
