"""wdt maintenance — display, screenshots, logcat, file transfer, debloat."""

from pathlib import Path

import click
from rich.console import Console

from waydroid_toolkit.modules.maintenance import (
    clear_app_data, debloat, freeze_app, get_device_info,
    launch_app, pull_file, push_file, record_screen,
    reset_display, set_density, set_resolution, stream_logcat,
    take_screenshot, unfreeze_app,
)

console = Console()


@click.group("maintenance")
def cmd() -> None:
    """Display settings, screenshots, logcat, file transfer, and app tools."""


# ── Display ───────────────────────────────────────────────────────────────────

@cmd.command("set-resolution")
@click.argument("width", type=int)
@click.argument("height", type=int)
def cmd_set_res(width: int, height: int) -> None:
    """Set the Waydroid display resolution (e.g. 1280 720)."""
    set_resolution(width, height)
    console.print(f"[green]Resolution set to {width}x{height}. Restart Waydroid to apply.[/green]")


@cmd.command("set-density")
@click.argument("dpi", type=int)
def cmd_set_dpi(dpi: int) -> None:
    """Set the Waydroid display density in DPI."""
    set_density(dpi)
    console.print(f"[green]Density set to {dpi} DPI. Restart Waydroid to apply.[/green]")


@cmd.command("reset-display")
def cmd_reset_display() -> None:
    """Reset display resolution and density to Waydroid defaults."""
    reset_display()
    console.print("[green]Display settings reset.[/green]")


# ── Device info ───────────────────────────────────────────────────────────────

@cmd.command("info")
def cmd_info() -> None:
    """Show Android device information via ADB."""
    info = get_device_info()
    for key, value in info.items():
        console.print(f"  [bold cyan]{key:<20}[/bold cyan] {value}")


# ── Screenshot / recording ────────────────────────────────────────────────────

@cmd.command("screenshot")
@click.option("--dest", default=None, help="Output file path.")
def cmd_screenshot(dest: str | None) -> None:
    """Capture a screenshot from Waydroid."""
    path = take_screenshot(Path(dest) if dest else None)
    console.print(f"[green]Screenshot saved: {path}[/green]")


@cmd.command("record")
@click.option("--dest", default=None, help="Output file path.")
@click.option("--duration", default=60, show_default=True, help="Max recording duration in seconds.")
def cmd_record(dest: str | None, duration: int) -> None:
    """Record the Waydroid screen."""
    path = record_screen(Path(dest) if dest else None, duration_seconds=duration)
    console.print(f"[green]Recording saved: {path}[/green]")


# ── File transfer ─────────────────────────────────────────────────────────────

@cmd.command("push")
@click.argument("local_path")
@click.argument("android_dest")
def cmd_push(local_path: str, android_dest: str) -> None:
    """Push a file from the host to Waydroid (e.g. /sdcard/file.txt)."""
    push_file(Path(local_path), android_dest)
    console.print("[green]File pushed.[/green]")


@cmd.command("pull")
@click.argument("android_src")
@click.argument("local_dest")
def cmd_pull(android_src: str, local_dest: str) -> None:
    """Pull a file from Waydroid to the host."""
    pull_file(android_src, Path(local_dest))
    console.print("[green]File pulled.[/green]")


# ── Logcat ────────────────────────────────────────────────────────────────────

@cmd.command("logcat")
@click.option("--tag", default=None, help="Filter by log tag.")
@click.option("--errors", is_flag=True, help="Show errors only.")
def cmd_logcat(tag: str | None, errors: bool) -> None:
    """Stream Waydroid logcat output. Press Ctrl+C to stop."""
    console.print("[dim]Streaming logcat — Ctrl+C to stop[/dim]")
    try:
        for line in stream_logcat(tag=tag, errors_only=errors):
            console.print(line)
    except KeyboardInterrupt:
        pass


# ── App tools ─────────────────────────────────────────────────────────────────

@cmd.command("freeze")
@click.argument("package")
def cmd_freeze(package: str) -> None:
    """Disable an app without uninstalling it."""
    freeze_app(package)
    console.print(f"[green]{package} frozen.[/green]")


@cmd.command("unfreeze")
@click.argument("package")
def cmd_unfreeze(package: str) -> None:
    """Re-enable a previously frozen app."""
    unfreeze_app(package)
    console.print(f"[green]{package} unfrozen.[/green]")


@cmd.command("clear-data")
@click.argument("package")
@click.option("--cache-only", is_flag=True, help="Clear only the app cache.")
def cmd_clear_data(package: str, cache_only: bool) -> None:
    """Clear app data or cache for a package."""
    clear_app_data(package, cache_only=cache_only)
    console.print(f"[green]{'Cache' if cache_only else 'Data'} cleared for {package}.[/green]")


@cmd.command("launch")
@click.argument("package")
def cmd_launch(package: str) -> None:
    """Launch an installed Android app by package name."""
    launch_app(package)


@cmd.command("debloat")
@click.option("--packages", "-p", multiple=True,
              help="Package names to remove. Repeatable. Defaults to common LineageOS bloat.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def cmd_debloat(packages: tuple[str, ...], yes: bool) -> None:
    """Remove bloatware from the Waydroid Android image."""
    from waydroid_toolkit.modules.maintenance.tools import DEFAULT_BLOAT
    targets = list(packages) or DEFAULT_BLOAT
    if not yes:
        console.print("Will remove:")
        for p in targets:
            console.print(f"  {p}")
        click.confirm("Continue?", abort=True)
    removed = debloat(targets, progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print(f"[green]Removed {len(removed)} package(s).[/green]")
