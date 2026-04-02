"""Integration tests for the D-Bus service.

These tests start the WdtService in a background thread and call its
public Python API directly (no real D-Bus connection required). They
verify that the service methods return correct types and values when
a live Waydroid session is available.

A separate ``test_dbus_wire`` class tests the actual D-Bus wire protocol
and is skipped when ``dbus-python`` is not installed.
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from waydroid_toolkit.modules.dbus.service import WdtService


class TestWdtServiceApiIntegration:
    """Call WdtService methods directly against a live Waydroid session."""

    def test_get_status_state_is_running(self, adb_connected: None) -> None:
        svc = WdtService()
        result = svc.get_status()
        assert result["state"] == "running"

    def test_get_status_version_is_string(self, adb_connected: None) -> None:
        svc = WdtService()
        result = svc.get_status()
        assert isinstance(result["version"], str)
        assert result["version"]  # non-empty

    def test_list_profiles_returns_list(self, adb_connected: None) -> None:
        svc = WdtService()
        result = svc.list_profiles()
        assert isinstance(result, list)

    def test_list_extensions_returns_all_extensions(self, adb_connected: None) -> None:
        from waydroid_toolkit.modules.extensions import list_all
        svc = WdtService()
        result = svc.list_extensions()
        assert len(result) == len(list_all())

    def test_list_extensions_have_required_keys(self, adb_connected: None) -> None:
        svc = WdtService()
        for ext in svc.list_extensions():
            assert "id" in ext
            assert "name" in ext
            assert "state" in ext

    def test_switch_profile_nonexistent_returns_false(self, adb_connected: None) -> None:
        svc = WdtService()
        result = svc.switch_profile("__nonexistent_profile__")
        assert result is False

    def test_install_extension_unknown_returns_false(self, adb_connected: None) -> None:
        svc = WdtService()
        result = svc.install_extension("__unknown_ext__")
        assert result is False

    def test_list_snapshots_returns_list(self, adb_connected: None) -> None:
        svc = WdtService()
        result = svc.list_snapshots()
        assert isinstance(result, list)

    def test_stop_does_not_raise_without_loop(self, adb_connected: None) -> None:
        svc = WdtService()
        svc._loop = None
        svc.stop()  # must not raise


class TestWdtServiceDbusWire:
    """Test the actual D-Bus wire protocol. Skipped if dbus-python absent."""

    @pytest.fixture(autouse=True)
    def _require_dbus(self):
        pytest.importorskip("dbus", reason="dbus-python not installed")

    def test_service_registers_on_session_bus(self, adb_connected: None) -> None:
        import dbus
        svc = WdtService()
        stop_event = threading.Event()

        def _run():
            try:
                svc.run()
            except Exception:
                pass
            finally:
                stop_event.set()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        time.sleep(0.5)  # give the service time to register

        try:
            bus = dbus.SessionBus()
            obj = bus.get_object(
                "io.github.waydroid_toolkit",
                "/io/github/waydroid_toolkit",
            )
            iface = dbus.Interface(obj, "io.github.waydroid_toolkit.Manager")
            raw = iface.GetStatus()
            data = json.loads(raw)
            assert "state" in data
        finally:
            svc.stop()
            t.join(timeout=3)
