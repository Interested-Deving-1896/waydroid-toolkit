"""wdt monitor — Waydroid container resource usage and stats.

Shows CPU, memory, network, and disk stats for the active Waydroid
container via the active backend.
"""

from __future__ import annotations

import json
import subprocess

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.core.container import ContainerState
from waydroid_toolkit.core.container import get_active as get_backend

console = Console()


def _backend() -> object:
    try:
        return get_backend()
    except RuntimeError as exc:
        console.print(f"[red]No backend available: {exc}[/red]")
        raise SystemExit(1) from exc


@click.group("monitor")
def cmd() -> None:
    """Show Waydroid container resource usage and stats."""


@cmd.command("status")
def monitor_status() -> None:
    """Detailed container status with resource info."""
    b = _backend()
    info = b.get_info()  # type: ignore[attr-defined]
    state = b.get_state()  # type: ignore[attr-defined]

    console.print(f"[bold]Container:[/bold] {info.container_name}")
    console.print(f"[bold]Backend  :[/bold] {info.backend_type.value} {info.version}")
    console.print()

    state_colour = {
        ContainerState.RUNNING: "green",
        ContainerState.STOPPED: "yellow",
        ContainerState.FROZEN:  "cyan",
        ContainerState.UNKNOWN: "red",
    }.get(state, "white")
    console.print(f"  Status : [{state_colour}]{state.value}[/{state_colour}]")

    if state == ContainerState.RUNNING:
        console.print()
        _print_stats(info.container_name)


@cmd.command("stats")
def monitor_stats() -> None:
    """CPU, memory, disk, and network stats (requires running container)."""
    b = _backend()
    info = b.get_info()  # type: ignore[attr-defined]
    state = b.get_state()  # type: ignore[attr-defined]

    if state != ContainerState.RUNNING:
        console.print(f"[yellow]Container is not running (state: {state.value})[/yellow]")
        raise SystemExit(1)

    _print_stats(info.container_name)


@cmd.command("disk")
def monitor_disk() -> None:
    """Disk usage and allocation for the Waydroid container."""
    b = _backend()
    info = b.get_info()  # type: ignore[attr-defined]
    container_name = info.container_name

    # Allocated root disk size from incus config
    try:
        alloc_result = subprocess.run(
            ["incus", "config", "device", "get", container_name, "root", "size"],
            capture_output=True, text=True, timeout=5,
        )
        allocated = alloc_result.stdout.strip() or "pool default"
    except FileNotFoundError:
        allocated = "incus not found"

    console.print(f"[bold]Disk:[/bold] {container_name}")
    console.print(f"  Allocated : {allocated}")
    console.print()

    # Live disk usage from incus info --format json
    try:
        result = subprocess.run(
            ["incus", "info", container_name, "--format", "json"],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        console.print("[yellow]incus not found — disk usage unavailable[/yellow]")
        return

    if result.returncode != 0:
        console.print("[yellow]Could not retrieve disk info from incus[/yellow]")
        return

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        console.print("[yellow]Could not parse incus info output[/yellow]")
        return

    disk = (data.get("state") or {}).get("disk", {})
    if disk:
        console.print("  [bold]Usage[/bold]")
        for dev, ddata in disk.items():
            usage_mb = ddata.get("usage", 0) / (1024 * 1024)
            console.print(f"    {dev}: {usage_mb:.1f} MiB used")
    else:
        console.print("  [yellow]Disk usage not available (container may be stopped)[/yellow]")


@cmd.command("top")
def monitor_top() -> None:
    """Overview of the Waydroid container (single-instance summary)."""
    b = _backend()
    info = b.get_info()  # type: ignore[attr-defined]
    state = b.get_state()  # type: ignore[attr-defined]

    table = Table(show_header=True, header_style="bold")
    table.add_column("Container", style="dim")
    table.add_column("Backend")
    table.add_column("Status")

    state_colour = {
        ContainerState.RUNNING: "green",
        ContainerState.STOPPED: "yellow",
        ContainerState.FROZEN:  "cyan",
        ContainerState.UNKNOWN: "red",
    }.get(state, "white")

    table.add_row(
        info.container_name,
        f"{info.backend_type.value} {info.version}",
        f"[{state_colour}]{state.value}[/{state_colour}]",
    )
    console.print(table)


# ── helpers ───────────────────────────────────────────────────────────────────

def _print_stats(container_name: str) -> None:
    """Print resource stats from incus info --format json."""
    try:
        result = subprocess.run(
            ["incus", "info", container_name, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        console.print("[yellow]incus not found — stats unavailable[/yellow]")
        return

    if result.returncode != 0:
        console.print("[yellow]Could not retrieve stats from incus[/yellow]")
        return

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        console.print("[yellow]Could not parse incus info output[/yellow]")
        return

    state_data = data.get("state") or {}

    # Memory
    mem = state_data.get("memory", {})
    if mem:
        usage_mb = mem.get("usage", 0) / (1024 * 1024)
        peak_mb  = mem.get("usage_peak", 0) / (1024 * 1024)
        console.print(f"  [bold]Memory[/bold] : {usage_mb:.1f} MiB used / {peak_mb:.1f} MiB peak")

    # CPU
    cpu = state_data.get("cpu", {})
    if cpu:
        usage_ns = cpu.get("usage", 0)
        console.print(f"  [bold]CPU   [/bold] : {usage_ns / 1e9:.2f}s total CPU time")

    # Network
    net = state_data.get("network", {})
    if net:
        console.print()
        console.print("  [bold]Network[/bold]")
        for iface, idata in net.items():
            counters = idata.get("counters", {})
            rx = counters.get("bytes_received", 0) / (1024 * 1024)
            tx = counters.get("bytes_sent", 0) / (1024 * 1024)
            console.print(f"    {iface}: ↓ {rx:.1f} MiB  ↑ {tx:.1f} MiB")

    # Disk
    disk = state_data.get("disk", {})
    if disk:
        console.print()
        console.print("  [bold]Disk[/bold]")
        for dev, ddata in disk.items():
            usage_mb = ddata.get("usage", 0) / (1024 * 1024)
            console.print(f"    {dev}: {usage_mb:.1f} MiB used")
