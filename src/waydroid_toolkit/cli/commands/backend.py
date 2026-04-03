"""wdt backend — manage the active container backend (LXC or Incus)."""

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.core.container import (
    BackendType,
)
from waydroid_toolkit.core.container import (
    IncusBackend,
    LxcBackend,
)
from waydroid_toolkit.core.container import (
    detect as detect_backend,
)
from waydroid_toolkit.core.container import (
    get_active as get_active_backend,
)
from waydroid_toolkit.core.container import (
    list_available as list_available_backends,
)
from waydroid_toolkit.core.container import (
    set_active as set_active_backend,
)

console = Console()


@click.group("backend")
def cmd() -> None:
    """Select and inspect the container backend (LXC or Incus)."""


@cmd.command("status")
def backend_status() -> None:
    """Show the active backend and all available backends."""
    try:
        active = get_active_backend()
        info = active.get_info()
    except RuntimeError as exc:
        console.print(f"[red]No backend available: {exc}[/red]")
        raise SystemExit(1)

    console.print(f"[bold]Active backend:[/bold] [green]{info.backend_type.value}[/green]")
    console.print(f"  Binary:    {info.binary}")
    console.print(f"  Version:   {info.version}")
    console.print(f"  Container: {info.container_name}")
    console.print()

    available = list_available_backends()
    if len(available) > 1:
        console.print("[bold]Also available:[/bold]")
        for b in available:
            if b.backend_type != active.backend_type:
                console.print(f"  {b.backend_type.value}")


@cmd.command("detect")
def backend_detect() -> None:
    """Auto-detect the best available backend and set it as active."""
    try:
        backend = detect_backend()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)

    set_active_backend(backend.backend_type)
    info = backend.get_info()
    console.print(
        f"[green]Detected and set backend:[/green] "
        f"{info.backend_type.value} {info.version}"
    )


def _do_switch(backend_name: str) -> None:
    """Shared implementation for 'switch' and 'set'."""
    backend_type = BackendType(backend_name)
    backend_map = {BackendType.LXC: LxcBackend, BackendType.INCUS: IncusBackend}
    backend = backend_map[backend_type]()

    if not backend.is_available():
        console.print(
            f"[red]Backend '{backend_name}' is not available "
            f"(binary not found on PATH).[/red]"
        )
        raise SystemExit(1)

    set_active_backend(backend_type)
    info = backend.get_info()
    console.print(
        f"[green]Active backend set to:[/green] "
        f"{info.backend_type.value} {info.version}"
    )
    if backend_type == BackendType.INCUS:
        console.print(
            "[dim]Run 'wdt backend incus-setup' to import the Waydroid "
            "container config into Incus.[/dim]"
        )


@cmd.command("switch")
@click.argument("backend_name", metavar="BACKEND", type=click.Choice(["lxc", "incus"]))
def backend_switch(backend_name: str) -> None:
    """Switch the active backend to LXC or Incus.

    BACKEND must be one of: lxc, incus

    The chosen backend binary must be present on PATH.
    For Incus, run 'wdt backend incus-setup' after switching to import
    the Waydroid container configuration into Incus.
    """
    _do_switch(backend_name)


@cmd.command("set")
@click.argument("backend_name", metavar="BACKEND", type=click.Choice(["lxc", "incus"]))
def backend_set(backend_name: str) -> None:
    """Set the active backend to LXC or Incus (alias for 'switch').

    BACKEND must be one of: lxc, incus

    The chosen backend binary must be present on PATH.
    For Incus, run 'wdt backend incus-setup' after switching to import
    the Waydroid container configuration into Incus.
    """
    _do_switch(backend_name)


@cmd.command("incus-setup")
def backend_incus_setup() -> None:
    """Import the Waydroid LXC container config into Incus.

    Reads the LXC config written by upstream waydroid/waydroid and creates
    an equivalent Incus container, passing Android-specific directives
    (binder nodes, seccomp, AppArmor) through Incus's raw.lxc passthrough.

    Run this once after switching to the Incus backend.
    """
    backend = IncusBackend()
    if not backend.is_available():
        console.print("[red]Incus is not installed (binary not found).[/red]")
        raise SystemExit(1)

    console.print("[bold]Importing Waydroid container config into Incus...[/bold]")
    try:
        backend.setup_from_lxc()
        console.print("[green]Done. The 'waydroid' container is now managed by Incus.[/green]")
        console.print(
            "[dim]Switch the active backend with: wdt backend switch incus[/dim]"
        )
    except RuntimeError as exc:
        console.print(f"[red]Setup failed: {exc}[/red]")
        raise SystemExit(1)


@cmd.command("list")
def backend_list() -> None:
    """List all backends and their availability on this system."""
    try:
        active = get_active_backend()
        active_type = active.backend_type
    except RuntimeError:
        active_type = None

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Backend")
    table.add_column("Available")
    table.add_column("Version")
    table.add_column("Active")

    for backend_cls in (LxcBackend, IncusBackend):
        backend = backend_cls()
        available = backend.is_available()
        version = backend.get_info().version if available else "—"
        is_active = active_type == backend.backend_type
        table.add_row(
            backend.backend_type.value,
            "[green]yes[/green]" if available else "[red]no[/red]",
            version,
            "[green]✅[/green]" if is_active else "",
        )

    console.print(table)
