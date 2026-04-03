"""wdt template — list, inspect, and apply Waydroid container resource templates."""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()

# Templates ship in data/templates/ relative to the package root.
_PKG_ROOT = Path(__file__).parent.parent.parent.parent.parent  # repo root
_BUILTIN_TEMPLATES_DIR = _PKG_ROOT / "data" / "templates"
_USER_TEMPLATES_DIR = Path.home() / ".config" / "waydroid-toolkit" / "templates"


def _templates_dir() -> Path:
    """Return the active templates directory (user overrides built-in)."""
    import os
    env = os.environ.get("WDT_TEMPLATES_DIR")
    if env:
        return Path(env)
    if _USER_TEMPLATES_DIR.exists():
        return _USER_TEMPLATES_DIR
    return _BUILTIN_TEMPLATES_DIR


def _parse_template(path: Path) -> dict[str, object]:
    """Minimal line-based YAML parser for template files."""
    data: dict[str, object] = {}
    section: str | None = None
    with path.open() as f:
        for raw in f:
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if line[0].isspace():
                # nested key under current section
                if section is not None:
                    stripped = line.strip()
                    if ":" in stripped:
                        k, _, v = stripped.partition(":")
                        if section not in data:
                            data[section] = {}
                        data[section][k.strip()] = v.strip().strip('"')  # type: ignore[index]
            else:
                if ":" in line:
                    k, _, v = line.partition(":")
                    k = k.strip()
                    v = v.strip().strip('"')
                    if v:
                        data[k] = v
                        section = None
                    else:
                        section = k
    return data


@click.group("template")
def cmd() -> None:
    """List, inspect, and apply Waydroid container resource templates."""


@cmd.command("list")
def template_list() -> None:
    """List available templates."""
    tdir = _templates_dir()
    yamls = sorted(tdir.glob("*.yaml")) if tdir.exists() else []

    if not yamls:
        console.print(f"[yellow]No templates found in {tdir}[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("NAME", style="cyan", min_width=12)
    table.add_column("CPU")
    table.add_column("MEMORY")
    table.add_column("DESCRIPTION")

    for f in yamls:
        d = _parse_template(f)
        res = d.get("resources", {})
        cpu = res.get("cpu", "-") if isinstance(res, dict) else "-"  # type: ignore[union-attr]
        mem = res.get("memory", "-") if isinstance(res, dict) else "-"  # type: ignore[union-attr]
        desc = str(d.get("description", ""))
        table.add_row(f.stem, str(cpu), str(mem), desc)

    console.print(table)
    console.print()
    console.print(f"Templates directory: {tdir}")
    console.print("Apply: [cyan]wdt template apply <name>[/cyan]")


@cmd.command("show")
@click.argument("name")
def template_show(name: str) -> None:
    """Show full details of a template."""
    tdir = _templates_dir()
    path = tdir / f"{name}.yaml"
    if not path.exists():
        console.print(f"[red]Template not found:[/red] {name}")
        raise SystemExit(1)

    d = _parse_template(path)
    res = d.get("resources", {})
    perf = d.get("performance", {})

    console.print(f"[bold]Template:[/bold] {name}")
    console.print()
    console.print(f"  Description : {d.get('description', '(none)')}")
    if isinstance(res, dict):
        console.print(f"  CPU         : {res.get('cpu', '(not set)')}")
        console.print(f"  Memory      : {res.get('memory', '(not set)')}")
    if isinstance(perf, dict) and perf:
        console.print(f"  Governor    : {perf.get('governor', '(not set)')}")
        console.print(f"  ZRAM        : {perf.get('zram', 'false')}")


@cmd.command("apply")
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="Show what would be applied without making changes.")
def template_apply(name: str, dry_run: bool) -> None:
    """Apply a template's resource limits to the Waydroid container.

    Sets incus config limits.cpu and limits.memory on the waydroid container.
    """
    from waydroid_toolkit.core.container.backend import get_backend

    tdir = _templates_dir()
    path = tdir / f"{name}.yaml"
    if not path.exists():
        console.print(f"[red]Template not found:[/red] {name}")
        raise SystemExit(1)

    d = _parse_template(path)
    res = d.get("resources", {})
    if not isinstance(res, dict) or not res:
        console.print("[yellow]Template has no resource settings to apply.[/yellow]")
        return

    b = get_backend()
    info = b.get_info()  # type: ignore[attr-defined]
    container = info.container_name

    cpu = res.get("cpu")
    mem = res.get("memory")

    console.print(f"[bold]Applying template '{name}' to container '{container}'[/bold]")
    if cpu:
        console.print(f"  limits.cpu    → {cpu}")
        if not dry_run:
            subprocess.run(
                ["incus", "config", "set", container, "limits.cpu", str(cpu)],
                check=True,
            )
    if mem:
        console.print(f"  limits.memory → {mem}")
        if not dry_run:
            subprocess.run(
                ["incus", "config", "set", container, "limits.memory", mem],
                check=True,
            )

    if dry_run:
        console.print("[yellow](dry-run — no changes made)[/yellow]")
    else:
        console.print(f"[green]Template '{name}' applied.[/green]")
        console.print("Restart the container for changes to take effect.")
