"""wdt packages — install/remove Android apps and manage F-Droid repos."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from waydroid_toolkit.modules.packages import (
    add_repo,
    get_installed_packages,
    install_apk_file,
    install_apk_url,
    list_repos,
    remove_package,
    remove_repo,
    search_repos,
)

console = Console()


@click.group("packages")
def cmd() -> None:
    """Manage Android packages and F-Droid repositories."""


@cmd.command("install")
@click.argument("source")
def install_pkg(source: str) -> None:
    """Install an APK from a local file path or URL."""
    def progress(msg: str) -> None:
        console.print(f"  [cyan]→[/cyan] {msg}")

    if source.startswith("http://") or source.startswith("https://"):
        install_apk_url(source, progress)
    else:
        install_apk_file(Path(source), progress)
    console.print("[green]Done.[/green]")


@cmd.command("remove")
@click.argument("package")
def remove_pkg(package: str) -> None:
    """Uninstall an Android package by package name."""
    remove_package(package, progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print("[green]Done.[/green]")


@cmd.command("list")
def list_pkgs() -> None:
    """List installed third-party Android packages."""
    pkgs = get_installed_packages()
    if not pkgs:
        console.print("[yellow]No third-party packages installed (or ADB not connected).[/yellow]")
        return
    for pkg in sorted(pkgs):
        console.print(f"  {pkg}")


@cmd.command("search")
@click.argument("query")
def search_pkgs(query: str) -> None:
    """Search F-Droid repos for a package."""
    results = search_repos(query)
    if not results:
        console.print(f"[yellow]No results for '{query}'.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Package ID")
    table.add_column("Name")
    table.add_column("Repo")
    for r in results:
        table.add_row(r["id"], r["name"], r["repo"])
    console.print(table)


@cmd.group("repo")
def repo_group() -> None:
    """Manage F-Droid repositories."""


@repo_group.command("add")
@click.argument("name")
@click.argument("url")
def repo_add(name: str, url: str) -> None:
    """Add an F-Droid repo. NAME is a short label, URL is the repo base URL."""
    add_repo(name, url, progress=lambda msg: console.print(f"  [cyan]→[/cyan] {msg}"))
    console.print(f"[green]Repo '{name}' added.[/green]")


@repo_group.command("remove")
@click.argument("name")
def repo_remove(name: str) -> None:
    """Remove an F-Droid repo by name."""
    remove_repo(name)
    console.print(f"[green]Repo '{name}' removed.[/green]")


@repo_group.command("list")
def repo_list() -> None:
    """List configured F-Droid repos."""
    repos = list_repos()
    if not repos:
        console.print("[yellow]No repos configured.[/yellow]")
        return
    for r in repos:
        console.print(f"  [bold]{r['name']}[/bold]  {r['url']}")


cmd.add_command(repo_group, name="repo")
