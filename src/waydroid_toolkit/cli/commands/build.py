"""wdt build — build a Waydroid Android image via penguins-eggs."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.modules.builder.builder import build_android_image
from waydroid_toolkit.utils.android_shared import AndroidShared

console = Console()

_VALID_VARIANTS = [
    AndroidShared.VARIANT_WAYDROID,
    AndroidShared.VARIANT_BLISSOS,
    AndroidShared.VARIANT_AOSP,
    AndroidShared.VARIANT_GRAPHENEOS,
    AndroidShared.VARIANT_LINEAGEOS,
    AndroidShared.VARIANT_CUTTLEFISH,
    AndroidShared.VARIANT_BASSOS,
    AndroidShared.VARIANT_CUSTOM,
]

_VALID_ARCHES = [
    AndroidShared.ABI_X8664,
    AndroidShared.ABI_ARM64,
    AndroidShared.ABI_X86,
    AndroidShared.ABI_ARM32,
    AndroidShared.ABI_RISCV64,
]


@click.command("build")
@click.option(
    "--variant",
    type=click.Choice(_VALID_VARIANTS),
    default=AndroidShared.VARIANT_WAYDROID,
    show_default=True,
    help="Android variant to build.",
)
@click.option(
    "--arch",
    type=click.Choice(_VALID_ARCHES),
    default=AndroidShared.ABI_X8664,
    show_default=True,
    help="Target CPU ABI.",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path.home() / "waydroid-images",
    show_default=True,
    help="Directory to write image files and manifest.",
)
@click.option(
    "--avb-sign",
    is_flag=True,
    help="Apply Android Verified Boot (AVB) signing to the image.",
)
@click.option(
    "--eggs-arg",
    "extra_args",
    multiple=True,
    metavar="ARG",
    help="Extra arguments forwarded verbatim to `eggs android build`.",
)
def cmd(
    variant: str,
    arch: str,
    output: Path,
    avb_sign: bool,
    extra_args: tuple[str, ...],
) -> None:
    """Build an Android image using penguins-eggs.

    penguins-eggs is installed automatically via npm if not present.
    After a successful build, a waydroid-image-manifest.json is written
    to the output directory. Use `wdt install --from-manifest` to install
    the resulting image into Waydroid.
    """
    def progress(msg: str) -> None:
        console.print(f"  [cyan]→[/cyan] {msg}")

    console.print(
        f"[bold]Building Android image[/bold] "
        f"(variant=[green]{variant}[/green], arch=[green]{arch}[/green])"
    )

    try:
        manifest = build_android_image(
            output_dir=output,
            variant=variant,
            arch=arch,
            avb_sign=avb_sign,
            extra_args=list(extra_args) if extra_args else None,
            progress=progress,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Build failed:[/red] {exc}")
        raise SystemExit(1) from exc

    # Summary table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Variant",         manifest.get(AndroidShared.MANIFEST_VARIANT, ""))
    table.add_row("Arch",            manifest.get(AndroidShared.MANIFEST_ARCH, ""))
    table.add_row("Android version", manifest.get(AndroidShared.MANIFEST_ANDROID_VER, ""))
    table.add_row("Build ID",        manifest.get(AndroidShared.MANIFEST_BUILD_ID, ""))
    table.add_row("AVB signed",      str(manifest.get(AndroidShared.MANIFEST_AVB_SIGNED, False)))
    table.add_row("system.img",      manifest.get(AndroidShared.MANIFEST_SYSTEM_IMG, ""))
    table.add_row("Manifest",        str(output / "waydroid-image-manifest.json"))

    console.print("\n[green]Build complete.[/green]")
    console.print(table)
    console.print(
        f"\nRun [bold]wdt install --from-manifest {output / 'waydroid-image-manifest.json'}[/bold] "
        "to install this image."
    )
