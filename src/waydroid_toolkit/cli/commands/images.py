"""wdt images — manage Waydroid image profiles."""

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.modules.images import get_active_profile, scan_profiles, switch_profile

console = Console()


@click.group("images")
def cmd() -> None:
    """List and switch between Waydroid image profiles."""


@cmd.command("list")
@click.option("--base", default=None, help="Directory to scan for profiles (default: ~/waydroid-images).")
def list_images(base: str | None) -> None:
    """List available image profiles."""
    from pathlib import Path
    scan_dir = Path(base) if base else None
    profiles = scan_profiles(*([scan_dir] if scan_dir else []))
    active = get_active_profile()

    if not profiles:
        console.print("[yellow]No image profiles found under ~/waydroid-images.[/yellow]")
        console.print("Place system.img + vendor.img pairs in subdirectories there.")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Path")
    table.add_column("Active")

    for p in profiles:
        is_active = active and str(p.path) in active
        table.add_row(
            p.name,
            str(p.path),
            "[green]✅[/green]" if is_active else "",
        )
    console.print(table)


@cmd.command("switch")
@click.argument("profile_name")
@click.option("--base", default=None, help="Directory to scan for profiles.")
def switch_image(profile_name: str, base: str | None) -> None:
    """Switch to a named image profile."""
    from pathlib import Path
    scan_dir = Path(base) if base else None
    profiles = scan_profiles(*([scan_dir] if scan_dir else []))
    match = next((p for p in profiles if p.name == profile_name), None)

    if match is None:
        console.print(f"[red]Profile '{profile_name}' not found.[/red]")
        raise SystemExit(1)

    switch_profile(match, progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print(f"[green]Switched to profile '{profile_name}'.[/green]")
