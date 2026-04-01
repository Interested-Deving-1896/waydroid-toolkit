"""wdt status — show Waydroid runtime status."""

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.core.adb import is_available as adb_available
from waydroid_toolkit.core.adb import is_connected as adb_connected
from waydroid_toolkit.core.waydroid import (
    SessionState,
    WaydroidConfig,
    get_session_state,
    is_initialized,
    is_installed,
)

console = Console()


@click.command("status")
def cmd() -> None:
    """Show Waydroid runtime status."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    installed = is_installed()
    table.add_row("Waydroid installed", "✅ yes" if installed else "❌ no")

    if installed:
        initialized = is_initialized()
        table.add_row("Waydroid initialized", "✅ yes" if initialized else "❌ no")

        state = get_session_state()
        state_str = {
            SessionState.RUNNING: "✅ running",
            SessionState.STOPPED: "⏹  stopped",
            SessionState.UNKNOWN: "❓ unknown",
        }[state]
        table.add_row("Session state", state_str)

        cfg = WaydroidConfig.load()
        table.add_row("Images path", cfg.images_path or "(not set)")
        table.add_row("Overlay enabled", "yes" if cfg.mount_overlays else "no")

    table.add_row("ADB available", "✅ yes" if adb_available() else "❌ no")
    if adb_available():
        table.add_row("ADB connected", "✅ yes" if adb_connected() else "no")

    console.print(table)
