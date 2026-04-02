"""wdt images — manage Waydroid image profiles."""

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.modules.images import (
    check_updates,
    download_updates,
    get_active_profile,
    scan_profiles,
    switch_profile,
)

console = Console()


@click.group("images")
def cmd() -> None:
    """List and switch between Waydroid image profiles."""


@cmd.command("list")
@click.option("--base", default=None, help="Directory to scan for profiles (default: ~/waydroid-images).")  # noqa: E501
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


@cmd.command("check-update")
def check_update() -> None:
    """Check OTA channels for available image updates."""
    import urllib.error
    try:
        system_info, vendor_info = check_updates()
    except urllib.error.URLError as exc:
        console.print(f"[red]Network error: {exc}[/red]")
        raise SystemExit(1)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Channel")
    table.add_column("Current build")
    table.add_column("Latest build")
    table.add_column("Status")

    for info in (system_info, vendor_info):
        current = str(info.current_datetime) if info.current_datetime else "none"
        latest  = str(info.latest.datetime) if info.latest else "unavailable"
        if info.update_available:
            status = "[green]update available[/green]"
        elif info.latest is None:
            status = "[yellow]channel unavailable[/yellow]"
        else:
            status = "[dim]up to date[/dim]"
        table.add_row(info.channel, current, latest, status)

    console.print(table)


@cmd.command("download")
@click.option(
    "--dest",
    default=None,
    help="Directory to save images (default: ~/waydroid-images/ota).",
)
@click.option(
    "--no-update-cfg",
    is_flag=True,
    default=False,
    help="Do not update system_datetime/vendor_datetime in waydroid.cfg.",
)
def download_image_cmd(dest: str | None, no_update_cfg: bool) -> None:
    """Download the latest system and vendor images from the OTA channel."""
    import urllib.error
    from pathlib import Path

    dest_dir = Path(dest) if dest else Path.home() / "waydroid-images" / "ota"

    try:
        system_path, vendor_path = download_updates(
            dest_dir=dest_dir,
            progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"),
            update_cfg=not no_update_cfg,
        )
    except urllib.error.URLError as exc:
        console.print(f"[red]Network error: {exc}[/red]")
        raise SystemExit(1)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)

    if system_path:
        console.print(f"[green]System image: {system_path}[/green]")
    if vendor_path:
        console.print(f"[green]Vendor image: {vendor_path}[/green]")
    if not system_path and not vendor_path:
        console.print("[dim]No updates downloaded — images are already up to date.[/dim]")
