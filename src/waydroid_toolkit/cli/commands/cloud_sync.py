"""wdt cloud-sync — sync Waydroid container backups to cloud storage via rclone."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import click
from rich.console import Console

console = Console()

_DEFAULT_BACKUP_DIR = Path.home() / ".local" / "share" / "waydroid-toolkit" / "backups"
_DEFAULT_REMOTE = "wdt-backups"
_DEFAULT_PATH = "wdt/backups"


def _backup_dir() -> Path:
    return Path(os.environ.get("WDT_BACKUP_DIR", str(_DEFAULT_BACKUP_DIR)))


def _remote_name() -> str:
    return os.environ.get("WDT_CLOUD_REMOTE", _DEFAULT_REMOTE)


def _remote_path() -> str:
    return os.environ.get("WDT_CLOUD_PATH", _DEFAULT_PATH)


def _require_rclone() -> None:
    if shutil.which("rclone") is None:
        console.print("[red]rclone is required for cloud sync.[/red]")
        console.print("Install: https://rclone.org/install/")
        raise SystemExit(1)


def _remote_configured() -> bool:
    result = subprocess.run(
        ["rclone", "listremotes"],
        capture_output=True, text=True,
    )
    return f"{_remote_name()}:" in result.stdout


@click.group("cloud-sync")
def cmd() -> None:
    """Sync Waydroid container backups to cloud storage via rclone."""


@cmd.command("push")
@click.argument("filter_str", metavar="[FILTER]", default="", required=False)
def cloud_push(filter_str: str) -> None:
    """Upload local backups to the configured remote.

    FILTER optionally restricts upload to filenames containing the given string.
    """
    _require_rclone()
    backup_dir = _backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not _remote_configured():
        console.print(f"[red]Remote '{_remote_name()}' not configured.[/red]")
        console.print("Run: wdt cloud-sync config")
        raise SystemExit(1)

    remote = f"{_remote_name()}:{_remote_path()}/"
    console.print("[bold]Cloud Sync: Push[/bold]")
    console.print(f"  Local  : {backup_dir}")
    console.print(f"  Remote : {remote}")

    count = 0
    for pattern in ("*.tar.gz", "*.tar"):
        for f in backup_dir.glob(pattern):
            if filter_str and filter_str not in f.name:
                continue
            size_mb = f.stat().st_size / (1024 * 1024)
            console.print(f"  Uploading: {f.name} ({size_mb:.1f} MiB)")
            result = subprocess.run(
                ["rclone", "copy", str(f), remote, "--progress", "--transfers", "1"],
            )
            if result.returncode != 0:
                console.print(f"[yellow]Failed to upload: {f.name}[/yellow]")
                continue
            count += 1

    for f in backup_dir.glob("*.meta"):
        subprocess.run(["rclone", "copy", str(f), remote], capture_output=True)

    if count == 0:
        console.print("[yellow]No backups to upload.[/yellow]")
    else:
        console.print(f"[green]Uploaded {count} backup(s).[/green]")


@cmd.command("pull")
@click.argument("filter_str", metavar="[FILTER]", default="", required=False)
def cloud_pull(filter_str: str) -> None:
    """Download remote backups to the local backup directory.

    FILTER optionally restricts download to filenames containing the given string.
    """
    _require_rclone()
    backup_dir = _backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    if not _remote_configured():
        console.print(f"[red]Remote '{_remote_name()}' not configured.[/red]")
        console.print("Run: wdt cloud-sync config")
        raise SystemExit(1)

    remote = f"{_remote_name()}:{_remote_path()}/"
    console.print("[bold]Cloud Sync: Pull[/bold]")
    console.print(f"  Remote : {remote}")
    console.print(f"  Local  : {backup_dir}")

    pull_cmd = ["rclone", "copy", remote, str(backup_dir), "--progress", "--transfers", "1"]
    if filter_str:
        pull_cmd += ["--include", f"*{filter_str}*"]

    result = subprocess.run(pull_cmd)
    if result.returncode != 0:
        console.print("[red]Pull failed.[/red]")
        raise SystemExit(1)

    console.print("[green]Pull complete.[/green]")


@cmd.command("list")
def cloud_list() -> None:
    """List backups stored on the remote."""
    _require_rclone()

    if not _remote_configured():
        console.print(f"[red]Remote '{_remote_name()}' not configured.[/red]")
        console.print("Run: wdt cloud-sync config")
        raise SystemExit(1)

    remote = f"{_remote_name()}:{_remote_path()}/"
    console.print(f"[bold]Remote Backups:[/bold] {remote}")
    console.print()

    result = subprocess.run(
        ["rclone", "lsf", remote, "--format", "psm"],
        capture_output=True, text=True,
    )
    rows = []
    for line in result.stdout.splitlines():
        parts = line.split(";", 2)
        if len(parts) < 3:
            continue
        path, size, mod = parts
        if path.endswith(".meta"):
            continue
        rows.append((path, size, mod))

    if rows:
        console.print(f"  {'FILENAME':<40} {'SIZE':<12} MODIFIED")
        console.print(f"  {'--------':<40} {'----':<12} --------")
        for path, size, mod in rows:
            console.print(f"  {path:<40} {size:<12} {mod}")
    else:
        console.print("[yellow]  No remote backups found.[/yellow]")

    backup_dir = _backup_dir()
    local_count = len(list(backup_dir.glob("*.tar*"))) if backup_dir.exists() else 0
    remote_count = len(rows)
    console.print()
    console.print(f"  Local: {local_count} backups | Remote: {remote_count} backups")


@cmd.group("config")
def cloud_config() -> None:
    """Configure the rclone remote for cloud sync."""


@cloud_config.command("show")
def config_show() -> None:
    """Show current cloud sync configuration."""
    console.print("[bold]Cloud Sync Configuration[/bold]")
    console.print(f"  Remote name : {_remote_name()}")
    console.print(f"  Remote path : {_remote_path()}")
    console.print(f"  Local dir   : {_backup_dir()}")
    if _remote_configured():
        console.print(f"[green]Remote '{_remote_name()}' is configured.[/green]")
    else:
        console.print(f"[yellow]Remote '{_remote_name()}' is not configured.[/yellow]")
        console.print("Run: wdt cloud-sync config s3  (or b2 / interactive)")


@cloud_config.command("s3")
def config_s3() -> None:
    """Configure an S3-compatible remote interactively via rclone."""
    _require_rclone()
    console.print("[dim]Configuring S3-compatible remote...[/dim]")
    result = subprocess.run(
        ["rclone", "config", "create", _remote_name(), "s3",
         "provider", "AWS", "env_auth", "false"],
    )
    if result.returncode != 0:
        console.print("[red]S3 config failed.[/red]")
        raise SystemExit(1)
    console.print(f"[green]S3 remote configured as '{_remote_name()}'.[/green]")


@cloud_config.command("b2")
def config_b2() -> None:
    """Configure a Backblaze B2 remote interactively via rclone."""
    _require_rclone()
    console.print("[dim]Configuring Backblaze B2 remote...[/dim]")
    result = subprocess.run(["rclone", "config", "create", _remote_name(), "b2"])
    if result.returncode != 0:
        console.print("[red]B2 config failed.[/red]")
        raise SystemExit(1)
    console.print(f"[green]B2 remote configured as '{_remote_name()}'.[/green]")


@cloud_config.command("interactive")
def config_interactive() -> None:
    """Launch rclone interactive config (alias: setup)."""
    _require_rclone()
    console.print(f"[dim]Create a remote named: {_remote_name()}[/dim]")
    subprocess.run(["rclone", "config"])


@cmd.command("status")
def cloud_status() -> None:
    """Show sync status: local vs remote backup counts."""
    _require_rclone()
    console.print("[bold]Cloud Sync Status[/bold]")

    if not _remote_configured():
        console.print(f"[yellow]Remote '{_remote_name()}' not configured.[/yellow]")
        console.print("Run: wdt cloud-sync config")
        raise SystemExit(1)

    console.print(f"[green]Remote:[/green] {_remote_name()} (configured)")
    console.print(f"  Path: {_remote_path()}")

    backup_dir = _backup_dir()
    local_count = len(list(backup_dir.glob("*.tar*"))) if backup_dir.exists() else 0
    remote = f"{_remote_name()}:{_remote_path()}/"
    remote_result = subprocess.run(
        ["rclone", "lsf", remote, "--include", "*.tar*"],
        capture_output=True, text=True,
    )
    remote_files = set(remote_result.stdout.splitlines())
    remote_count = len(remote_files)

    console.print(f"  Local backups  : {local_count}")
    console.print(f"  Remote backups : {remote_count}")

    unsynced = 0
    if backup_dir.exists():
        for f in list(backup_dir.glob("*.tar.gz")) + list(backup_dir.glob("*.tar")):
            if f.name not in remote_files:
                unsynced += 1

    if unsynced > 0:
        console.print(f"[yellow]{unsynced} local backup(s) not yet synced.[/yellow]")
        console.print("Run: wdt cloud-sync push")
    else:
        console.print("[green]All local backups synced.[/green]")

