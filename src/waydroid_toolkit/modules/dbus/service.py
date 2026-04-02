"""D-Bus service implementation for waydroid-toolkit.

Registers ``io.github.waydroid_toolkit`` on the session bus and exposes
the ``io.github.waydroid_toolkit.Manager`` interface.

The service is intentionally thin: it delegates every call to the same
Python functions used by the CLI, so there is no logic duplication.

D-Bus dependency
----------------
``dbus-python`` (``python3-dbus`` on Debian/Ubuntu) is an optional runtime
dependency.  If it is not installed the module can still be imported and
tested; ``WdtService.run()`` will raise ``ImportError`` with a clear message.

Interface summary
-----------------
Methods
    GetStatus()          → dict   Waydroid session state + version
    ListProfiles()       → list   Available image profiles
    SwitchProfile(name)  → bool   Switch to a named image profile
    ListExtensions()     → list   All extensions with install state
    InstallExtension(id) → bool   Install an extension (with dep resolution)
    CreateSnapshot(label)→ str    Take a filesystem snapshot; returns name
    ListSnapshots()      → list   All snapshots (name, backend, created)
    Stop()               → void   Gracefully stop the service

Signals
    ProfileChanged(name)          Emitted after a successful SwitchProfile
    ExtensionInstalled(id)        Emitted after a successful InstallExtension
    SnapshotCreated(name, backend)Emitted after a successful CreateSnapshot
"""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)

BUS_NAME   = "io.github.waydroid_toolkit"
OBJECT_PATH = "/io/github/waydroid_toolkit"
INTERFACE   = "io.github.waydroid_toolkit.Manager"


class WdtService:
    """D-Bus service object.

    Instantiate and call ``run()`` to start the GLib main loop.
    """

    def __init__(self) -> None:
        self._loop: Any = None   # GLib.MainLoop, set in run()
        self._bus:  Any = None   # dbus.SessionBus, set in run()

    # ── Public API (also callable directly without D-Bus) ─────────────────────

    def get_status(self) -> dict[str, str]:
        """Return Waydroid session state and toolkit version."""
        from waydroid_toolkit import __version__
        from waydroid_toolkit.core.waydroid import get_session_state
        try:
            state = get_session_state().value
        except Exception:  # noqa: BLE001
            state = "unknown"
        return {"state": state, "version": __version__}

    def list_profiles(self) -> list[dict[str, str]]:
        """Return available image profiles."""
        from waydroid_toolkit.modules.images import scan_profiles
        return [{"name": p.name, "path": str(p.path)} for p in scan_profiles()]

    def switch_profile(self, name: str) -> bool:
        """Switch to a named image profile. Returns True on success."""
        from waydroid_toolkit.modules.images import scan_profiles, switch_profile
        profiles = scan_profiles()
        match = next((p for p in profiles if p.name == name), None)
        if match is None:
            return False
        switch_profile(match)
        return True

    def list_extensions(self) -> list[dict[str, str]]:
        """Return all extensions with their install state."""
        from waydroid_toolkit.modules.extensions import list_all
        return [
            {
                "id":    ext.meta.id,
                "name":  ext.meta.name,
                "state": ext.state().value,
            }
            for ext in list_all()
        ]

    def install_extension(self, ext_id: str) -> bool:
        """Install an extension (with dependency resolution). Returns True on success."""
        from waydroid_toolkit.modules.extensions import REGISTRY, install_with_deps
        try:
            install_with_deps([ext_id], REGISTRY)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("install_extension(%s) failed: %s", ext_id, exc)
            return False

    def create_snapshot(self, label: str = "") -> str:
        """Take a filesystem snapshot. Returns the snapshot name."""
        from waydroid_toolkit.modules.snapshot import get_backend
        backend = get_backend()
        info = backend.create(label)
        return info.name

    def list_snapshots(self) -> list[dict[str, str]]:
        """Return all snapshots."""
        from waydroid_toolkit.modules.snapshot import get_backend
        try:
            backend = get_backend()
            return [
                {
                    "name":    s.name,
                    "backend": s.backend,
                    "created": s.created.isoformat(),
                    "source":  s.source,
                }
                for s in backend.list()
            ]
        except RuntimeError:
            return []

    def stop(self) -> None:
        """Stop the D-Bus service and exit the main loop."""
        if self._loop is not None:
            self._loop.quit()

    # ── D-Bus runner ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the D-Bus service and block until stopped.

        Raises
        ------
        ImportError
            If ``dbus-python`` is not installed.
        """
        try:
            import dbus
            import dbus.mainloop.glib
            import dbus.service
            from gi.repository import GLib
        except ImportError as exc:
            raise ImportError(
                "D-Bus service requires dbus-python and PyGObject. "
                "Install with: sudo apt install python3-dbus python3-gi"
            ) from exc

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self._bus = dbus.SessionBus()

        # Build the dbus.service.Object subclass dynamically so that the
        # dbus decorators can reference the live dbus module.
        _build_dbus_object(self, self._bus)

        self._loop = GLib.MainLoop()
        log.info("WdtService running on %s", BUS_NAME)
        try:
            self._loop.run()
        finally:
            log.info("WdtService stopped.")


# ── Dynamic D-Bus object builder ─────────────────────────────────────────────

def _build_dbus_object(service: WdtService, bus: Any) -> Any:
    """Create and register the dbus.service.Object on *bus*.

    This is a separate function so the class body can reference the
    already-imported ``dbus`` module without a top-level import.
    """
    import dbus
    import dbus.service

    class _WdtDbusObject(dbus.service.Object):  # type: ignore[misc]
        def __init__(self) -> None:
            bus_name = dbus.service.BusName(BUS_NAME, bus=bus)
            super().__init__(bus_name, OBJECT_PATH)

        @dbus.service.method(INTERFACE, out_signature="s")
        def GetStatus(self) -> str:  # noqa: N802
            return json.dumps(service.get_status())

        @dbus.service.method(INTERFACE, out_signature="s")
        def ListProfiles(self) -> str:  # noqa: N802
            return json.dumps(service.list_profiles())

        @dbus.service.method(INTERFACE, in_signature="s", out_signature="b")
        def SwitchProfile(self, name: str) -> bool:  # noqa: N802
            result = service.switch_profile(str(name))
            if result:
                self.ProfileChanged(str(name))
            return result

        @dbus.service.method(INTERFACE, out_signature="s")
        def ListExtensions(self) -> str:  # noqa: N802
            return json.dumps(service.list_extensions())

        @dbus.service.method(INTERFACE, in_signature="s", out_signature="b")
        def InstallExtension(self, ext_id: str) -> bool:  # noqa: N802
            result = service.install_extension(str(ext_id))
            if result:
                self.ExtensionInstalled(str(ext_id))
            return result

        @dbus.service.method(INTERFACE, in_signature="s", out_signature="s")
        def CreateSnapshot(self, label: str) -> str:  # noqa: N802
            name = service.create_snapshot(str(label))
            self.SnapshotCreated(name, "")
            return name

        @dbus.service.method(INTERFACE, out_signature="s")
        def ListSnapshots(self) -> str:  # noqa: N802
            return json.dumps(service.list_snapshots())

        @dbus.service.method(INTERFACE)
        def Stop(self) -> None:  # noqa: N802
            service.stop()

        # ── Signals ───────────────────────────────────────────────────────────

        @dbus.service.signal(INTERFACE, signature="s")
        def ProfileChanged(self, name: str) -> None:  # noqa: N802
            pass

        @dbus.service.signal(INTERFACE, signature="s")
        def ExtensionInstalled(self, ext_id: str) -> None:  # noqa: N802
            pass

        @dbus.service.signal(INTERFACE, signature="ss")
        def SnapshotCreated(self, name: str, backend: str) -> None:  # noqa: N802
            pass

    return _WdtDbusObject()
