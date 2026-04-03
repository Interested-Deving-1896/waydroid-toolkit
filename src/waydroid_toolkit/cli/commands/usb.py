"""wdt usb — manage USB device passthrough for the Waydroid container."""

from __future__ import annotations

import subprocess

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _container_name() -> str:
    try:
        from waydroid_toolkit.core.container import get_active as get_backend
        b = get_backend()
        return b.get_info().container_name  # type: ignore[attr-defined]
    except Exception:
        return "waydroid"


@click.group("usb")
def cmd() -> None:
    """Manage USB device passthrough for the Waydroid container."""


@cmd.command("list-host")
def usb_list_host() -> None:
    """List USB devices available on the host."""
    result = subprocess.run(["lsusb"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print("[yellow]lsusb not found — install usbutils[/yellow]")
        # Fallback: incus info --resources
        r2 = subprocess.run(
            ["incus", "info", "--resources"],
            capture_output=True, text=True,
        )
        if r2.returncode == 0:
            in_usb = False
            for line in r2.stdout.splitlines():
                if "USB devices" in line:
                    in_usb = True
                    continue
                if in_usb and line and not line[0].isspace():
                    break
                if in_usb:
                    console.print(f"  {line}")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("VENDOR:ID", style="cyan", min_width=10)
    table.add_column("BUS:DEV", min_width=8)
    table.add_column("DESCRIPTION")

    for line in result.stdout.splitlines():
        # Bus 001 Device 003: ID 046d:c52b Logitech, Inc. Unifying Receiver
        parts = line.split()
        if len(parts) < 6:
            continue
        bus = parts[1]
        dev = parts[3].rstrip(":")
        vid_pid = parts[5]
        desc = " ".join(parts[6:]) if len(parts) > 6 else ""
        table.add_row(vid_pid, f"{bus}:{dev}", desc)

    console.print(table)


@cmd.command("attach")
@click.argument("vendor_id")
@click.argument("product_id", required=False, default=None)
@click.option("--dev-name", default="", help="Device name (default: usb-<VID>-<PID>).")
def usb_attach(vendor_id: str, product_id: str | None, dev_name: str) -> None:
    """Attach a USB device to the container by vendor and product ID.

    Accepts either two separate arguments (VENDOR_ID PRODUCT_ID) or a single
    VID:PID string (e.g. 046d:c52b).
    """
    # Support VID:PID shorthand as a single argument
    if product_id is None:
        if ":" in vendor_id:
            vendor_id, product_id = vendor_id.split(":", 1)
        else:
            raise click.UsageError(
                "Provide VENDOR_ID PRODUCT_ID or a single VID:PID string (e.g. 046d:c52b)."
            )

    ct = _container_name()
    pname = dev_name or f"usb-{vendor_id}-{product_id}"

    console.print(f"Attaching USB {vendor_id}:{product_id} to '{ct}' as '{pname}'")
    result = subprocess.run([
        "incus", "config", "device", "add", ct, pname, "usb",
        f"vendorid={vendor_id}",
        f"productid={product_id}",
    ])
    if result.returncode != 0:
        console.print("[red]Failed to attach USB device.[/red]")
        raise SystemExit(1)
    console.print(f"[green]USB device attached:[/green] {pname} ({vendor_id}:{product_id})")


@cmd.command("detach")
@click.argument("dev_name")
def usb_detach(dev_name: str) -> None:
    """Remove a USB passthrough device from the container."""
    ct = _container_name()
    result = subprocess.run(["incus", "config", "device", "remove", ct, dev_name])
    if result.returncode != 0:
        console.print(f"[red]Failed to remove USB device '{dev_name}'.[/red]")
        raise SystemExit(1)
    console.print(f"[green]USB device removed:[/green] {dev_name}")


@cmd.command("list")
def usb_list() -> None:
    """List USB devices currently attached to the container."""
    ct = _container_name()

    list_r = subprocess.run(
        ["incus", "config", "device", "list", ct],
        capture_output=True, text=True,
    )
    if list_r.returncode != 0:
        console.print("[yellow]Could not list devices.[/yellow]")
        return

    usb_devices = [
        line.split()[0] for line in list_r.stdout.splitlines()
        if "usb" in line
    ]

    if not usb_devices:
        console.print("[yellow]No USB devices attached.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("DEVICE", style="cyan")
    table.add_column("VENDOR ID")
    table.add_column("PRODUCT ID")

    for dev in usb_devices:
        vid_r = subprocess.run(
            ["incus", "config", "device", "get", ct, dev, "vendorid"],
            capture_output=True, text=True,
        )
        pid_r = subprocess.run(
            ["incus", "config", "device", "get", ct, dev, "productid"],
            capture_output=True, text=True,
        )
        table.add_row(dev, vid_r.stdout.strip(), pid_r.stdout.strip())

    console.print(table)
