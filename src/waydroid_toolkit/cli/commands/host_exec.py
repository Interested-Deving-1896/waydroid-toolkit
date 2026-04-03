"""wdt host-exec — run a host command from inside the Waydroid container.

Executes a command on the host by running it inside the Waydroid container
via `incus exec`, using nsenter to escape into the host's namespaces.
Mirrors the incusbox-host-exec pattern.

Usage:
  wdt host-exec COMMAND [ARGS...]
"""

from __future__ import annotations

import subprocess
import sys

import click
from rich.console import Console

console = Console()


def _container_name() -> str:
    try:
        from waydroid_toolkit.core.container import get_active as get_backend
        b = get_backend()
        return b.get_info().container_name  # type: ignore[attr-defined]
    except Exception:
        return "waydroid"


@click.command("host-exec")
@click.argument("command", nargs=-1, required=True)
@click.option(
    "--container", "-c", default="",
    help="Container name (default: active Waydroid container).",
)
def cmd(command: tuple[str, ...], container: str) -> None:
    """Run a host command from inside the Waydroid container via nsenter.

    The command is executed in the host's mount, network, PID, and UTS
    namespaces by running nsenter inside the container.

    \b
    Examples:
      wdt host-exec systemctl --user status
      wdt host-exec flatpak run org.mozilla.firefox
      wdt host-exec bash
    """
    ct = container or _container_name()

    # Build the nsenter invocation that runs inside the container.
    # /proc/1/ns/* inside the container points to the host's PID 1 namespaces
    # when the container shares the host PID namespace (Incus default for
    # privileged containers). For unprivileged containers the fallback is
    # chroot /run/host.
    nsenter_cmd = [
        "nsenter",
        "--mount=/proc/1/ns/mnt",
        "--uts=/proc/1/ns/uts",
        "--ipc=/proc/1/ns/ipc",
        "--net=/proc/1/ns/net",
        "--pid=/proc/1/ns/pid",
        "--target=1",
        "--",
        *command,
    ]

    incus_exec = [
        "incus", "exec", ct,
        "--",
        "sh", "-c",
        # Try nsenter first; fall back to chroot /run/host if /proc/1/ns/mnt
        # is not readable (unprivileged container without SYS_PTRACE).
        f"if [ -r /proc/1/ns/mnt ]; then "
        f"exec {' '.join(_shell_quote(a) for a in nsenter_cmd)}; "
        f"else exec chroot /run/host {' '.join(_shell_quote(a) for a in command)}; fi",
    ]

    result = subprocess.run(incus_exec)
    sys.exit(result.returncode)


def _shell_quote(s: str) -> str:
    """Minimal shell quoting for embedding in a sh -c string."""
    import shlex
    return shlex.quote(s)
