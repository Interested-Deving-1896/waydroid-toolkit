"""Integration tests for the extension resolver and registry.

These tests do NOT install extensions (that would modify the running system).
They verify that the resolver, conflict detection, and state queries work
correctly against the real registry with a live Waydroid session.
"""

from __future__ import annotations

import pytest

from waydroid_toolkit.modules.extensions import (
    REGISTRY,
    ConflictError,
    list_all,
    resolve,
)
from waydroid_toolkit.modules.extensions.base import ExtensionState


class TestRegistryIntegration:
    def test_all_extensions_have_valid_state(self, adb_connected: None) -> None:
        """state() must return a valid ExtensionState for every extension."""
        for ext in list_all():
            state = ext.state()
            assert isinstance(state, ExtensionState), (
                f"{ext.meta.id}.state() returned {state!r}"
            )

    def test_is_installed_returns_bool(self, adb_connected: None) -> None:
        for ext in list_all():
            result = ext.is_installed()
            assert isinstance(result, bool), (
                f"{ext.meta.id}.is_installed() returned {result!r}"
            )

    def test_no_extension_installed_twice(self, adb_connected: None) -> None:
        """Sanity: conflicting extensions should not both be installed."""
        installed = {
            ext.meta.id for ext in list_all() if ext.is_installed()
        }
        for ext in list_all():
            if ext.meta.id in installed:
                for conflict_id in ext.meta.conflicts:
                    assert conflict_id not in installed, (
                        f"Both '{ext.meta.id}' and '{conflict_id}' are installed "
                        f"but they conflict."
                    )


class TestResolverIntegration:
    def test_resolve_single_extension(self, adb_connected: None) -> None:
        order = resolve(["gapps"], REGISTRY)
        assert "gapps" in order

    def test_resolve_respects_conflicts(self, adb_connected: None) -> None:
        with pytest.raises(ConflictError):
            resolve(["gapps", "microg"], REGISTRY)

    def test_resolve_libhoudini_libndk_conflict(self, adb_connected: None) -> None:
        with pytest.raises(ConflictError):
            resolve(["libhoudini", "libndk"], REGISTRY)

    def test_resolve_compatible_set(self, adb_connected: None) -> None:
        # gapps + magisk + libhoudini + widevine + keymapper have no conflicts
        safe = ["gapps", "magisk", "libhoudini", "widevine", "keymapper"]
        order = resolve(safe, REGISTRY)
        assert set(order) == set(safe)

    def test_resolve_order_respects_requires(self, adb_connected: None) -> None:
        """Every extension's requires must appear before it in the resolved order."""
        safe = ["gapps", "magisk", "libhoudini", "widevine", "keymapper"]
        order = resolve(safe, REGISTRY)
        for ext_id in order:
            ext = REGISTRY[ext_id]
            for dep_id in ext.meta.requires:
                if dep_id in order:
                    assert order.index(dep_id) < order.index(ext_id), (
                        f"Dependency '{dep_id}' appears after '{ext_id}' in order"
                    )
