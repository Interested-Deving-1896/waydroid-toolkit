"""wdt net — manage network port forwarding for the Waydroid container."""

from __future__ import annotations

import subprocess

import click
from rich.console import Console
from rich.table import Table

console = Console()

_CONTAINER = "waydroid"


def _container_name() -> str:
    """Return the active Waydroid container name."""
    try:
        from waydroid_toolkit.core.container.backend import get_backend
        b = get_backend()
        return b.get_info().container_name  # type: ignore[attr-defined]
    except Exception:
        return _CONTAINER


@click.group("net")
def cmd() -> None:
    """Manage network port forwarding for the Waydroid container."""


@cmd.command("forward")
@click.argument("host_port", type=int)
@click.argument("container_port", type=int, required=False)
@click.option("--proto", default="tcp", type=click.Choice(["tcp", "udp"]), show_default=True)
@click.option("--listen", "listen_addr", default="0.0.0.0", show_default=True,
              help="Host listen address.")
@click.option("--proxy-name", default="", help="Proxy device name (default: fwd-<port>).")
def net_forward(
    host_port: int,
    container_port: int | None,
    proto: str,
    listen_addr: str,
    proxy_name: str,
) -> None:
    """Forward HOST_PORT on the host to CONTAINER_PORT inside the container.

    CONTAINER_PORT defaults to HOST_PORT when omitted.
    """
    ct = _container_name()
    cport = container_port if container_port is not None else host_port
    pname = proxy_name or f"fwd-{host_port}"

    console.print(f"Adding port forward: {listen_addr}:{host_port} → {ct}:{cport} ({proto})")
    result = subprocess.run([
        "incus", "config", "device", "add", ct, pname, "proxy",
        f"listen={proto}:{listen_addr}:{host_port}",
        f"connect={proto}:127.0.0.1:{cport}",
    ])
    if result.returncode != 0:
        console.print("[red]Failed to add port forward.[/red]")
        raise SystemExit(1)
    console.print(f"[green]Port forward added:[/green] {pname}")
    console.print(f"  Host      : {listen_addr}:{host_port}")
    console.print(f"  Container : 127.0.0.1:{cport}")


@cmd.command("unforward")
@click.argument("proxy_name")
def net_unforward(proxy_name: str) -> None:
    """Remove a port forward proxy device by name."""
    ct = _container_name()
    result = subprocess.run(["incus", "config", "device", "remove", ct, proxy_name])
    if result.returncode != 0:
        console.print(f"[red]Failed to remove proxy device '{proxy_name}'.[/red]")
        raise SystemExit(1)
    console.print(f"[green]Removed port forward:[/green] {proxy_name}")


@cmd.command("list")
def net_list() -> None:
    """List all port forward proxy devices on the container."""
    ct = _container_name()

    # Get all device names
    list_r = subprocess.run(
        ["incus", "config", "device", "list", ct],
        capture_output=True, text=True,
    )
    if list_r.returncode != 0:
        console.print("[yellow]Could not list devices (is the container running?)[/yellow]")
        return

    proxy_devices = [
        line.split()[0] for line in list_r.stdout.splitlines()
        if "proxy" in line
    ]

    if not proxy_devices:
        console.print("[yellow]No port forwards configured.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("DEVICE", style="cyan")
    table.add_column("LISTEN")
    table.add_column("CONNECT")

    for dev in proxy_devices:
        listen_r = subprocess.run(
            ["incus", "config", "device", "get", ct, dev, "listen"],
            capture_output=True, text=True,
        )
        connect_r = subprocess.run(
            ["incus", "config", "device", "get", ct, dev, "connect"],
            capture_output=True, text=True,
        )
        table.add_row(
            dev,
            listen_r.stdout.strip(),
            connect_r.stdout.strip(),
        )

    console.print(table)


@cmd.command("status")
def net_status() -> None:
    """Show network interfaces and port forwards for the container."""
    ct = _container_name()
    console.print(f"[bold]Network status:[/bold] {ct}")
    console.print()

    # Network interfaces from incus info
    info_r = subprocess.run(
        ["incus", "info", ct],
        capture_output=True, text=True,
    )
    if info_r.returncode == 0:
        in_net = False
        for line in info_r.stdout.splitlines():
            if line.startswith("Network usage:"):
                in_net = True
                continue
            if in_net and line and not line[0].isspace():
                break
            if in_net:
                console.print(f"  {line}")

    console.print()
    console.print("[bold]Proxy devices:[/bold]")

    show_r = subprocess.run(
        ["incus", "config", "device", "show", ct],
        capture_output=True, text=True,
    )
    found = False
    if show_r.returncode == 0:
        in_proxy = False
        for line in show_r.stdout.splitlines():
            if "type: proxy" in line:
                in_proxy = True
                found = True
            if in_proxy:
                console.print(f"  {line}")
                if not line.strip():
                    in_proxy = False

    if not found:
        console.print("  [yellow]None[/yellow]")
