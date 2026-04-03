"""wdt storage — manage shared storage for the Waydroid container.

Ported from canonical/anbox-cloud-nfs-operator (Apache-2.0).
The Juju subordinate charm that mounted NFS into LXD-hosted Anbox containers
is replaced here with direct incus config device commands.

Sub-commands
------------
  wdt storage nfs add    -- attach an NFS share as an Incus disk device
  wdt storage nfs remove -- detach a disk device by name
  wdt storage nfs list   -- list all disk devices on the container
"""

from __future__ import annotations

import subprocess

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.modules.storage.nfs import (
    NfsMount,
    add_nfs_mount,
    list_nfs_mounts,
    remove_nfs_mount,
)

console = Console()


@click.group("storage")
def cmd() -> None:
    """Manage shared storage for the Waydroid container."""


# ── nfs ──────────────────────────────────────────────────────────────────────

@cmd.group("nfs")
def storage_nfs() -> None:
    """Mount and unmount NFS/EFS shares inside the Waydroid container.

    Uses incus config device add/remove under the hood.
    Equivalent to the anbox-cloud-nfs-operator Juju charm, without Juju.
    """


@storage_nfs.command("add")
@click.argument("source")
@click.option(
    "--path", "container_path",
    default="/data/shared",
    show_default=True,
    help="Mount point inside the container.",
)
@click.option(
    "--name", "device_name",
    default="",
    help="Incus device name (default: nfs-<source>).",
)
@click.option(
    "--type", "mount_type",
    default="nfs",
    type=click.Choice(["nfs", "efs", "disk"]),
    show_default=True,
    help="Mount type: nfs, efs (AWS EFS), or disk (local bind).",
)
@click.option(
    "--options",
    default="soft,async",
    show_default=True,
    help="Extra mount options passed via raw.mount.options.",
)
def nfs_add(
    source: str,
    container_path: str,
    device_name: str,
    mount_type: str,
    options: str,
) -> None:
    """Attach SOURCE as a shared disk device inside the Waydroid container.

    SOURCE is an NFS path (host:/export), an EFS filesystem ID, or a local
    directory path for bind mounts.

    Examples:

    \b
      # NFS share
      wdt storage nfs add 192.168.1.10:/exports/assets

    \b
      # AWS EFS
      wdt storage nfs add fs-0abc1234:/ --type efs --options tls

    \b
      # Local bind mount
      wdt storage nfs add /mnt/gamedata --type disk --path /data/games
    """
    console.print(f"Attaching [bold]{source}[/bold] → container:[bold]{container_path}[/bold]")
    try:
        mount = add_nfs_mount(
            source=source,
            container_path=container_path,
            device_name=device_name,
            mount_type=mount_type,
            extra_options=options,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]incus command failed:[/red] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[green]Mounted:[/green] {mount.device_name}")
    console.print(f"  Source    : {mount.source}")
    console.print(f"  Path      : {mount.container_path}")
    console.print(f"  Type      : {mount.mount_type}")
    if mount.options:
        console.print(f"  Options   : {mount.options}")
    console.print()
    console.print(f"Remove with: wdt storage nfs remove {mount.device_name}")


@storage_nfs.command("remove")
@click.argument("device_name")
@click.confirmation_option(prompt="Remove this storage device from the container?")
def nfs_remove(device_name: str) -> None:
    """Remove a disk device DEVICE_NAME from the Waydroid container."""
    try:
        remove_nfs_mount(device_name)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]incus command failed:[/red] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[green]Removed storage device:[/green] {device_name}")


@storage_nfs.command("list")
def nfs_list() -> None:
    """List all disk devices attached to the Waydroid container."""
    mounts = list_nfs_mounts()
    if not mounts:
        console.print("[yellow]No disk devices attached.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("DEVICE", style="cyan")
    table.add_column("SOURCE")
    table.add_column("CONTAINER PATH")
    table.add_column("OPTIONS")

    for m in mounts:
        table.add_row(m.device_name, m.source, m.container_path, m.options or "-")

    console.print(table)
