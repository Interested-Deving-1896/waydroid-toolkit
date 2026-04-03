"""wdt container — Incus-level container lifecycle operations.

These commands operate on the Waydroid container via the active backend.
Snapshot and console operations require the Incus backend; they raise a
clear error when the LXC backend is active.
"""

from __future__ import annotations

import click
from rich.console import Console

from waydroid_toolkit.core.container import get_active as get_backend

console = Console()


def _backend() -> object:
    try:
        return get_backend()
    except RuntimeError as exc:
        console.print(f"[red]No backend available: {exc}[/red]")
        raise SystemExit(1) from exc


@click.group("container")
def cmd() -> None:
    """Manage the Waydroid container (snapshot, console)."""


# ── snapshot ──────────────────────────────────────────────────────────────────

@cmd.group("snapshot")
def container_snapshot() -> None:
    """Create, list, restore, and delete container snapshots."""


@container_snapshot.command("create")
@click.argument("name", default="", required=False)
def snapshot_create(name: str) -> None:
    """Take a snapshot of the Waydroid container.

    NAME defaults to snap-<timestamp> when omitted.
    """
    import datetime
    snap = name or f"snap-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    b = _backend()
    try:
        b.snapshot_create(snap)  # type: ignore[attr-defined]
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    console.print(f"[green]Snapshot created:[/green] {snap}")


@container_snapshot.command("list")
def snapshot_list() -> None:
    """List snapshots of the Waydroid container."""
    b = _backend()
    try:
        names = b.snapshot_list()  # type: ignore[attr-defined]
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    if not names:
        console.print("[yellow]No snapshots found.[/yellow]")
        return
    for n in names:
        console.print(f"  {n}")


@container_snapshot.command("restore")
@click.argument("name")
@click.confirmation_option(
    prompt="This will overwrite the current container state. Continue?"
)
def snapshot_restore(name: str) -> None:
    """Restore the Waydroid container to a snapshot."""
    b = _backend()
    try:
        b.snapshot_restore(name)  # type: ignore[attr-defined]
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    console.print(f"[green]Restored to snapshot:[/green] {name}")


@container_snapshot.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Delete this snapshot permanently?")
def snapshot_delete(name: str) -> None:
    """Delete a container snapshot by name."""
    b = _backend()
    try:
        b.snapshot_delete(name)  # type: ignore[attr-defined]
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    console.print(f"[green]Deleted snapshot:[/green] {name}")


# ── console ───────────────────────────────────────────────────────────────────

@cmd.command("console")
def container_console() -> None:
    """Attach to the Waydroid container console interactively.

    Requires the Incus backend. Press Ctrl-a q to detach.
    """
    b = _backend()
    try:
        b.console()  # type: ignore[attr-defined]
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
