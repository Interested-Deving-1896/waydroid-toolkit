"""wdt upgrade — upgrade the Waydroid Android image (OTA).

Convenience wrapper around `wdt images check-update` + `wdt images download`
that also handles stopping/restarting the container and switching the active
profile to the newly downloaded images.

Sub-commands
------------
  wdt upgrade check    Check OTA channels for available updates
  wdt upgrade apply    Download and apply the latest images
"""

from __future__ import annotations

import subprocess

import click
from rich.console import Console

from waydroid_toolkit.core.waydroid import run_waydroid
from waydroid_toolkit.modules.images import (
    check_updates,
    download_updates,
    scan_profiles,
    switch_profile,
)

console = Console()


def _container_name() -> str:
    try:
        from waydroid_toolkit.core.container import get_active
        return get_active().get_info().container_name  # type: ignore[attr-defined]
    except Exception:
        return "waydroid"


def _waydroid_running() -> bool:
    try:
        from waydroid_toolkit.core.waydroid import SessionState, get_session_state
        return get_session_state() == SessionState.RUNNING
    except Exception:
        return False


@click.group("upgrade", invoke_without_command=True)
@click.pass_context
def cmd(ctx: click.Context) -> None:
    """Upgrade the Waydroid Android image via OTA.

    With no subcommand, checks for updates and prompts to apply them.

    \b
    Examples:
      wdt upgrade
      wdt upgrade check
      wdt upgrade apply
      wdt upgrade apply --yes
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(upgrade_check)


@cmd.command("check")
def upgrade_check() -> None:
    """Check OTA channels for available Waydroid image updates."""
    import urllib.error

    from rich.table import Table

    try:
        system_info, vendor_info = check_updates()
    except urllib.error.URLError as exc:
        console.print(f"[red]Network error: {exc}[/red]")
        raise SystemExit(1) from exc
    except Exception as exc:
        console.print(f"[red]Could not check for updates: {exc}[/red]")
        raise SystemExit(1) from exc
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Channel")
    table.add_column("Current build")
    table.add_column("Latest build")
    table.add_column("Status")

    any_available = False
    for info in (system_info, vendor_info):
        current = str(info.current_datetime) if info.current_datetime else "none"
        latest = str(info.latest.datetime) if info.latest else "unavailable"
        if info.update_available:
            status = "[green]update available[/green]"
            any_available = True
        elif info.latest is None:
            status = "[yellow]channel unavailable[/yellow]"
        else:
            status = "[dim]up to date[/dim]"
        table.add_row(info.channel, current, latest, status)

    console.print(table)

    if any_available:
        console.print()
        console.print("Apply with: [cyan]wdt upgrade apply[/cyan]")
    else:
        console.print("[green]Waydroid images are up to date.[/green]")


@cmd.command("apply")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.option("--dest", default=None,
              help="Directory to save downloaded images (default: ~/waydroid-images/ota).")
@click.option("--no-restart", is_flag=True,
              help="Do not restart Waydroid after applying the update.")
@click.option("--no-snapshot", is_flag=True,
              help="Skip the pre-upgrade backup snapshot.")
def upgrade_apply(yes: bool, dest: str | None, no_restart: bool, no_snapshot: bool) -> None:
    """Download and apply the latest Waydroid OTA images.

    Steps:
      1. Check for available updates
      2. Optionally snapshot the container
      3. Stop Waydroid if running
      4. Download new system + vendor images
      5. Switch the active profile to the new images
      6. Restart Waydroid (unless --no-restart)

    \b
    Examples:
      wdt upgrade apply
      wdt upgrade apply --yes
      wdt upgrade apply --no-restart
    """
    import urllib.error
    from pathlib import Path

    # 1. Check for updates
    console.print("Checking for updates...")
    try:
        system_info, vendor_info = check_updates()
    except urllib.error.URLError as exc:
        console.print(f"[red]Network error: {exc}[/red]")
        raise SystemExit(1) from exc
    except Exception as exc:
        console.print(f"[red]Could not check for updates: {exc}[/red]")
        raise SystemExit(1) from exc

    any_available = system_info.update_available or vendor_info.update_available
    if not any_available:
        console.print("[green]Already up to date — nothing to do.[/green]")
        return

    console.print("[green]Updates available.[/green]")
    if not yes:
        click.confirm("Download and apply updates now?", abort=True)

    ct = _container_name()

    # 2. Pre-upgrade snapshot
    if not no_snapshot:
        import datetime
        snap = f"pre-upgrade-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
        console.print(f"Creating snapshot [bold]{snap}[/bold]...")
        result = subprocess.run(
            ["incus", "snapshot", "create", ct, snap],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] Snapshot created: {snap}")
        else:
            console.print("  [yellow]⚠[/yellow] Snapshot failed — continuing anyway")

    # 3. Stop Waydroid if running
    was_running = _waydroid_running()
    if was_running:
        console.print("Stopping Waydroid session...")
        try:
            run_waydroid("session", "stop", sudo=True)
        except Exception:
            subprocess.run(["sudo", "waydroid", "session", "stop"],
                           capture_output=True)

    # 4. Download new images
    dest_dir = Path(dest) if dest else Path.home() / "waydroid-images" / "ota"
    console.print(f"Downloading images to [bold]{dest_dir}[/bold]...")
    try:
        system_path, vendor_path = download_updates(
            dest_dir=dest_dir,
            progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"),
            update_cfg=True,
        )
    except Exception as exc:
        console.print(f"[red]Download failed: {exc}[/red]")
        raise SystemExit(1) from exc

    if system_path:
        console.print(f"  [green]✓[/green] system.img: {system_path}")
    if vendor_path:
        console.print(f"  [green]✓[/green] vendor.img: {vendor_path}")

    # 5. Switch active profile to the new images
    if system_path or vendor_path:
        try:
            profiles = scan_profiles(dest_dir)
            if profiles:
                newest = profiles[0]
                console.print(f"Switching to profile [bold]{newest.name}[/bold]...")
                switch_profile(
                    newest,
                    progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"),
                )
                console.print(f"  [green]✓[/green] Active profile: {newest.name}")
        except Exception as exc:
            console.print(f"  [yellow]⚠[/yellow] Profile switch failed: {exc}")

    # 6. Restart
    if not no_restart and was_running:
        console.print("Restarting Waydroid...")
        try:
            run_waydroid("session", "start", sudo=True)
            console.print("  [green]✓[/green] Waydroid restarted")
        except Exception:
            console.print("  [yellow]⚠[/yellow] Could not restart automatically")
            console.print("  Start manually: sudo waydroid session start")

    console.print()
    console.print("[green]Upgrade complete.[/green]")
