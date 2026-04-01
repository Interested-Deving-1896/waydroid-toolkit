"""wdt install — install and initialise Waydroid."""

import click
from rich.console import Console

from waydroid_toolkit.modules.installer.installer import (
    ImageArch,
    ImageType,
    init_waydroid,
    install_package,
    is_waydroid_installed,
    setup_repo,
)
from waydroid_toolkit.utils.distro import Distro, detect_distro

console = Console()


@click.command("install")
@click.option("--image-type", type=click.Choice(["VANILLA", "GAPPS"]), default="VANILLA",
              show_default=True, help="Android image type to initialise with.")
@click.option("--arch", type=click.Choice(["x86_64", "arm64"]), default="x86_64",
              show_default=True, help="Target architecture.")
@click.option("--skip-repo", is_flag=True, help="Skip adding the Waydroid package repo.")
@click.option("--init-only", is_flag=True, help="Skip package install; only run waydroid init.")
@click.option("--no-bundled-apps", is_flag=True,
              help="Skip installing bundled apps (F-Droid, AuroraStore, etc.) after init.")
def cmd(
    image_type: str, arch: str, skip_repo: bool, init_only: bool, no_bundled_apps: bool,
) -> None:
    """Install Waydroid and initialise with the chosen image type.

    After initialisation, F-Droid, AuroraStore, AuroraDroid, AuroraServices,
    and selected GitHub-Releases apps are installed automatically. Use
    --no-bundled-apps to skip this step.
    """
    distro = detect_distro()
    if distro == Distro.UNKNOWN:
        console.print("[yellow]Warning: could not detect distro. Proceeding anyway.[/yellow]")

    def progress(msg: str) -> None:
        console.print(f"  [cyan]→[/cyan] {msg}")

    if not init_only:
        if is_waydroid_installed():
            console.print("[green]Waydroid is already installed.[/green]")
        else:
            if not skip_repo:
                console.print("[bold]Setting up Waydroid repository...[/bold]")
                setup_repo(distro, progress)
            console.print("[bold]Installing Waydroid package...[/bold]")
            install_package(distro, progress)

    console.print("[bold]Initialising Waydroid...[/bold]")
    init_waydroid(
        image_type=ImageType[image_type],
        arch=ImageArch(arch),
        install_apps=not no_bundled_apps,
        progress=progress,
    )
    console.print("[green]Done. Run 'wdt status' to verify.[/green]")
