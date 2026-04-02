"""wdt extensions — manage Waydroid extensions."""

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.modules.extensions import (
    REGISTRY,
    ConflictError,
    CyclicDependencyError,
    DependencyError,
    ExtensionState,
    MissingDependencyError,
    get,
    install_with_deps,
    list_all,
    resolve,
)

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
@click.argument("extension_ids", nargs=-1, required=True)
@click.option("--dry-run", is_flag=True, default=False,
              help="Show the resolved install order without installing.")
def install_extension(extension_ids: tuple[str, ...], dry_run: bool) -> None:
    """Install one or more extensions by ID, resolving dependencies automatically.

    Example: wdt extensions install gapps widevine
    """
    try:
        order = resolve(list(extension_ids), REGISTRY)
    except MissingDependencyError as e:
        console.print(f"[red]Missing dependency: {e}[/red]")
        raise SystemExit(1)
    except ConflictError as e:
        console.print(f"[red]Conflict: {e}[/red]")
        raise SystemExit(1)
    except CyclicDependencyError as e:
        console.print(f"[red]Cyclic dependency: {e}[/red]")
        raise SystemExit(1)

    if dry_run:
        console.print("[bold]Resolved install order:[/bold]")
        for i, ext_id in enumerate(order, 1):
            ext = REGISTRY[ext_id]
            state = "[green]installed[/green]" if ext.is_installed() else "pending"
            console.print(f"  {i}. {ext.meta.name} ({ext_id}) — {state}")
        return

    try:
        installed = install_with_deps(
            list(extension_ids),
            REGISTRY,
            progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"),
        )
    except DependencyError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    if installed:
        console.print(f"[green]Installed: {', '.join(installed)}[/green]")
    else:
        console.print("[yellow]All requested extensions are already installed.[/yellow]")


@cmd.command("deps")
@click.argument("extension_ids", nargs=-1, required=True)
def show_deps(extension_ids: tuple[str, ...]) -> None:
    """Show the resolved dependency order for one or more extensions."""
    try:
        order = resolve(list(extension_ids), REGISTRY)
    except DependencyError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Requires")
    table.add_column("Conflicts")

    for i, ext_id in enumerate(order, 1):
        ext = REGISTRY[ext_id]
        table.add_row(
            str(i),
            ext_id,
            ext.meta.name,
            ", ".join(ext.meta.requires) or "—",
            ", ".join(ext.meta.conflicts) or "—",
        )
    console.print(table)


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
