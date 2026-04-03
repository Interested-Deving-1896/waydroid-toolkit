"""wdt container — Incus-level container lifecycle operations.

These commands operate on the Waydroid container via the active backend.
Snapshot, console, export, and import operations require the Incus backend;
they raise a clear error when the LXC backend is active.
"""

from __future__ import annotations

from pathlib import Path

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
    """Manage the Waydroid container (start, stop, list, snapshot, console)."""


# ── start / stop / list ───────────────────────────────────────────────────────

@cmd.command("start")
def container_start() -> None:
    """Start the Waydroid container."""
    import subprocess
    b = _backend()
    ct = b.get_info().container_name  # type: ignore[attr-defined]
    console.print(f"Starting container [bold]{ct}[/bold] ...")
    r = subprocess.run(["incus", "start", ct])
    if r.returncode != 0:
        console.print(f"[red]Failed to start '{ct}'.[/red]")
        raise SystemExit(1)
    console.print(f"[green]Started:[/green] {ct}")


@cmd.command("stop")
@click.option("--force", is_flag=True, help="Force-stop (incus stop --force).")
def container_stop(force: bool) -> None:
    """Stop the Waydroid container."""
    import subprocess
    b = _backend()
    ct = b.get_info().container_name  # type: ignore[attr-defined]
    console.print(f"Stopping container [bold]{ct}[/bold] ...")
    cmd_args = ["incus", "stop", ct]
    if force:
        cmd_args.append("--force")
    r = subprocess.run(cmd_args)
    if r.returncode != 0:
        console.print(f"[red]Failed to stop '{ct}'.[/red]")
        raise SystemExit(1)
    console.print(f"[green]Stopped:[/green] {ct}")


@cmd.command("list")
def container_list() -> None:
    """List Waydroid containers managed by the active backend."""
    import json
    import subprocess

    from rich.table import Table

    r = subprocess.run(
        ["incus", "list", "--format", "json"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        console.print("[yellow]Could not query Incus.[/yellow]")
        raise SystemExit(1)

    try:
        instances = json.loads(r.stdout)
    except json.JSONDecodeError:
        instances = []

    containers = [i for i in instances if i.get("type") == "container"]
    if not containers:
        console.print("[yellow]No containers found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("NAME", style="cyan")
    table.add_column("STATUS")
    table.add_column("IPV4")
    for inst in containers:
        name = inst.get("name", "")
        status = inst.get("status", "unknown")
        status_str = f"[green]{status}[/green]" if status == "Running" else status
        ip = "-"
        for iface in inst.get("state", {}).get("network", {}).values():
            for addr in iface.get("addresses", []):
                if addr.get("family") == "inet" and not addr["address"].startswith("127."):
                    ip = addr["address"]
                    break
            if ip != "-":
                break
        table.add_row(name, status_str, ip)
    console.print(table)


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


@cmd.group("snapshot-auto")
def container_snapshot_auto() -> None:
    """Manage automatic snapshot schedules for the Waydroid container."""


@container_snapshot_auto.command("set")
@click.argument("schedule")
@click.option("--expiry", default="", help="Auto-delete after duration (e.g. 7d, 30d).")
@click.option("--pattern", default="snap-%d", show_default=True, help="Snapshot naming pattern.")
def snapshot_auto_set(schedule: str, expiry: str, pattern: str) -> None:
    """Set an automatic snapshot schedule.

    SCHEDULE accepts cron expressions or shorthand (@daily, @weekly, etc.).
    """
    b = _backend()
    try:
        b.snapshot_auto_set(schedule, expiry, pattern)  # type: ignore[attr-defined]
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    console.print(f"[green]Auto-snapshot configured:[/green] {schedule}")
    if expiry:
        console.print(f"  Expiry  : {expiry}")
    console.print(f"  Pattern : {pattern}")


@container_snapshot_auto.command("show")
def snapshot_auto_show() -> None:
    """Show the current automatic snapshot schedule."""
    b = _backend()
    try:
        cfg = b.snapshot_auto_show()  # type: ignore[attr-defined]
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    console.print(f"  Schedule : {cfg.get('snapshots.schedule', '(not set)')}")
    console.print(f"  Expiry   : {cfg.get('snapshots.expiry', '(not set)')}")
    console.print(f"  Pattern  : {cfg.get('snapshots.pattern', '(not set)')}")


@container_snapshot_auto.command("disable")
def snapshot_auto_disable() -> None:
    """Remove the automatic snapshot schedule."""
    b = _backend()
    try:
        b.snapshot_auto_disable()  # type: ignore[attr-defined]
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    console.print("[green]Auto-snapshot disabled.[/green]")


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


# ── export ────────────────────────────────────────────────────────────────────

@cmd.command("export")
@click.option("--alias", "-a", default="", help="Image alias (default: waydroid-<timestamp>)")
@click.option(
    "--output", "-o",
    default="",
    help="Also export image to a file at this path.",
)
def container_export(alias: str, output: str) -> None:
    """Publish the Waydroid container as a reusable Incus image.

    Requires the Incus backend. The container is stopped temporarily
    if running, then published. Use the alias with 'incus init' to
    create new containers from the image.
    """
    import datetime
    import subprocess

    b = _backend()
    info = b.get_info()  # type: ignore[attr-defined]
    container_name = info.container_name

    if not alias:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        alias = f"waydroid-{ts}"

    try:
        result = subprocess.run(
            ["incus", "info", container_name, "--format", "json"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            console.print(f"[red]Container '{container_name}' not found[/red]")
            raise SystemExit(1)

        import json as _json
        data = _json.loads(result.stdout)
        was_running = data.get("status", "").lower() == "running"

        if was_running:
            console.print(f"[dim]Stopping '{container_name}' for export...[/dim]")
            subprocess.run(["incus", "stop", container_name], check=True)

        console.print(f"Publishing [bold]{container_name}[/bold] as image [bold]{alias}[/bold] ...")
        subprocess.run(["incus", "publish", container_name, "--alias", alias], check=True)
        console.print(f"[green]Published:[/green] {alias}")

        if output:
            console.print(f"Exporting image to file: {output} ...")
            subprocess.run(["incus", "image", "export", alias, output], check=True)
            console.print(f"[green]Image file:[/green] {output}")

        if was_running:
            subprocess.run(["incus", "start", container_name], check=True)

    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Command failed:[/red] {exc}")
        raise SystemExit(1) from exc


# ── import ────────────────────────────────────────────────────────────────────

@cmd.command("import")
@click.option(
    "--from", "source",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Image file to import.",
)
@click.option("--alias", "-a", default="", help="Alias to assign to the imported image.")
def container_import(source: Path, alias: str) -> None:
    """Import an Incus image from a file.

    After importing, create a new container with:
      incus init <alias> <name>

    Requires the Incus backend.
    """
    import subprocess

    _backend()  # ensure backend is available

    import_cmd = ["incus", "image", "import", str(source)]
    if alias:
        import_cmd += ["--alias", alias]

    console.print(f"Importing image from [bold]{source}[/bold] ...")
    try:
        subprocess.run(import_cmd, check=True)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Import failed:[/red] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[green]Image imported[/green]{f': {alias}' if alias else ''}")
    console.print(f"  Create a container: incus init {alias or '<alias>'} <name>")
