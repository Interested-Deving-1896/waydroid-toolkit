"""wdt extensions — manage Waydroid extensions."""

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.modules.extensions import ExtensionState, get, list_all

console = Console()


@click.group("extensions")
def cmd() -> None:
    """Install, remove, and list Waydroid extensions."""


@cmd.command("list")
def list_extensions() -> None:
    """List all available extensions and their install state."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("State")
    table.add_column("Conflicts")

    for ext in list_all():
        state = ext.state()
        state_str = {
            ExtensionState.INSTALLED: "[green]installed[/green]",
            ExtensionState.NOT_INSTALLED: "not installed",
            ExtensionState.UNKNOWN: "[yellow]unknown[/yellow]",
        }[state]
        conflicts = ", ".join(ext.meta.conflicts) or "—"
        table.add_row(ext.meta.id, ext.meta.name, state_str, conflicts)

    console.print(table)


@cmd.command("install")
@click.argument("extension_id")
def install_extension(extension_id: str) -> None:
    """Install an extension by ID (e.g. gapps, magisk, libhoudini)."""
    try:
        ext = get(extension_id)
    except KeyError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    if ext.is_installed():
        console.print(f"[yellow]{ext.meta.name} is already installed.[/yellow]")
        return

    # Check conflicts
    for conflict_id in ext.meta.conflicts:
        try:
            conflict = get(conflict_id)
            if conflict.is_installed():
                console.print(
                    f"[red]Cannot install {ext.meta.name}: conflicts with "
                    f"{conflict.meta.name} (currently installed).[/red]"
                )
                raise SystemExit(1)
        except KeyError:
            pass

    console.print(f"[bold]Installing {ext.meta.name}...[/bold]")
    ext.install(progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print(f"[green]{ext.meta.name} installed.[/green]")


@cmd.command("remove")
@click.argument("extension_id")
def remove_extension(extension_id: str) -> None:
    """Remove an installed extension by ID."""
    try:
        ext = get(extension_id)
    except KeyError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    if not ext.is_installed():
        console.print(f"[yellow]{ext.meta.name} is not installed.[/yellow]")
        return

    console.print(f"[bold]Removing {ext.meta.name}...[/bold]")
    ext.uninstall(progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print(f"[green]{ext.meta.name} removed.[/green]")
