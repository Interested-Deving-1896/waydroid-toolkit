"""wdt doctor — check prerequisites and runtime environment."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()

# Kernel modules required for Waydroid
_REQUIRED_MODULES = ["binder_linux"]
_OPTIONAL_MODULES = ["ashmem_linux"]

# Character device nodes the Android container needs
_REQUIRED_DEVICES = ["/dev/binder", "/dev/ashmem"]
_OPTIONAL_DEVICES = [
    "/dev/dri/renderD128",
    "/dev/dma_heap/system",
    "/dev/dma_heap/system-uncached",
]


def _check(label: str, ok: bool, detail: str = "", fix: str = "") -> tuple[str, str, str, str]:
    """Return a table row tuple: (label, status, detail, fix hint)."""
    status = "[green]✅ ok[/green]" if ok else "[red]❌ fail[/red]"
    return label, status, detail, fix


def _warn(label: str, detail: str = "", fix: str = "") -> tuple[str, str, str, str]:
    return label, "[yellow]⚠  warn[/yellow]", detail, fix


def _module_loaded(name: str) -> bool:
    try:
        result = subprocess.run(
            ["lsmod"], capture_output=True, text=True, timeout=5
        )
        return name in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _device_exists(path: str) -> bool:
    return Path(path).exists()


def _audio_socket() -> tuple[str, str]:
    """Return (backend_name, socket_path) for the detected audio backend."""
    runtime = Path(
        subprocess.run(
            ["bash", "-c", "echo $XDG_RUNTIME_DIR"],
            capture_output=True, text=True,
        ).stdout.strip() or f"/run/user/{os.getuid()}"
    )
    pw_sock = runtime / "pipewire-0"
    pa_sock = runtime / "pulse" / "native"
    if pw_sock.exists():
        return "pipewire", str(pw_sock)
    if pa_sock.exists():
        return "pulseaudio", str(pa_sock)
    return "none", ""


@click.command("doctor")
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON.")
def cmd(as_json: bool) -> None:
    """Check prerequisites and runtime environment for Waydroid.

    Verifies: Waydroid binary, container backend, kernel modules,
    device nodes, ADB, audio socket, and Incus-specific requirements
    when the Incus backend is active.
    """
    rows: list[tuple[str, str, str, str]] = []
    fail_count = 0
    warn_count = 0

    def add(row: tuple[str, str, str, str]) -> None:
        nonlocal fail_count, warn_count
        rows.append(row)
        if "fail" in row[1]:
            fail_count += 1
        elif "warn" in row[1]:
            warn_count += 1

    # ── Waydroid binary ───────────────────────────────────────────────────────
    waydroid_ok = shutil.which("waydroid") is not None
    add(_check(
        "waydroid binary",
        waydroid_ok,
        shutil.which("waydroid") or "",
        "" if waydroid_ok else "Install Waydroid: wdt install",
    ))

    # ── Waydroid initialised ──────────────────────────────────────────────────
    if waydroid_ok:
        from waydroid_toolkit.core.waydroid import is_initialized
        init_ok = is_initialized()
        add(_check(
            "waydroid initialized",
            init_ok,
            fix="" if init_ok else "Run: wdt install --init-only",
        ))

    # ── Container backend ─────────────────────────────────────────────────────
    try:
        from waydroid_toolkit.core.container import get_active
        backend = get_active()
        info = backend.get_info()
        add(_check(
            "container backend",
            True,
            f"{info.backend_type.value} {info.version}",
        ))
        active_backend_type = info.backend_type
    except RuntimeError as exc:
        add(_check("container backend", False, fix=str(exc)))
        active_backend_type = None

    # ── Incus-specific checks ─────────────────────────────────────────────────
    from waydroid_toolkit.core.container import BackendType

    if active_backend_type == BackendType.INCUS:
        # incus binary
        incus_bin = shutil.which("incus")
        add(_check(
            "incus binary",
            incus_bin is not None,
            incus_bin or "",
            fix="" if incus_bin else "Install Incus: https://linuxcontainers.org/incus/",
        ))

        # waydroid container exists in Incus
        if incus_bin:
            try:
                result = subprocess.run(
                    ["incus", "info", "waydroid"],
                    capture_output=True, text=True, timeout=10,
                )
                container_ok = result.returncode == 0
                add(_check(
                    "incus 'waydroid' container",
                    container_ok,
                    fix="" if container_ok else "Run: wdt backend incus-setup",
                ))
            except (FileNotFoundError, subprocess.TimeoutExpired):
                add(_check("incus 'waydroid' container", False,
                           fix="Run: wdt backend incus-setup"))

    elif active_backend_type == BackendType.LXC:
        # Suggest upgrading to Incus
        incus_available = shutil.which("incus") is not None
        if incus_available:
            add(_warn(
                "container backend",
                "Incus is available but LXC is active",
                fix="Run: wdt backend set incus",
            ))

    # ── Kernel modules ────────────────────────────────────────────────────────
    for mod in _REQUIRED_MODULES:
        loaded = _module_loaded(mod)
        add(_check(
            f"kernel module: {mod}",
            loaded,
            fix="" if loaded else f"sudo modprobe {mod}",
        ))

    for mod in _OPTIONAL_MODULES:
        loaded = _module_loaded(mod)
        if not loaded:
            add(_warn(
                f"kernel module: {mod}",
                "optional — needed on older kernels",
                fix=f"sudo modprobe {mod}",
            ))

    # ── Device nodes ──────────────────────────────────────────────────────────
    for dev in _REQUIRED_DEVICES:
        exists = _device_exists(dev)
        add(_check(
            f"device: {dev}",
            exists,
            fix="" if exists else f"sudo modprobe binder_linux && ls {dev}",
        ))

    for dev in _OPTIONAL_DEVICES:
        exists = _device_exists(dev)
        if not exists:
            add(_warn(f"device: {dev}", "optional — GPU acceleration"))

    # ── ADB ───────────────────────────────────────────────────────────────────
    adb_bin = shutil.which("adb")
    add(_check(
        "adb binary",
        adb_bin is not None,
        adb_bin or "",
        fix="" if adb_bin else "Install: sudo apt install adb  # or platform-tools",
    ))

    if adb_bin:
        try:
            from waydroid_toolkit.core.adb import is_connected as adb_connected
            connected = adb_connected()
            if connected:
                add(_check("adb connected", True))
            else:
                add(_warn("adb connected", "Waydroid may not be running"))
        except Exception:  # noqa: BLE001  # broad catch intentional — adb state is best-effort
            add(_warn("adb connected", "could not determine state"))

    # ── Audio ─────────────────────────────────────────────────────────────────
    audio_backend, audio_sock = _audio_socket()
    if audio_backend != "none":
        add(_check("audio socket", True, f"{audio_backend}: {audio_sock}"))
    else:
        add(_warn(
            "audio socket",
            "no PipeWire or PulseAudio socket found",
            fix="Start PipeWire or PulseAudio before launching Waydroid",
        ))

    # ── Output ────────────────────────────────────────────────────────────────
    if as_json:
        import json
        import re

        def strip_markup(s: str) -> str:
            return re.sub(r"\[/?[^\]]+\]", "", s)

        data = [
            {
                "check": r[0],
                "status": strip_markup(r[1]),
                "detail": r[2],
                "fix": r[3],
            }
            for r in rows
        ]
        console.print_json(json.dumps(data, indent=2))
    else:
        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Detail")
        table.add_column("Fix")

        for row in rows:
            table.add_row(*row)

        console.print()
        console.print(table)
        console.print()

        if fail_count == 0 and warn_count == 0:
            console.print("[green]All checks passed.[/green]")
        elif fail_count == 0:
            console.print(
                f"[yellow]{warn_count} warning(s). "
                "Waydroid should work but some features may be limited.[/yellow]"
            )
        else:
            console.print(
                f"[red]{fail_count} check(s) failed[/red], "
                f"[yellow]{warn_count} warning(s)[/yellow]."
            )
            raise SystemExit(1)
