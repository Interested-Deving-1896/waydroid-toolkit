"""wdt publish — create an Incus image from the Waydroid container.

Publishes the stopped Waydroid container as a reusable Incus image.
The image can be used to create new containers or shared via an Incus remote.

Sub-commands
------------
  wdt publish create   Publish the container as an image
  wdt publish list     List published Waydroid images
  wdt publish delete   Delete a published image by alias
"""

from __future__ import annotations

import subprocess

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _container_name() -> str:
    try:
        from waydroid_toolkit.core.container import get_active as get_backend
        return get_backend().get_info().container_name  # type: ignore[attr-defined]
    except Exception:
        return "waydroid"


@click.group("publish")
def cmd() -> None:
    """Create and manage Incus images from the Waydroid container."""


@cmd.command("create")
@click.option("--alias", "-a", default="", help="Image alias (default: waydroid/published).")
@click.option("--description", "-d", default="", help="Image description.")
@click.option("--force-stop", is_flag=True,
              help="Stop the container before publishing if running.")
def publish_create(alias: str, description: str, force_stop: bool) -> None:
    """Publish the Waydroid container as a reusable Incus image.

    The container must be stopped. Use --force-stop to stop it automatically.

    \b
    Examples:
      wdt publish create
      wdt publish create --alias waydroid/gapps-v1
      wdt publish create --force-stop
    """
    ct = _container_name()
    alias = alias or "waydroid/published"

    # Check running state
    result = subprocess.run(
        ["incus", "list", "--format", "csv", "-c", "ns", ct],
        capture_output=True, text=True,
    )
    is_running = "RUNNING" in result.stdout

    if is_running:
        if force_stop:
            console.print(f"Stopping [bold]{ct}[/bold]...")
            subprocess.run(["incus", "stop", ct], check=True)
        else:
            console.print(f"[red]{ct} is running.[/red] Stop it first or use --force-stop")
            raise SystemExit(1)

    console.print(f"Publishing [bold]{ct}[/bold] as [bold]{alias}[/bold]...")
    cmd_args = ["incus", "publish", ct, "--alias", alias]
    if description:
        cmd_args += ["--compression", "gzip"]

    try:
        subprocess.run(cmd_args, check=True)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Publish failed:[/red] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[green]Published:[/green] {alias}")
    console.print(f"Create from image: incus launch {alias} <new-name>")
    console.print("List images: wdt publish list")


@cmd.command("list")
def publish_list() -> None:
    """List published Waydroid images in the Incus image store."""
    result = subprocess.run(
        ["incus", "image", "list", "--format", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        console.print("[red]Failed to list images.[/red]")
        raise SystemExit(1)

    import json
    try:
        images = json.loads(result.stdout)
    except json.JSONDecodeError:
        images = []

    # Filter to waydroid-related images
    wdt_images = [
        img for img in images
        if any("waydroid" in str(a).lower() for a in img.get("aliases", []))
        or "waydroid" in img.get("properties", {}).get("description", "").lower()
    ]

    if not wdt_images:
        console.print("[yellow]No published Waydroid images found.[/yellow]")
        console.print("Publish with: wdt publish create")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ALIAS", style="cyan")
    table.add_column("FINGERPRINT")
    table.add_column("SIZE")
    table.add_column("CREATED")

    for img in wdt_images:
        aliases = ", ".join(a.get("name", "") for a in img.get("aliases", []))
        fp = img.get("fingerprint", "")[:12]
        size = img.get("size", 0)
        size_str = f"{size // 1024 // 1024} MiB" if size else "?"
        created = img.get("created_at", "")[:10]
        table.add_row(aliases or "(no alias)", fp, size_str, created)

    console.print(table)


@cmd.command("delete")
@click.argument("alias")
@click.confirmation_option(prompt="Delete this image?")
def publish_delete(alias: str) -> None:
    """Delete a published image by ALIAS."""
    try:
        subprocess.run(["incus", "image", "delete", alias], check=True)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Delete failed:[/red] {exc}")
        raise SystemExit(1) from exc
    console.print(f"[green]Deleted image:[/green] {alias}")
