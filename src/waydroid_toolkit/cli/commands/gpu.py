"""wdt gpu — manage GPU passthrough for the Waydroid container."""

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


@click.group("gpu")
def cmd() -> None:
    """Manage GPU passthrough for the Waydroid container."""


@cmd.command("list-host")
def gpu_list_host() -> None:
    """List GPUs available on the host."""
    console.print("[bold]GPUs available on host:[/bold]")
    console.print()

    # Try incus info --resources first
    r = subprocess.run(
        ["incus", "info", "--resources"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        in_gpu = False
        for line in r.stdout.splitlines():
            if "GPUs:" in line:
                in_gpu = True
                continue
            if in_gpu and line and not line[0].isspace():
                break
            if in_gpu:
                console.print(f"  {line}")

    # Also show lspci output if available
    lspci_r = subprocess.run(["lspci"], capture_output=True, text=True)
    if lspci_r.returncode == 0:
        console.print()
        console.print("[bold]PCI GPU devices:[/bold]")
        found = False
        for line in lspci_r.stdout.splitlines():
            if any(k in line.upper() for k in ("VGA", "3D", "DISPLAY", "NVIDIA", "AMD")):
                console.print(f"  {line}")
                found = True
        if not found:
            console.print("  [yellow]None found[/yellow]")


@cmd.command("attach")
@click.option("--type", "gpu_type", default="physical",
              type=click.Choice(["physical", "mdev", "mig", "virtio"]),
              show_default=True, help="GPU type.")
@click.option("--pci", "pci_addr", default="", help="PCI address (e.g. 0000:01:00.0).")
@click.option("--dev-name", default="gpu0", show_default=True, help="Device name.")
@click.option("--vendor", default="", help="GPU vendor ID filter.")
def gpu_attach(gpu_type: str, pci_addr: str, dev_name: str, vendor: str) -> None:
    """Attach a GPU to the container."""
    ct = _container_name()

    cmd_args = [
        "incus", "config", "device", "add", ct, dev_name, "gpu",
        f"gputype={gpu_type}",
    ]
    if pci_addr:
        cmd_args.append(f"pci={pci_addr}")
    if vendor:
        cmd_args.append(f"vendorid={vendor}")

    desc = f"type={gpu_type}" + (f", pci={pci_addr}" if pci_addr else "")
    console.print(f"Attaching GPU to '{ct}' ({desc})")
    result = subprocess.run(cmd_args)
    if result.returncode != 0:
        console.print("[red]Failed to attach GPU.[/red]")
        raise SystemExit(1)
    console.print(f"[green]GPU attached:[/green] {dev_name} → {ct}")
    console.print(f"  Type : {gpu_type}")
    if pci_addr:
        console.print(f"  PCI  : {pci_addr}")


@cmd.command("detach")
@click.argument("dev_name")
def gpu_detach(dev_name: str) -> None:
    """Remove a GPU passthrough device from the container."""
    ct = _container_name()
    result = subprocess.run(["incus", "config", "device", "remove", ct, dev_name])
    if result.returncode != 0:
        console.print(f"[red]Failed to remove GPU device '{dev_name}'.[/red]")
        raise SystemExit(1)
    console.print(f"[green]GPU removed:[/green] {dev_name}")


@cmd.command("list")
def gpu_list() -> None:
    """List GPU devices currently attached to the container."""
    ct = _container_name()

    list_r = subprocess.run(
        ["incus", "config", "device", "list", ct],
        capture_output=True, text=True,
    )
    if list_r.returncode != 0:
        console.print("[yellow]Could not list devices.[/yellow]")
        return

    gpu_devices = [
        line.split()[0] for line in list_r.stdout.splitlines()
        if "gpu" in line
    ]

    if not gpu_devices:
        console.print("[yellow]No GPU devices attached.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("DEVICE", style="cyan")
    table.add_column("TYPE")
    table.add_column("PCI")

    for dev in gpu_devices:
        gtype_r = subprocess.run(
            ["incus", "config", "device", "get", ct, dev, "gputype"],
            capture_output=True, text=True,
        )
        pci_r = subprocess.run(
            ["incus", "config", "device", "get", ct, dev, "pci"],
            capture_output=True, text=True,
        )
        table.add_row(
            dev,
            gtype_r.stdout.strip() or "physical",
            pci_r.stdout.strip() or "-",
        )

    console.print(table)


@cmd.command("status")
def gpu_status() -> None:

    """Show GPU attachment status and host GPU resources."""
    ct = _container_name()
    console.print(f"[bold]GPU status:[/bold] {ct}")
    console.print()

    # Attached devices
    list_r = subprocess.run(
        ["incus", "config", "device", "list", ct],
        capture_output=True, text=True,
    )
    gpu_devices = []
    if list_r.returncode == 0:
        gpu_devices = [
            line.split()[0] for line in list_r.stdout.splitlines()
            if "gpu" in line
        ]

    if gpu_devices:
        table = Table(show_header=True, header_style="bold")
        table.add_column("DEVICE", style="cyan")
        table.add_column("TYPE")
        table.add_column("PCI")
        for dev in gpu_devices:
            gtype_r = subprocess.run(
                ["incus", "config", "device", "get", ct, dev, "gputype"],
                capture_output=True, text=True,
            )
            pci_r = subprocess.run(
                ["incus", "config", "device", "get", ct, dev, "pci"],
                capture_output=True, text=True,
            )
            table.add_row(dev, gtype_r.stdout.strip() or "physical", pci_r.stdout.strip() or "-")
        console.print(table)
    else:
        console.print("[yellow]No GPU devices attached.[/yellow]")

    console.print()
    console.print("[bold]Host GPU resources:[/bold]")
    r = subprocess.run(["incus", "info", "--resources"], capture_output=True, text=True)
    if r.returncode == 0:
        in_gpu = False
        for line in r.stdout.splitlines():
            if "GPUs:" in line:
                in_gpu = True
                continue
            if in_gpu and line and not line[0].isspace():
                break
            if in_gpu:
                console.print(f"  {line}")
