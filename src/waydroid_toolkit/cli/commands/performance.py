"""wdt performance — host-side performance tuning for Waydroid gaming."""

import click
from rich.console import Console

from waydroid_toolkit.modules.performance import (
    PerformanceProfile, apply_profile, install_systemd_service, restore_defaults,
)

console = Console()


@click.group("performance")
def cmd() -> None:
    """Apply or remove host performance tuning for Waydroid gaming."""


@cmd.command("apply")
@click.option("--zram-size", default=4096, show_default=True, help="ZRAM size in MB.")
@click.option("--zram-algo", default="lz4", show_default=True,
              type=click.Choice(["lz4", "zstd", "lzo"]), help="ZRAM compression algorithm.")
@click.option("--governor", default="performance", show_default=True,
              type=click.Choice(["performance", "schedutil", "powersave"]),
              help="CPU frequency governor.")
@click.option("--no-turbo", is_flag=True, help="Disable CPU Turbo Boost.")
@click.option("--no-gamemode", is_flag=True, help="Skip GameMode integration.")
def perf_apply(
    zram_size: int, zram_algo: str, governor: str, no_turbo: bool, no_gamemode: bool,
) -> None:
    """Apply performance tuning to the host system."""
    profile = PerformanceProfile(
        zram_size_mb=zram_size,
        zram_algorithm=zram_algo,
        cpu_governor=governor,
        enable_turbo=not no_turbo,
        use_gamemode=not no_gamemode,
    )
    apply_profile(profile, progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print("[green]Performance profile applied.[/green]")


@cmd.command("restore")
def perf_restore() -> None:
    """Restore conservative CPU/system defaults."""
    restore_defaults(progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print("[green]Defaults restored.[/green]")


@cmd.command("enable-service")
def perf_enable_service() -> None:
    """Install a systemd service to persist the performance profile across reboots."""
    install_systemd_service(progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print("[green]waydroid-boost.service installed and enabled.[/green]")
