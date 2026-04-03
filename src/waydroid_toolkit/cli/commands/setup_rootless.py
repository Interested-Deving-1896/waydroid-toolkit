"""wdt setup-rootless — configure the system for rootless Waydroid operation.

Checks and optionally fixes prerequisites for running the Waydroid
container as a non-root user via incus-user:

  1. User is not root
  2. incus-user daemon (systemd user service + socket)
  3. Waydroid binder kernel module (binder_linux / ashmem_linux)
  4. UID/GID delegation (subuid/subgid)
  5. waydroid-container Incus profile registered in incus-user
  6. Waydroid service (waydroid-container.service) enabled

Sub-commands
------------
  wdt setup-rootless          Run all checks (report only)
  wdt setup-rootless --fix    Attempt to fix detected issues
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import click
from rich.console import Console

console = Console()


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, **kwargs)


def _ok(msg: str) -> None:
    console.print(f"  [green]✔[/green]  {msg}")


def _warn(msg: str) -> None:
    console.print(f"  [yellow]⚠[/yellow]  {msg}")


def _fail(msg: str) -> None:
    console.print(f"  [red]✘[/red]  {msg}")


def _section(title: str) -> None:
    console.print(f"\n[bold]{title}[/bold]")


def _ask_fix(msg: str, cmd: list[str], fix: bool, issues: list) -> None:
    if fix:
        console.print(f"  Fixing: {msg}")
        result = _run(cmd)
        if result.returncode == 0:
            _ok(f"Fixed: {msg}")
        else:
            _fail(f"Failed to fix: {msg}")
            console.print(f"    [dim]{result.stderr.strip()}[/dim]")
            issues.append(msg)
    else:
        _warn(msg)
        console.print(f"    Run: [cyan]{' '.join(cmd)}[/cyan]")
        issues.append(msg)


@click.command("setup-rootless")
@click.option("--fix", is_flag=True, help="Attempt to automatically fix detected issues.")
@click.option("-Y", "--yes", "yes", is_flag=True,
              help="Non-interactive mode (implies --fix).")
def cmd(fix: bool, yes: bool) -> None:
    """Configure the system for rootless Waydroid operation via incus-user.

    Checks prerequisites and optionally fixes them with --fix.

    \b
    Checks:
      1. Not running as root
      2. incus-user daemon (systemd user service + socket)
      3. Waydroid binder kernel module
      4. UID/GID delegation (subuid/subgid)
      5. waydroid-container Incus profile in incus-user
      6. waydroid-container.service enabled

    \b
    Examples:
      wdt setup-rootless
      wdt setup-rootless --fix
      wdt setup-rootless --yes
    """
    if yes:
        fix = True

    issues: list[str] = []
    uid = os.getuid()
    user = os.environ.get("USER", "")
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    incus_socket = Path(xdg_runtime) / "incus" / "incus.socket"

    # 1. Not root
    _section("1. User check")
    if uid == 0:
        console.print("[red]Run as a regular user, not root.[/red]")
        raise SystemExit(1)
    _ok(f"Running as {user} (uid={uid})")

    # 2. incus-user daemon
    _section("2. incus-user daemon")
    incus_result = _run(["incus", "--version"])
    if incus_result.returncode != 0:
        _fail("incus not found — install Incus: https://linuxcontainers.org/incus/")
        issues.append("incus not installed")
    else:
        _ok(f"incus found: {incus_result.stdout.strip()}")

    if incus_socket.exists():
        _ok(f"incus-user socket: {incus_socket}")
    else:
        svc_check = _run(
            ["systemctl", "--user", "list-unit-files", "incus-user.service"]
        )
        if svc_check.returncode == 0 and "incus-user.service" in svc_check.stdout:
            active = _run(["systemctl", "--user", "is-active", "incus-user.service"])
            if active.returncode == 0:
                _warn("incus-user.service active but socket not found")
                console.print("    Check: [cyan]systemctl --user status incus-user.service[/cyan]")
                issues.append("incus-user socket missing")
            else:
                _ask_fix(
                    "Start and enable incus-user.service",
                    ["systemctl", "--user", "enable", "--now", "incus-user.service"],
                    fix, issues,
                )
        else:
            _fail("incus-user.service not found — install incus-user package")
            issues.append("incus-user not installed")

    # 3. Binder kernel module
    _section("3. Waydroid binder kernel module")
    binder_ok = False
    for mod in ("binder_linux", "ashmem_linux"):
        lsmod = _run(["lsmod"])
        if mod in lsmod.stdout:
            _ok(f"Kernel module loaded: {mod}")
            binder_ok = True
            break
    if not binder_ok:
        # Check if binder is built-in
        builtin = _run(["grep", "-r", "binder", "/sys/module/"], check=False)
        if builtin.returncode == 0:
            _ok("binder: built into kernel")
        else:
            _ask_fix(
                "Load binder_linux kernel module",
                ["sudo", "modprobe", "binder_linux"],
                fix, issues,
            )

    # 4. subuid/subgid
    _section("4. UID/GID delegation (subuid/subgid)")
    for fname in ("/etc/subuid", "/etc/subgid"):
        label = Path(fname).name
        try:
            content = Path(fname).read_text()
            if user and f"{user}:" in content:
                line = next(ln for ln in content.splitlines() if ln.startswith(f"{user}:"))
                _ok(f"{label}: {line}")
            else:
                _ask_fix(
                    f"Add {user} to {fname}",
                    ["sudo", "usermod", f"--add-sub{'uid' if 'uid' in fname else 'gid'}s",
                     "65536-131071", user],
                    fix, issues,
                )
        except OSError:
            _warn(f"{fname} not found")
            issues.append(f"{fname} missing")

    # 5. waydroid-container Incus profile
    _section("5. waydroid-container Incus profile")
    env = os.environ.copy()
    if incus_socket.exists():
        env["INCUS_SOCKET"] = str(incus_socket)

    profile_check = subprocess.run(
        ["incus", "profile", "show", "waydroid"],
        capture_output=True, text=True, env=env,
    )
    if profile_check.returncode == 0:
        _ok("waydroid profile registered in incus-user")
    else:
        # Look for a profile YAML in common locations
        profile_yaml: Path | None = None
        for candidate in [
            Path(__file__).parents[4] / "data" / "profiles" / "waydroid.yaml",
            Path.home() / ".local" / "share" / "waydroid-toolkit" / "profiles" / "waydroid.yaml",
            Path("/usr/share/waydroid-toolkit/profiles/waydroid.yaml"),
        ]:
            if candidate.exists():
                profile_yaml = candidate
                break

        if profile_yaml:
            _ask_fix(
                "Register waydroid profile",
                ["sh", "-c",
                 f"incus profile create waydroid && "
                 f"incus profile edit waydroid < {profile_yaml}"],
                fix, issues,
            )
        else:
            _warn("waydroid profile not registered")
            console.print("    Run: [cyan]wdt profiles install[/cyan]")
            issues.append("waydroid profile not registered")

    # 6. waydroid-container.service
    _section("6. waydroid-container.service")
    svc_enabled = _run(
        ["systemctl", "--user", "is-enabled", "waydroid-container.service"]
    )
    if svc_enabled.returncode == 0:
        _ok("waydroid-container.service enabled")
    else:
        svc_exists = _run(
            ["systemctl", "--user", "list-unit-files", "waydroid-container.service"]
        )
        if svc_exists.returncode == 0 and "waydroid-container" in svc_exists.stdout:
            _ask_fix(
                "Enable waydroid-container.service",
                ["systemctl", "--user", "enable", "waydroid-container.service"],
                fix, issues,
            )
        else:
            _warn("waydroid-container.service not found (may not be needed for your setup)")

    # Summary
    console.print()
    if not issues:
        console.print("[green]All checks passed. Rootless wdt is ready.[/green]")
        console.print()
        console.print("Quick start:")
        console.print("  [cyan]wdt install[/cyan]")
        console.print("  [cyan]wdt status[/cyan]")
    else:
        console.print(f"[yellow]{len(issues)} issue(s) found.[/yellow]")
        if not fix:
            console.print("Re-run with --fix to attempt automatic fixes:")
            console.print("  [cyan]wdt setup-rootless --fix[/cyan]")
        else:
            console.print("Some issues could not be fixed automatically.")
            console.print("Review the output above and resolve them manually.")
        raise SystemExit(1)
