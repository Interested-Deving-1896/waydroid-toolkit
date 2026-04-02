"""wdt dbus — D-Bus service mode."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.group("dbus")
def cmd() -> None:
    """Start or query the waydroid-toolkit D-Bus service."""


@cmd.command("serve")
def dbus_serve() -> None:
    """Start the D-Bus service and block until stopped.

    Registers ``io.github.waydroid_toolkit`` on the session bus.
    Requires python3-dbus and python3-gi.
    """
    from waydroid_toolkit.modules.dbus import WdtService
    try:
        service = WdtService()
        service.run()
    except ImportError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    except KeyboardInterrupt:
        pass


@cmd.command("status")
def dbus_status() -> None:
    """Call GetStatus() on the running D-Bus service."""
    _call_method("GetStatus", [], lambda r: console.print_json(r))


@cmd.command("list-profiles")
def dbus_list_profiles() -> None:
    """Call ListProfiles() on the running D-Bus service."""
    _call_method("ListProfiles", [], lambda r: console.print_json(r))


@cmd.command("switch-profile")
@click.argument("name")
def dbus_switch_profile(name: str) -> None:
    """Call SwitchProfile(NAME) on the running D-Bus service."""
    _call_method("SwitchProfile", [name], lambda r: console.print(
        "[green]OK[/green]" if r else "[red]Profile not found[/red]"
    ))


@cmd.command("list-extensions")
def dbus_list_extensions() -> None:
    """Call ListExtensions() on the running D-Bus service."""
    _call_method("ListExtensions", [], lambda r: console.print_json(r))


@cmd.command("install-extension")
@click.argument("ext_id")
def dbus_install_extension(ext_id: str) -> None:
    """Call InstallExtension(EXT_ID) on the running D-Bus service."""
    _call_method("InstallExtension", [ext_id], lambda r: console.print(
        "[green]Installed[/green]" if r else "[red]Install failed[/red]"
    ))


@cmd.command("create-snapshot")
@click.argument("label", default="", required=False)
def dbus_create_snapshot(label: str) -> None:
    """Call CreateSnapshot(LABEL) on the running D-Bus service."""
    _call_method("CreateSnapshot", [label], lambda r: console.print(
        f"[green]Snapshot created:[/green] {r}"
    ))


@cmd.command("list-snapshots")
def dbus_list_snapshots() -> None:
    """Call ListSnapshots() on the running D-Bus service."""
    _call_method("ListSnapshots", [], lambda r: console.print_json(r))


@cmd.command("stop")
def dbus_stop() -> None:
    """Call Stop() on the running D-Bus service."""
    _call_method("Stop", [], lambda _: console.print("[green]Service stopped.[/green]"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _call_method(
    method: str,
    args: list,
    on_result,
) -> None:
    """Connect to the session bus and call *method* on the WdtService object."""
    try:
        import dbus
    except ImportError:
        console.print(
            "[red]dbus-python not installed.[/red] "
            "Install with: sudo apt install python3-dbus"
        )
        raise SystemExit(1)

    try:
        bus = dbus.SessionBus()
        obj = bus.get_object(
            "io.github.waydroid_toolkit",
            "/io/github/waydroid_toolkit",
        )
        iface = dbus.Interface(obj, "io.github.waydroid_toolkit.Manager")
        fn = getattr(iface, method)
        result = fn(*args)
        on_result(result)
    except dbus.exceptions.DBusException as exc:
        console.print(f"[red]D-Bus error: {exc}[/red]")
        raise SystemExit(1)
