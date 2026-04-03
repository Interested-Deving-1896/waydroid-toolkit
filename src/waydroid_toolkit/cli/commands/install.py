"""wdt install — install and initialise Waydroid."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from waydroid_toolkit.core.container import BackendType, IncusBackend, LxcBackend
from waydroid_toolkit.core.container import set_active as set_active_backend
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
    "--backend",
    type=click.Choice(["incus", "lxc"]),
    default="incus",
    show_default=True,
    help=(
        "Container backend to activate after installation. "
        "'incus' is recommended; use 'lxc' only if Incus is not available."
    ),
)
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
    backend: str,
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
        _activate_backend(backend)
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
    _activate_backend(backend)
    console.print("[green]Done. Run 'wdt status' to verify.[/green]")


def _activate_backend(backend_name: str) -> None:
    """Persist the chosen backend to the toolkit config."""
    backend_type = BackendType(backend_name)
    backend_map = {BackendType.LXC: LxcBackend, BackendType.INCUS: IncusBackend}
    backend_obj = backend_map[backend_type]()

    if not backend_obj.is_available():
        console.print(
            f"[yellow]Warning: backend '{backend_name}' is not available "
            f"(binary not found). Skipping backend activation.[/yellow]\n"
            "  Install the backend and run: wdt backend switch "
            f"{backend_name}"
        )
        return

    set_active_backend(backend_type)
    console.print(f"[dim]Container backend set to: {backend_name}[/dim]")

    if backend_type == BackendType.INCUS:
        console.print(
            "[dim]Run 'wdt backend incus-setup' to import the Waydroid "
            "container config into Incus.[/dim]"
        )


def _install_from_manifest(manifest_path: Path, no_bundled_apps: bool) -> None:
    """Install Waydroid using image paths from a penguins-eggs manifest.

    Reads system.img and vendor.img paths from the manifest and stages them
    into /etc/waydroid-extra/images/ so waydroid init uses them directly
    instead of downloading images from the OTA channel.
    """
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
    m_vendor  = manifest.get(AndroidShared.MANIFEST_VENDOR_IMG, "")
    m_boot    = manifest.get(AndroidShared.MANIFEST_BOOT_IMG, "")

    console.print(
        f"  variant=[green]{m_variant}[/green]  "
        f"arch=[green]{m_arch}[/green]  "
        f"android=[green]{m_ver}[/green]"
    )

    # Resolve image paths — system.img is required; vendor.img falls back to
    # the same directory as system.img when not explicitly listed in the manifest
    system_img: Path | None = None
    vendor_img: Path | None = None

    if m_system:
        system_img = Path(m_system)
        if not system_img.exists():
            console.print(f"[red]system.img not found:[/red] {system_img}")
            raise SystemExit(1)

        # Derive vendor.img: use manifest value if present, else sibling file
        if m_vendor:
            vendor_img = Path(m_vendor)
        else:
            vendor_img = system_img.parent / "vendor.img"

        if not vendor_img.exists():
            console.print(
                f"[yellow]Warning:[/yellow] vendor.img not found at {vendor_img}. "
                "Waydroid init will fall back to OTA download for vendor."
            )
            vendor_img = None

        if vendor_img is None:
            # Can't stage without both — proceed without custom images
            system_img = None

    if system_img:
        progress(f"system.img: {system_img}")
        progress(f"vendor.img: {vendor_img}")
        if m_boot:
            progress(f"boot.img:   {m_boot}  (informational — not staged)")
    else:
        progress("No image paths in manifest — waydroid init will download images.")

    # Map Android ABI to Waydroid ImageArch
    _abi_to_image_arch = {
        AndroidShared.ABI_X8664: ImageArch.X86_64,
        AndroidShared.ABI_ARM64: ImageArch.ARM64,
        AndroidShared.ABI_X86:   ImageArch.X86_64,
        AndroidShared.ABI_ARM32: ImageArch.ARM64,
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
    init_waydroid(
        image_type=ImageType.VANILLA,
        arch=image_arch,
        install_apps=not no_bundled_apps,
        system_img=system_img,
        vendor_img=vendor_img,
        progress=progress,
    )
    console.print("[green]Done. Run 'wdt status' to verify.[/green]")
