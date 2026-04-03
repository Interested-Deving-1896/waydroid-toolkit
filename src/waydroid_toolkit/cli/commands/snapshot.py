"""wdt snapshot — filesystem-level snapshots via ZFS or btrfs."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group("snapshot")
def cmd() -> None:
    """Create, list, restore, and delete Waydroid snapshots."""


# ── auto subgroup ─────────────────────────────────────────────────────────────

@cmd.group("auto")
def snapshot_auto() -> None:
    """Manage automatic snapshot schedules (Incus backend only)."""


@snapshot_auto.command("set")
@click.argument("schedule")
@click.option("--expiry", default="",
              help="Auto-delete snapshots after this duration (e.g. 7d, 30d, 24h).")
@click.option("--pattern", default="snap-%d", show_default=True,
              help="Naming pattern for auto-snapshots (%d replaced by a counter).")
def auto_set(schedule: str, expiry: str, pattern: str) -> None:
    """Configure a cron-style schedule for automatic snapshots.

    SCHEDULE accepts cron expressions or shorthand:
    @hourly, @daily, @weekly, @monthly, or "0 6 * * *".
    """
    backend = _get_incus_backend()
    try:
        backend.snapshot_auto_set(schedule, expiry=expiry, pattern=pattern)
    except (RuntimeError, NotImplementedError) as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    console.print("[green]Auto-snapshot configured[/green]")
    console.print(f"  Schedule : {schedule}")
    console.print(f"  Pattern  : {pattern}")
    if expiry:
        console.print(f"  Expiry   : {expiry}")


@snapshot_auto.command("show")
def auto_show() -> None:
    """Display the current auto-snapshot schedule, expiry, and pattern."""
    backend = _get_incus_backend()
    try:
        info = backend.snapshot_auto_show()
    except (RuntimeError, NotImplementedError) as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    console.print(f"  Schedule : {info.get('schedule', '(not set)')}")
    console.print(f"  Expiry   : {info.get('expiry', '(not set)')}")
    console.print(f"  Pattern  : {info.get('pattern', '(not set)')}")


@snapshot_auto.command("disable")
def auto_disable() -> None:
    """Remove the automatic snapshot schedule."""
    backend = _get_incus_backend()
    try:
        backend.snapshot_auto_disable()
    except (RuntimeError, NotImplementedError) as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    console.print("[green]Auto-snapshot disabled.[/green]")


@cmd.command("create")
@click.argument("label", default="", required=False)
@click.option("--backend", type=click.Choice(["zfs", "btrfs", "auto"]),
              default="auto", show_default=True,
              help="Snapshot backend to use.")
def snapshot_create(label: str, backend: str) -> None:
    """Take a snapshot of the Waydroid data directory."""
    b = _get_backend(backend)
    try:
        info = b.create(label)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    console.print(f"[green]Snapshot created:[/green] {info.name}")
    console.print(f"  Backend : {info.backend}")
    console.print(f"  Source  : {info.source}")
    console.print(f"  Created : {info.created.strftime('%Y-%m-%d %H:%M:%S UTC')}")


@cmd.command("list")
@click.option("--backend", type=click.Choice(["zfs", "btrfs", "auto"]),
              default="auto", show_default=True)
def snapshot_list(backend: str) -> None:
    """List available snapshots."""
    b = _get_backend(backend)
    snaps = b.list()
    if not snaps:
        console.print("[yellow]No snapshots found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Created (UTC)")
    table.add_column("Backend")
    table.add_column("Source")
    table.add_column("Size")

    for s in snaps:
        size = f"{s.size_bytes // 1024 // 1024} MiB" if s.size_bytes else "—"
        table.add_row(
            s.name,
            s.created.strftime("%Y-%m-%d %H:%M:%S"),
            s.backend,
            s.source,
            size,
        )
    console.print(table)


@cmd.command("restore")
@click.argument("name")
@click.option("--backend", type=click.Choice(["zfs", "btrfs", "auto"]),
              default="auto", show_default=True)
@click.confirmation_option(
    prompt="This will overwrite the current Waydroid data. Continue?"
)
def snapshot_restore(name: str, backend: str) -> None:
    """Restore Waydroid data from a snapshot.

    The Waydroid session must be stopped before restoring.
    """
    b = _get_backend(backend)
    try:
        b.restore(name)
    except (RuntimeError, FileNotFoundError) as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    console.print(f"[green]Restored from snapshot:[/green] {name}")


@cmd.command("delete")
@click.argument("name")
@click.option("--backend", type=click.Choice(["zfs", "btrfs", "auto"]),
              default="auto", show_default=True)
@click.confirmation_option(prompt="Delete this snapshot permanently?")
def snapshot_delete(name: str, backend: str) -> None:
    """Delete a snapshot by name."""
    b = _get_backend(backend)
    try:
        b.delete(name)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    console.print(f"[green]Deleted snapshot:[/green] {name}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_backend(choice: str):  # type: ignore[return]
    from waydroid_toolkit.modules.snapshot import BtrfsBackend, ZfsBackend, get_backend

    if choice == "zfs":
        return ZfsBackend()
    if choice == "btrfs":
        return BtrfsBackend()
    try:
        return get_backend()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)


def _get_incus_backend():  # type: ignore[return]
    """Return the IncusBackend, or exit with an error if unavailable."""
    from waydroid_toolkit.core.container import IncusBackend

    backend = IncusBackend()
    if not backend.is_available():
        console.print(
            "[red]Auto-snapshot scheduling requires the Incus backend.[/red]\n"
            "Switch with: wdt backend switch incus"
        )
        raise SystemExit(1)
    return backend

