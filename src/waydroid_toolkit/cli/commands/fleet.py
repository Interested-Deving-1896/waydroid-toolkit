"""wdt fleet — multi-instance Waydroid orchestration.

Operates on all Waydroid containers managed by the active backend at once.

Sub-commands
------------
  wdt fleet list        List all Waydroid instances
  wdt fleet start-all   Start all stopped instances
  wdt fleet stop-all    Stop all running instances
  wdt fleet backup-all  Backup all instances
  wdt fleet status      Show status summary for all instances
  wdt fleet exec CMD    Run a shell command in every running instance
"""

from __future__ import annotations

import subprocess

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _all_instances() -> list[dict]:
    """Return all Incus instances that look like Waydroid containers."""
    import json

    result = subprocess.run(
        ["incus", "list", "--format", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    try:
        instances = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    # Filter to waydroid containers (name contains 'waydroid' or type container)
    return [i for i in instances if i.get("type") == "container"]


def _running(instances: list[dict]) -> list[str]:
    return [i["name"] for i in instances if i.get("status") == "Running"]


def _stopped(instances: list[dict]) -> list[str]:
    return [i["name"] for i in instances if i.get("status") != "Running"]


@click.group("fleet")
def cmd() -> None:
    """Multi-instance Waydroid orchestration."""


@cmd.command("list")
def fleet_list() -> None:
    """List all Waydroid container instances."""
    instances = _all_instances()
    if not instances:
        console.print("[yellow]No instances found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("NAME", style="cyan")
    table.add_column("STATUS")
    table.add_column("IPV4")
    table.add_column("TYPE")

    for inst in instances:
        name = inst["name"]
        status = inst.get("status", "?")
        status_fmt = f"[green]{status}[/green]" if status == "Running" else status
        ipv4 = ""
        for net in inst.get("state", {}).get("network", {}).values():
            for addr in net.get("addresses", []):
                if addr.get("family") == "inet" and not addr["address"].startswith("127."):
                    ipv4 = addr["address"]
                    break
        table.add_row(name, status_fmt, ipv4, inst.get("type", "?"))

    console.print(table)


@cmd.command("start-all")
def fleet_start_all() -> None:
    """Start all stopped Waydroid instances."""
    instances = _all_instances()
    stopped = _stopped(instances)
    if not stopped:
        console.print("[yellow]No stopped instances.[/yellow]")
        return
    for name in stopped:
        console.print(f"Starting [bold]{name}[/bold]...")
        result = subprocess.run(["incus", "start", name], capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] {name}")
        else:
            console.print(f"  [red]✗[/red] {name}: {result.stderr.strip()}")


@cmd.command("stop-all")
@click.option("--force", is_flag=True, help="Force-stop (kill) instead of graceful shutdown.")
def fleet_stop_all(force: bool) -> None:
    """Stop all running Waydroid instances."""
    instances = _all_instances()
    running = _running(instances)
    if not running:
        console.print("[yellow]No running instances.[/yellow]")
        return
    for name in running:
        console.print(f"Stopping [bold]{name}[/bold]...")
        cmd_args = ["incus", "stop", name]
        if force:
            cmd_args.append("--force")
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] {name}")
        else:
            console.print(f"  [red]✗[/red] {name}: {result.stderr.strip()}")


@cmd.command("backup-all")
@click.option("--dir", "backup_dir", default="", help="Backup destination directory.")
def fleet_backup_all(backup_dir: str) -> None:
    """Create backups of all Waydroid instances."""
    from pathlib import Path

    instances = _all_instances()
    if not instances:
        console.print("[yellow]No instances found.[/yellow]")
        return

    dest = Path(backup_dir) if backup_dir else Path.home() / ".local/share/waydroid-toolkit/backups"
    dest.mkdir(parents=True, exist_ok=True)

    ok_count = 0
    fail_count = 0
    for inst in instances:
        name = inst["name"]
        console.print(f"Backing up [bold]{name}[/bold]...")
        result = subprocess.run(
            ["incus", "export", name, str(dest / f"{name}.tar.gz"), "--optimized-storage"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            console.print(f"  [green]✓[/green] {name}")
            ok_count += 1
        else:
            console.print(f"  [red]✗[/red] {name}: {result.stderr.strip()}")
            fail_count += 1

    console.print()
    console.print(f"Done: {ok_count} succeeded, {fail_count} failed")
    console.print(f"Backups in: {dest}")


@cmd.command("status")
def fleet_status() -> None:
    """Show a status summary for all Waydroid instances."""
    instances = _all_instances()
    if not instances:
        console.print("[yellow]No instances found.[/yellow]")
        return

    running = _running(instances)
    stopped = _stopped(instances)
    console.print(f"Total: [bold]{len(instances)}[/bold]  "
                  f"Running: [green]{len(running)}[/green]  "
                  f"Stopped: [yellow]{len(stopped)}[/yellow]")
    console.print()
    fleet_list.invoke(click.Context(fleet_list))


@cmd.command("exec")
@click.argument("command", nargs=-1, required=True)
@click.option("--all", "all_instances", is_flag=True, default=True,
              help="Run in all instances (default).")
def fleet_exec(command: tuple, all_instances: bool) -> None:
    """Run COMMAND in every running Waydroid instance.

    \b
    Example:
      wdt fleet exec -- waydroid status
      wdt fleet exec -- sh -c 'echo hello'
    """
    instances = _all_instances()
    running = _running(instances)
    if not running:
        console.print("[yellow]No running instances.[/yellow]")
        return

    cmd_list = list(command)
    for name in running:
        console.print(f"[bold]{name}[/bold]:")
        result = subprocess.run(
            ["incus", "exec", name, "--"] + cmd_list,
            capture_output=True, text=True,
        )
        if result.stdout:
            console.print(result.stdout.rstrip())
        if result.returncode != 0 and result.stderr:
            console.print(f"  [red]{result.stderr.strip()}[/red]")
