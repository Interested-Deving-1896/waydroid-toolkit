"""wdt install — install and initialise Waydroid."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from waydroid_toolkit.modules.builder.builder import read_manifest
from waydroid_toolkit.modules.installer.installer import (
    ImageArch,
    ImageType,
    init_waydroid,
    install_package,
    is_waydroid_installed,
    setup_repo,
)
from waydroid_toolkit.utils.android_shared import AndroidShared
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
@click.option(
    "--from-manifest",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    metavar="PATH",
    help=(
        "Path to a waydroid-image-manifest.json produced by `wdt build`. "
        "Uses the arch and image paths from the manifest instead of defaults."
    ),
)
def cmd(
    image_type: str,
    arch: str,
    skip_repo: bool,
    init_only: bool,
    no_bundled_apps: bool,
    from_manifest: Path | None,
) -> None:
    """Install Waydroid and initialise with the chosen image type.

    After initialisation, F-Droid, AuroraStore, AuroraDroid, AuroraServices,
    and selected GitHub-Releases apps are installed automatically. Use
    --no-bundled-apps to skip this step.

    Pass --from-manifest to use an image built by `wdt build` instead of
    the default Waydroid images.
    """
    # ── Manifest mode ─────────────────────────────────────────────────────────
    if from_manifest is not None:
        _install_from_manifest(from_manifest, no_bundled_apps)
        return

    # ── Standard mode ─────────────────────────────────────────────────────────
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


def _install_from_manifest(manifest_path: Path, no_bundled_apps: bool) -> None:
    """Install Waydroid using image paths from a penguins-eggs manifest."""
    def progress(msg: str) -> None:
        console.print(f"  [cyan]→[/cyan] {msg}")

    console.print(f"[bold]Reading manifest:[/bold] {manifest_path}")
    try:
        manifest = read_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Invalid manifest:[/red] {exc}")
        raise SystemExit(1) from exc

    m_arch    = manifest.get(AndroidShared.MANIFEST_ARCH, "x86_64")
    m_variant = manifest.get(AndroidShared.MANIFEST_VARIANT, "unknown")
    m_ver     = manifest.get(AndroidShared.MANIFEST_ANDROID_VER, "unknown")
    m_system  = manifest.get(AndroidShared.MANIFEST_SYSTEM_IMG, "")
    m_boot    = manifest.get(AndroidShared.MANIFEST_BOOT_IMG, "")

    console.print(
        f"  variant=[green]{m_variant}[/green]  "
        f"arch=[green]{m_arch}[/green]  "
        f"android=[green]{m_ver}[/green]"
    )

    # Map Android ABI to Waydroid ImageArch
    _abi_to_image_arch = {
        AndroidShared.ABI_X8664:  ImageArch.X86_64,
        AndroidShared.ABI_ARM64:  ImageArch.ARM64,
        AndroidShared.ABI_X86:    ImageArch.X86_64,   # fallback
        AndroidShared.ABI_ARM32:  ImageArch.ARM64,    # fallback
    }
    image_arch = _abi_to_image_arch.get(m_arch, ImageArch.X86_64)

    distro = detect_distro()
    if not is_waydroid_installed():
        if distro != Distro.UNKNOWN:
            console.print("[bold]Setting up Waydroid repository...[/bold]")
            setup_repo(distro, progress)
        console.print("[bold]Installing Waydroid package...[/bold]")
        install_package(distro, progress)

    console.print("[bold]Initialising Waydroid from manifest images...[/bold]")
    if m_system:
        progress(f"system.img: {m_system}")
    if m_boot:
        progress(f"boot.img:   {m_boot}")

    init_waydroid(
        image_type=ImageType.VANILLA,
        arch=image_arch,
        install_apps=not no_bundled_apps,
        progress=progress,
    )
    console.print("[green]Done. Run 'wdt status' to verify.[/green]")
