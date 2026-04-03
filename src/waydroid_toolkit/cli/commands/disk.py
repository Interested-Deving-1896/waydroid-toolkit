"""wdt disk — live disk resize for the Waydroid container.

Resizes the root disk of the Waydroid Incus container without data loss.
Incus handles the online resize for LVM/ZFS/Btrfs pools.

Sub-commands
------------
  wdt disk resize <size>   Resize the root disk (e.g. 20GB, +5GB)
  wdt disk info            Show current disk size and pool info
"""

from __future__ import annotations

import subprocess

import click
from rich.console import Console

console = Console()


def _container_name() -> str:
    try:
        from waydroid_toolkit.core.container import get_active
        return get_active().get_info().container_name  # type: ignore[attr-defined]
    except Exception:
        return "waydroid"


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, check=check)


@click.group("disk")
def cmd() -> None:
    """Live disk resize for the Waydroid container."""


@cmd.command("resize")
@click.argument("size")
@click.option("--container", "-c", default="",
              help="Incus container name (default: auto-detect).")
def disk_resize(size: str, container: str) -> None:
    """Resize the Waydroid container's root disk to SIZE.

    SIZE formats:
      20GB     Set to exactly 20 GiB
      +5GB     Grow by 5 GiB
      100GiB   Set to 100 GiB

    Incus handles the online resize for LVM/ZFS/Btrfs pools.
    The filesystem inside the container expands automatically.

    \b
    Examples:
      wdt disk resize 20GB
      wdt disk resize +5GB
      wdt disk resize 100GiB
    """
    import re
    ct = container or _container_name()

    # Validate size format
    if not re.match(r'^\+?[0-9]+(GB|GiB|MB|MiB|TB|TiB|KB|KiB)$', size):
        console.print(f"[red]Invalid size format: {size}[/red]")
        console.print("Use e.g. 20GB, +5GB, 100GiB")
        raise SystemExit(1)

    # Get current size
    current = _get_root_size(ct)
    console.print(f"Container : [bold]{ct}[/bold]")
    console.print(f"Current   : {current or 'pool default'}")
    console.print(f"New size  : [bold]{size}[/bold]")
    console.print()

    try:
        _run(["incus", "config", "device", "set", ct, "root", "size", size])
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Resize failed:[/red] {exc.stderr.strip()}")
        raise SystemExit(1) from exc

    new_size = _get_root_size(ct) or size
    console.print(f"[green]Root disk resized to {new_size}[/green]")
    console.print()
    console.print("The filesystem expands automatically on the next container start.")
    console.print("Verify inside the container: wdt shell exec -- df -h /")


@cmd.command("info")
@click.option("--container", "-c", default="",
              help="Incus container name (default: auto-detect).")
def disk_info(container: str) -> None:
    """Show current disk size and pool info for the Waydroid container."""
    ct = container or _container_name()

    size = _get_root_size(ct)
    pool = _get_pool(ct)

    console.print(f"[bold]Container:[/bold] {ct}")
    console.print(f"[bold]Root disk:[/bold] {size or 'pool default'}")
    console.print(f"[bold]Pool:[/bold]      {pool or 'default'}")
    console.print()

    # Pool details
    if pool:
        result = _run(["incus", "storage", "info", pool], check=False)
        if result.returncode == 0:
            console.print("[bold]Pool usage:[/bold]")
            for line in result.stdout.splitlines():
                if any(k in line.lower() for k in ("used", "total", "free", "space")):
                    console.print(f"  {line.strip()}")
            console.print()

    # Live filesystem usage if running
    state_result = _run(
        ["incus", "list", "--format", "csv", "-c", "s", ct], check=False
    )
    if "RUNNING" in state_result.stdout:
        df_result = _run(
            ["incus", "exec", ct, "--", "df", "-h", "/"], check=False
        )
        if df_result.returncode == 0:
            console.print("[bold]Live filesystem usage:[/bold]")
            for line in df_result.stdout.splitlines():
                console.print(f"  {line}")


def _get_root_size(ct: str) -> str:
    result = _run(["incus", "config", "device", "show", ct], check=False)
    if result.returncode != 0:
        return ""
    in_root = False
    for line in result.stdout.splitlines():
        if line.strip().startswith("root:"):
            in_root = True
            continue
        if in_root:
            if line.startswith(" ") or line.startswith("\t"):
                if "size:" in line:
                    return line.split("size:")[-1].strip()
            else:
                break
    return ""


def _get_pool(ct: str) -> str:
    result = _run(["incus", "config", "device", "show", ct], check=False)
    if result.returncode != 0:
        return ""
    in_root = False
    for line in result.stdout.splitlines():
        if line.strip().startswith("root:"):
            in_root = True
            continue
        if in_root:
            if line.startswith(" ") or line.startswith("\t"):
                if "pool:" in line:
                    return line.split("pool:")[-1].strip()
            else:
                break
    return ""
