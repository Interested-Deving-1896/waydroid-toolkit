"""wdt profiles — manage Waydroid image profiles.

An image profile is a directory containing a system.img + vendor.img pair.
Profiles live under ~/waydroid-images/ by default.

Sub-commands
------------
  wdt profiles list              List available profiles
  wdt profiles show <name>       Show details for a profile
  wdt profiles switch <name>     Switch the active profile
  wdt profiles active            Print the currently active profile
  wdt profiles add <path>        Register a directory as a named profile
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.modules.images import (
    get_active_profile,
    scan_profiles,
    switch_profile,
)

console = Console()

_DEFAULT_BASE = Path.home() / "waydroid-images"


@click.group("profiles")
def cmd() -> None:
    """Manage Waydroid image profiles (system.img + vendor.img pairs)."""


@cmd.command("list")
@click.option("--base", default=None,
              help="Directory to scan for profiles (default: ~/waydroid-images).")
def profiles_list(base: str | None) -> None:
    """List available image profiles."""
    scan_dir = Path(base) if base else _DEFAULT_BASE
    profiles = scan_profiles(scan_dir)
    active = get_active_profile()

    if not profiles:
        console.print(f"[yellow]No profiles found under {scan_dir}[/yellow]")
        console.print("Place system.img + vendor.img pairs in subdirectories there.")
        console.print("Or specify a different base: wdt profiles list --base <dir>")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("NAME", style="cyan")
    table.add_column("PATH")
    table.add_column("ACTIVE")
    table.add_column("SIZE")

    for p in profiles:
        is_active = active and str(p.path) in active
        # Sum system.img + vendor.img sizes
        size_mb = 0
        for img in ("system.img", "vendor.img"):
            f = p.path / img
            if f.exists():
                size_mb += f.stat().st_size // (1024 * 1024)
        size_str = f"{size_mb} MiB" if size_mb else "?"
        table.add_row(
            p.name,
            str(p.path),
            "[green]✓[/green]" if is_active else "",
            size_str,
        )

    console.print(table)
    console.print(f"\n{len(profiles)} profile(s) found under {scan_dir}")


@cmd.command("show")
@click.argument("name")
@click.option("--base", default=None, help="Directory to scan for profiles.")
def profiles_show(name: str, base: str | None) -> None:
    """Show details for a named profile."""
    scan_dir = Path(base) if base else _DEFAULT_BASE
    profiles = scan_profiles(scan_dir)
    match = next((p for p in profiles if p.name == name), None)

    if match is None:
        console.print(f"[red]Profile '{name}' not found.[/red]")
        console.print("List profiles with: wdt profiles list")
        raise SystemExit(1)

    active = get_active_profile()
    is_active = active and str(match.path) in active

    console.print(f"[bold]Name:[/bold]   {match.name}")
    console.print(f"[bold]Path:[/bold]   {match.path}")
    console.print(f"[bold]Active:[/bold] {'yes' if is_active else 'no'}")

    for img in ("system.img", "vendor.img"):
        f = match.path / img
        if f.exists():
            size_mb = f.stat().st_size // (1024 * 1024)
            console.print(f"[bold]{img}:[/bold] {size_mb} MiB")
        else:
            console.print(f"[bold]{img}:[/bold] [yellow]missing[/yellow]")


@cmd.command("active")
def profiles_active() -> None:
    """Print the currently active profile path."""
    active = get_active_profile()
    if active:
        console.print(active)
    else:
        console.print("[yellow]No active profile set.[/yellow]")
        raise SystemExit(1)


@cmd.command("switch")
@click.argument("name")
@click.option("--base", default=None, help="Directory to scan for profiles.")
def profiles_switch(name: str, base: str | None) -> None:
    """Switch the active Waydroid image profile to NAME.

    Waydroid must be stopped before switching profiles.

    \b
    Examples:
      wdt profiles switch vanilla
      wdt profiles switch gapps --base ~/my-images
    """
    scan_dir = Path(base) if base else _DEFAULT_BASE
    profiles = scan_profiles(scan_dir)
    match = next((p for p in profiles if p.name == name), None)

    if match is None:
        console.print(f"[red]Profile '{name}' not found.[/red]")
        console.print("List profiles with: wdt profiles list")
        raise SystemExit(1)

    console.print(f"Switching to profile [bold]{name}[/bold]...")
    try:
        switch_profile(
            match,
            progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"),
        )
    except Exception as exc:
        console.print(f"[red]Switch failed: {exc}[/red]")
        raise SystemExit(1) from exc

    console.print(f"[green]Active profile: {name}[/green]")
    console.print(f"Path: {match.path}")


@cmd.command("add")
@click.argument("path")
@click.option("--name", "-n", default="",
              help="Profile name (default: directory basename).")
def profiles_add(path: str, name: str) -> None:
    """Register PATH as a named profile by symlinking it under ~/waydroid-images.

    PATH must contain system.img and vendor.img.

    \b
    Examples:
      wdt profiles add /mnt/external/waydroid-gapps
      wdt profiles add /mnt/external/waydroid-gapps --name gapps
    """
    src = Path(path).resolve()
    if not src.is_dir():
        console.print(f"[red]Not a directory: {src}[/red]")
        raise SystemExit(1)

    missing = [img for img in ("system.img", "vendor.img") if not (src / img).exists()]
    if missing:
        console.print(f"[yellow]Warning: missing in {src}: {', '.join(missing)}[/yellow]")

    profile_name = name or src.name
    dest = _DEFAULT_BASE / profile_name

    if dest.exists() or dest.is_symlink():
        console.print(f"[yellow]Profile '{profile_name}' already exists at {dest}[/yellow]")
        console.print("Remove it first or choose a different name with --name.")
        raise SystemExit(1)

    _DEFAULT_BASE.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(src)
    console.print(f"[green]Registered profile '{profile_name}'[/green]")
    console.print(f"  {dest} → {src}")
    console.print(f"Switch with: wdt profiles switch {profile_name}")
