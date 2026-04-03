"""wdt winesapos — fetch, import, and launch winesapOS gaming VMs.

winesapOS is an Arch Linux-based gaming OS (Steam Deck-compatible) distributed
as raw disk images. This command downloads the image, converts it to qcow2,
imports it into Incus, and launches it as a virtual machine.

References:
  https://github.com/winesapOS/winesapOS
  https://github.com/winesapOS/winesapOS/releases

Sub-commands
------------
  wdt winesapos fetch   [VERSION] [--edition ...]
  wdt winesapos import  [VERSION] [--edition ...]
  wdt winesapos launch  NAME [options]
  wdt winesapos list
  wdt winesapos versions
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import click
from rich.console import Console

console = Console()

_GITHUB_BASE = "https://github.com/winesapOS/winesapOS/releases/download"
_GITHUB_API = "https://api.github.com/repos/winesapOS/winesapOS/releases"
_DEFAULT_VERSION = "4.5.0"
_DEFAULT_EDITION = "minimal"
_DEFAULT_DIR = Path.home() / ".local" / "share" / "waydroid-toolkit" / "winesapos"


def _ws_dir() -> Path:
    return Path(os.environ.get("WDT_WINESAPOS_DIR", str(_DEFAULT_DIR)))


def _ws_filename(version: str, edition: str) -> str:
    return f"winesapos-{version}-{edition}.img.zst"


def _ws_alias(version: str, edition: str) -> str:
    return f"winesapos/{version}/{edition}"


def _ws_img_exists(version: str, edition: str) -> bool:
    alias = _ws_alias(version, edition)
    try:
        result = subprocess.run(
            ["incus", "image", "list", "--format", "csv"],
            capture_output=True, text=True,
        )
        return alias in result.stdout
    except FileNotFoundError:
        return False


@click.group("winesapos")
def cmd() -> None:
    """Fetch, import, and launch winesapOS gaming VMs via Incus.

    winesapOS is an Arch Linux-based gaming OS (Steam Deck-compatible).
    See https://github.com/winesapOS/winesapOS
    """


@cmd.command("fetch")
@click.argument("version", default="")
@click.option("--edition", "-e",
              type=click.Choice(["minimal", "performance", "secure"]),
              default="", help="Image edition (default: minimal).")
def ws_fetch(version: str, edition: str) -> None:
    """Download the winesapOS disk image from GitHub Releases.

    VERSION defaults to the value of WDT_WINESAPOS_VERSION (or 4.5.0).
    """
    version = version or os.environ.get("WDT_WINESAPOS_VERSION", _DEFAULT_VERSION)
    edition = edition or os.environ.get("WDT_WINESAPOS_EDITION", _DEFAULT_EDITION)

    if not shutil.which("curl"):
        console.print("[red]curl is required.[/red]")
        raise SystemExit(1)
    if not shutil.which("zstd"):
        console.print("[red]zstd is required.[/red] Install: sudo apt install zstd")
        raise SystemExit(1)

    fname = _ws_filename(version, edition)
    dest_zst = _ws_dir() / fname
    dest_img = _ws_dir() / fname.removesuffix(".zst")

    _ws_dir().mkdir(parents=True, exist_ok=True)

    if dest_img.exists():
        console.print(f"[yellow]Already fetched:[/yellow] {dest_img}")
        return

    if not dest_zst.exists():
        url = f"{_GITHUB_BASE}/{version}/{fname}"
        console.print(f"Downloading [bold]{fname}[/bold]...")
        console.print(f"  URL: {url}")
        try:
            subprocess.run(
                ["curl", "-L", "--progress-bar", "--fail", "-o", str(dest_zst), url],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            console.print("[red]Download failed.[/red] Check version/edition at:")
            console.print("  https://github.com/winesapOS/winesapOS/releases")
            raise SystemExit(1) from exc
    else:
        console.print(f"[yellow]Archive already downloaded:[/yellow] {dest_zst}")

    console.print("Decompressing...")
    try:
        subprocess.run(
            ["zstd", "--decompress", "--rm", str(dest_zst), "-o", str(dest_img)],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Decompression failed:[/red] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[green]Image ready:[/green] {dest_img}")


@cmd.command("import")
@click.argument("version", default="")
@click.option("--edition", "-e",
              type=click.Choice(["minimal", "performance", "secure"]),
              default="", help="Image edition.")
def ws_import(version: str, edition: str) -> None:
    """Import a fetched winesapOS image into the Incus image store."""
    version = version or os.environ.get("WDT_WINESAPOS_VERSION", _DEFAULT_VERSION)
    edition = edition or os.environ.get("WDT_WINESAPOS_EDITION", _DEFAULT_EDITION)

    if not shutil.which("qemu-img"):
        console.print("[red]qemu-img is required.[/red] Install: sudo apt install qemu-utils")
        raise SystemExit(1)

    fname = _ws_filename(version, edition).removesuffix(".zst")
    img = _ws_dir() / fname
    qcow2 = _ws_dir() / fname.replace(".img", ".qcow2")
    alias = _ws_alias(version, edition)

    if not img.exists():
        console.print(f"[red]Image not found:[/red] {img}")
        console.print(f"Run: wdt winesapos fetch {version} --edition {edition}")
        raise SystemExit(1)

    if _ws_img_exists(version, edition):
        console.print(f"[yellow]Already imported:[/yellow] {alias}")
        return

    if not qcow2.exists():
        console.print("Converting raw image to qcow2...")
        try:
            subprocess.run(
                ["qemu-img", "convert", "-f", "raw", "-O", "qcow2", "-p",
                 str(img), str(qcow2)],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            console.print(f"[red]Conversion failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print(f"Importing [bold]{alias}[/bold] into Incus...")
    try:
        subprocess.run(
            ["incus", "image", "import", str(qcow2),
             "--alias", alias, "--type", "virtual-machine"],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Import failed:[/red] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[green]Imported:[/green] {alias}")
    console.print("Launch with: wdt winesapos launch my-gaming-vm")


@cmd.command("launch")
@click.argument("name")
@click.option("--version", "-v", default="", help="winesapOS version.")
@click.option("--edition", "-e",
              type=click.Choice(["minimal", "performance", "secure"]),
              default="", help="Image edition.")
@click.option("--cpus", "-c", default=0, help="vCPU count (default: 4).")
@click.option("--memory", "-m", default=0, help="Memory in MiB (default: 8192).")
@click.option("--disk", "-d", default="", help="Root disk size (default: 64GiB).")
def ws_launch(
    name: str,
    version: str,
    edition: str,
    cpus: int,
    memory: int,
    disk: str,
) -> None:
    """Launch a winesapOS VM in Incus.

    Fetches and imports the image automatically if not already present.

    \b
    Examples:
      wdt winesapos launch my-gaming-vm
      wdt winesapos launch my-gaming-vm --cpus 8 --memory 16384
      wdt winesapos launch my-gaming-vm --edition performance
    """
    version = version or os.environ.get("WDT_WINESAPOS_VERSION", _DEFAULT_VERSION)
    edition = edition or os.environ.get("WDT_WINESAPOS_EDITION", _DEFAULT_EDITION)
    cpus = cpus or int(os.environ.get("WDT_WINESAPOS_CPUS", "4"))
    memory = memory or int(os.environ.get("WDT_WINESAPOS_MEMORY", "8192"))
    disk = disk or os.environ.get("WDT_WINESAPOS_DISK", "64GiB")

    alias = _ws_alias(version, edition)

    if not _ws_img_exists(version, edition):
        console.print(f"Image [bold]{alias}[/bold] not found — fetching and importing...")
        subprocess.run(
            ["wdt", "winesapos", "fetch", version, "--edition", edition],
            check=True,
        )
        subprocess.run(
            ["wdt", "winesapos", "import", version, "--edition", edition],
            check=True,
        )

    console.print(f"Launching [bold]{name}[/bold] ({alias})")
    console.print(f"  CPUs   : {cpus}")
    console.print(f"  Memory : {memory} MiB")
    console.print(f"  Disk   : {disk}")

    try:
        subprocess.run(
            [
                "incus", "launch", alias, name,
                "--vm",
                f"--config=limits.cpu={cpus}",
                f"--config=limits.memory={memory}MiB",
                f"--device=root,size={disk}",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Launch failed:[/red] {exc}")
        raise SystemExit(1) from exc

    console.print(f"[green]VM launched:[/green] {name}")
    console.print(f"Console: incus console {name}")
    console.print(f"Stop   : incus stop {name}")


@cmd.command("list")
def ws_list() -> None:
    """List winesapOS VMs in Incus."""
    result = subprocess.run(
        ["incus", "list", "--format", "table"],
        capture_output=True, text=True,
    )
    lines = [ln for ln in result.stdout.splitlines() if "winesapos" in ln.lower()]
    if lines:
        for line in lines:
            console.print(line)
    else:
        console.print("[yellow]No winesapOS VMs found.[/yellow]")
        console.print("Launch with: wdt winesapos launch NAME")


@cmd.command("versions")
def ws_versions() -> None:
    """List available winesapOS releases from GitHub."""
    if not shutil.which("curl"):
        console.print("[red]curl is required.[/red]")
        raise SystemExit(1)

    console.print("Fetching winesapOS releases...")
    try:
        result = subprocess.run(
            ["curl", "--silent", "--fail",
             f"{_GITHUB_API}?per_page=10"],
            capture_output=True, text=True, check=True,
        )
        releases = json.loads(result.stdout)
        for r in releases:
            console.print(f"  {r['tag_name']}")
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as exc:
        console.print(f"[red]Failed to fetch releases:[/red] {exc}")
        raise SystemExit(1) from exc
