"""wdt backup — backup and restore Waydroid data."""

from pathlib import Path

import click
from rich.console import Console

from waydroid_toolkit.modules.backup import (
    DEFAULT_BACKUP_DIR,
    create_backup,
    list_backups,
    restore_backup,
)

console = Console()


@click.group("backup")
def cmd() -> None:
    """Backup and restore Waydroid data."""


@cmd.command("create")
@click.option("--dest", default=None, help="Directory to store the backup archive.")
def backup_create(dest: str | None) -> None:
    """Create a compressed backup of all Waydroid data."""
    dest_path = Path(dest) if dest else DEFAULT_BACKUP_DIR
    archive = create_backup(
        dest_dir=dest_path,
        progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"),
    )
    console.print(f"[green]Backup saved to: {archive}[/green]")


@cmd.command("list")
@click.option("--dir", "backup_dir", default=None, help="Directory to list backups from.")
def backup_list(backup_dir: str | None) -> None:
    """List available backup archives."""
    path = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR
    archives = list_backups(path)
    if not archives:
        console.print("[yellow]No backups found.[/yellow]")
        return
    for i, a in enumerate(archives, 1):
        size_mb = a.stat().st_size / (1024 * 1024)
        console.print(f"  [bold]{i}.[/bold] {a.name}  ({size_mb:.1f} MB)")


@cmd.command("restore")
@click.argument("archive")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def backup_restore(archive: str, yes: bool) -> None:
    """Restore Waydroid data from a backup archive."""
    path = Path(archive)
    if not yes:
        click.confirm(
            f"This will overwrite current Waydroid data with '{path.name}'. Continue?",
            abort=True,
        )
    restore_backup(path, progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print("[green]Restore complete.[/green]")
