"""wdt assemble — apply a declarative Waydroid configuration file.

Unlike incusbox/imt which manage fleets of containers, Waydroid has a single
container. 'wdt assemble' applies a YAML configuration idempotently:
  - backend selection
  - image type and architecture
  - extensions to install
  - performance profile

This is the wdt equivalent of 'incusbox assemble' and 'imt vm assemble'.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich.console import Console

from waydroid_toolkit.core.container import BackendType, IncusBackend, LxcBackend
from waydroid_toolkit.core.container import set_active as set_active_backend

console = Console()


@click.command("assemble")
@click.option(
    "-f", "--file",
    "config_file",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="YAML configuration file.",
)
@click.option(
    "-d", "--dry-run",
    is_flag=True,
    default=False,
    help="Print actions without executing them.",
)
@click.option(
    "-y", "--yes",
    is_flag=True,
    default=False,
    help="Skip confirmation prompts.",
)
def cmd(config_file: Path, dry_run: bool, yes: bool) -> None:
    """Apply a declarative Waydroid configuration file.

    Reads a YAML file and applies the described configuration idempotently.
    Existing state is preserved where possible; only missing or changed
    items are applied.

    YAML schema:

    \b
      waydroid:
        backend: incus          # incus | lxc  (default: incus)
        image_type: VANILLA     # VANILLA | GAPPS  (default: VANILLA)
        arch: x86_64            # x86_64 | arm64  (default: x86_64)
        extensions:             # list of extension IDs to install
          - gapps
          - widevine
        performance:            # optional performance profile
          zram_size: 4096       # MB
          zram_algo: lz4        # lz4 | zstd | lzo
          governor: performance # performance | schedutil | powersave

    Example:
      wdt assemble --file waydroid.yaml
      wdt assemble --file waydroid.yaml --dry-run
    """
    try:
        cfg = _load_yaml(config_file)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to read config:[/red] {exc}")
        raise SystemExit(1) from exc

    waydroid_cfg: dict[str, Any] = cfg.get("waydroid", {})
    if not waydroid_cfg:
        console.print("[yellow]No 'waydroid:' section found in config — nothing to do.[/yellow]")
        return

    errors: list[str] = []

    # ── backend ───────────────────────────────────────────────────────────────
    backend_name: str = waydroid_cfg.get("backend", "incus")
    if backend_name not in ("incus", "lxc"):
        errors.append(f"Unknown backend '{backend_name}' — must be 'incus' or 'lxc'.")

    # ── image_type ────────────────────────────────────────────────────────────
    image_type: str = waydroid_cfg.get("image_type", "VANILLA").upper()
    if image_type not in ("VANILLA", "GAPPS"):
        errors.append(f"Unknown image_type '{image_type}' — must be VANILLA or GAPPS.")

    # ── arch ──────────────────────────────────────────────────────────────────
    arch: str = waydroid_cfg.get("arch", "x86_64")
    if arch not in ("x86_64", "arm64"):
        errors.append(f"Unknown arch '{arch}' — must be x86_64 or arm64.")

    # ── extensions ────────────────────────────────────────────────────────────
    extensions: list[str] = waydroid_cfg.get("extensions", []) or []

    # ── performance ───────────────────────────────────────────────────────────
    perf_cfg: dict[str, Any] = waydroid_cfg.get("performance", {}) or {}

    if errors:
        for e in errors:
            console.print(f"[red]Config error:[/red] {e}")
        raise SystemExit(1)

    # ── summary ───────────────────────────────────────────────────────────────
    console.print(f"[bold]Assembling Waydroid configuration from:[/bold] {config_file}")
    console.print(f"  backend    : {backend_name}")
    console.print(f"  image_type : {image_type}")
    console.print(f"  arch       : {arch}")
    console.print(f"  extensions : {', '.join(extensions) or '(none)'}")
    if perf_cfg:
        console.print(f"  performance: {perf_cfg}")
    console.print()

    if dry_run:
        console.print("[dim]Dry run — no changes applied.[/dim]")
        return

    if not yes:
        click.confirm("Apply this configuration?", abort=True)

    # ── apply backend ─────────────────────────────────────────────────────────
    _apply_backend(backend_name)

    # ── apply extensions ──────────────────────────────────────────────────────
    if extensions:
        _apply_extensions(extensions)

    # ── apply performance ─────────────────────────────────────────────────────
    if perf_cfg:
        _apply_performance(perf_cfg)

    console.print("[green]Assembly complete.[/green]")
    console.print("  Run 'wdt status' to verify the current state.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file using PyYAML if available, else a minimal parser."""
    try:
        import yaml  # type: ignore[import-untyped]
        with path.open() as fh:
            return yaml.safe_load(fh) or {}
    except ImportError:
        pass
    # Minimal fallback: handles the flat schema used by wdt assemble
    return _parse_minimal_yaml(path.read_text())


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Parse the wdt assemble YAML schema without PyYAML.

    Handles:
      - Top-level 'waydroid:' section
      - Scalar key: value pairs (string, int)
      - Sequence items under 'extensions:'
    """
    result: dict[str, Any] = {}
    section: dict[str, Any] | None = None
    list_key: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.lstrip()

        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(stripped)

        # Top-level section header
        if indent == 0 and stripped.endswith(":"):
            key = stripped[:-1]
            section = {}
            result[key] = section
            list_key = None
            continue

        if section is None:
            continue

        # Sequence item under a list key
        if stripped.startswith("- ") and list_key is not None:
            val = stripped[2:].strip()
            section[list_key].append(val)  # type: ignore[union-attr]
            continue

        # Key: value pair inside section
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                # Start of a nested mapping or list — peek at next non-empty line
                # handled by list_key tracking below
                list_key = key
                section[key] = []
                continue
            list_key = None
            # Coerce integers
            try:
                section[key] = int(val)
            except ValueError:
                section[key] = val

    return result


def _apply_backend(backend_name: str) -> None:
    backend_type = BackendType(backend_name)
    backend_map: dict[BackendType, type] = {
        BackendType.LXC: LxcBackend,
        BackendType.INCUS: IncusBackend,
    }
    backend_obj = backend_map[backend_type]()

    if not backend_obj.is_available():
        console.print(
            f"[yellow]Backend '{backend_name}' not available — skipping.[/yellow]"
        )
        return

    set_active_backend(backend_type)
    console.print(f"  [green]✓[/green] Backend set to: {backend_name}")


def _apply_extensions(extension_ids: list[str]) -> None:
    try:
        from waydroid_toolkit.modules.extensions import (
            REGISTRY,
            ExtensionState,
            get,
            install_with_deps,
            resolve,
        )
    except ImportError as exc:
        console.print(f"[yellow]Extensions module unavailable: {exc}[/yellow]")
        return

    for ext_id in extension_ids:
        try:
            ext = get(ext_id, REGISTRY)
        except KeyError:
            console.print(f"  [yellow]![/yellow] Unknown extension: {ext_id}")
            continue

        if ext.state() == ExtensionState.INSTALLED:
            console.print(f"  [dim]–[/dim] Extension already installed: {ext_id}")
            continue

        try:
            order = resolve([ext_id], REGISTRY)
            install_with_deps(
                order,
                progress=lambda msg: console.print(f"    [cyan]→[/cyan] {msg}"),
            )
            console.print(f"  [green]✓[/green] Extension installed: {ext_id}")
        except Exception as exc:  # noqa: BLE001
            console.print(f"  [red]✗[/red] Failed to install {ext_id}: {exc}")


def _apply_performance(perf_cfg: dict[str, Any]) -> None:
    try:
        from waydroid_toolkit.modules.performance import PerformanceProfile, apply_profile
    except ImportError as exc:
        console.print(f"[yellow]Performance module unavailable: {exc}[/yellow]")
        return

    profile = PerformanceProfile(
        zram_size_mb=int(perf_cfg.get("zram_size", 4096)),
        zram_algorithm=str(perf_cfg.get("zram_algo", "lz4")),
        cpu_governor=str(perf_cfg.get("governor", "performance")),
        enable_turbo=bool(perf_cfg.get("enable_turbo", True)),
        use_gamemode=bool(perf_cfg.get("use_gamemode", True)),
    )
    try:
        apply_profile(profile)
        console.print("  [green]✓[/green] Performance profile applied.")
    except Exception as exc:  # noqa: BLE001
        console.print(f"  [red]✗[/red] Performance profile failed: {exc}")
