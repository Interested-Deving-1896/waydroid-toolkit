"""wdt update — check for and install waydroid-toolkit updates from GitHub."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import click
from rich.console import Console

console = Console()

_GITHUB_REPO = "Interested-Deving-1896/waydroid-toolkit"
_GITHUB_API = f"https://api.github.com/repos/{_GITHUB_REPO}/releases/latest"


def _current_version() -> str:
    """Read version from installed package metadata."""
    try:
        from importlib.metadata import version
        return version("waydroid-toolkit")
    except Exception:
        return "0.0.0"


def _version_gt(v1: str, v2: str) -> bool:
    """Return True if v1 > v2 (semver, strips leading 'v')."""
    def parts(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.lstrip("v").split(".")[:3])
    try:
        return parts(v1) > parts(v2)
    except ValueError:
        return False


def _fetch_release() -> dict:
    """Fetch the latest GitHub release JSON."""
    import json
    req = urllib.request.Request(
        _GITHUB_API,
        headers={"Accept": "application/vnd.github.v3+json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read())


@click.group("update")
def cmd() -> None:
    """Check for and install waydroid-toolkit updates."""


@cmd.command("check")
def update_check() -> None:
    """Check GitHub for a newer version."""
    current = _current_version()
    console.print(f"  Current version : v{current}")
    console.print("  Checking GitHub for updates...")

    try:
        release = _fetch_release()
    except Exception as exc:
        console.print(f"[yellow]Could not reach GitHub API: {exc}[/yellow]")
        console.print(f"  Check manually: https://github.com/{_GITHUB_REPO}/releases")
        return

    latest_tag = release.get("tag_name", "")
    latest = latest_tag.lstrip("v")
    if not latest:
        console.print("[yellow]Could not determine latest version.[/yellow]")
        return

    console.print(f"  Latest version  : v{latest}")

    if _version_gt(latest, current):
        console.print()
        console.print(f"[green]Update available:[/green] v{current} → v{latest}")
        body = (release.get("body") or "")[:400]
        if body:
            console.print()
            console.print("[dim]Release notes:[/dim]")
            for line in body.splitlines()[:10]:
                console.print(f"  {line}")
        console.print()
        console.print("  Update with: [cyan]wdt update install[/cyan]")
    else:
        console.print(f"[green]waydroid-toolkit is up to date (v{current})[/green]")


@cmd.command("install")
def update_install() -> None:
    """Download and install the latest version."""
    current = _current_version()
    console.print(f"  Current version : v{current}")
    console.print("  Fetching latest release...")

    try:
        release = _fetch_release()
    except Exception as exc:
        console.print(f"[red]Could not reach GitHub API: {exc}[/red]")
        raise SystemExit(1) from exc

    latest_tag = release.get("tag_name", "")
    latest = latest_tag.lstrip("v")
    if not latest:
        console.print("[red]Could not determine latest version.[/red]")
        raise SystemExit(1)

    if not _version_gt(latest, current):
        console.print(f"[green]Already up to date (v{current})[/green]")
        return

    console.print(f"  Updating: v{current} → v{latest}")

    # Detect install method
    pkg_root = Path(__file__).parent.parent.parent.parent.parent
    is_git = (pkg_root / ".git").exists()
    is_pip = shutil.which("pip") is not None or shutil.which("pip3") is not None

    if is_git:
        console.print("  [dim]Git repository detected — pulling latest...[/dim]")
        result = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=str(pkg_root),
        )
        if result.returncode == 0:
            subprocess.run(
                ["git", "checkout", f"v{latest}"],
                cwd=str(pkg_root),
            )
        if result.returncode != 0:
            subprocess.run(["git", "pull", "origin", "main"], cwd=str(pkg_root), check=True)
        console.print(f"[green]Updated via git to v{latest}[/green]")

    elif is_pip:
        console.print("  [dim]pip install detected — upgrading via pip...[/dim]")
        pip = shutil.which("pip3") or shutil.which("pip") or "pip"
        result = subprocess.run(
            [pip, "install", "--upgrade",
             f"git+https://github.com/{_GITHUB_REPO}.git@v{latest}"],
        )
        if result.returncode != 0:
            console.print("[red]pip upgrade failed.[/red]")
            raise SystemExit(1)
        console.print(f"[green]Updated to v{latest} via pip[/green]")

    else:
        # Tarball fallback
        tarball_url = release.get("tarball_url", "")
        if not tarball_url:
            console.print("[red]No tarball URL in release.[/red]")
            raise SystemExit(1)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_tar = Path(tmp) / f"wdt-{latest}.tar.gz"
            console.print(f"  [dim]Downloading v{latest}...[/dim]")
            urllib.request.urlretrieve(tarball_url, tmp_tar)  # noqa: S310
            console.print("  [dim]Extracting...[/dim]")
            with tarfile.open(tmp_tar) as tf:
                tf.extractall(tmp)
            # Find extracted dir
            extracted = next(
                (Path(tmp) / d for d in Path(tmp).iterdir()
                 if (Path(tmp) / d).is_dir() and d.name != tmp_tar.name),
                None,
            )
            if extracted and (extracted / "pyproject.toml").exists():
                pip = shutil.which("pip3") or shutil.which("pip") or "pip"
                subprocess.run([pip, "install", str(extracted)], check=True)
                console.print(f"[green]Updated to v{latest}[/green]")
            else:
                console.print("[red]Could not locate extracted package.[/red]")
                raise SystemExit(1)

    new_ver = _current_version()
    console.print(f"  Verified: v{new_ver}")
