"""wdt shell — open an interactive shell inside the Waydroid container.

Equivalent to 'incus exec waydroid -- bash' but with convenience options
for running as root or a specific user, and for running one-off commands.

Sub-commands
------------
  wdt shell          Open an interactive bash shell (default)
  wdt shell exec CMD Run a single command and exit
  wdt shell root     Open a root shell
"""

from __future__ import annotations

import os
import subprocess

import click
from rich.console import Console

console = Console()


def _container_name() -> str:
    try:
        from waydroid_toolkit.core.container import get_active as get_backend
        return get_backend().get_info().container_name  # type: ignore[attr-defined]
    except Exception:
        return "waydroid"


@click.group("shell", invoke_without_command=True)
@click.pass_context
def cmd(ctx: click.Context) -> None:
    """Open an interactive shell inside the Waydroid container.

    With no subcommand, opens an interactive bash session.

    \b
    Examples:
      wdt shell
      wdt shell root
      wdt shell exec -- waydroid status
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(shell_enter)


@cmd.command("enter")
@click.option("--user", "-u", default="", help="Run as this user (default: root).")
@click.option("--shell", "shell_bin", default="/bin/bash",
              show_default=True, help="Shell binary to launch.")
def shell_enter(user: str, shell_bin: str) -> None:
    """Open an interactive shell inside the Waydroid container."""
    ct = _container_name()
    cmd_args = ["incus", "exec", ct]
    if user:
        cmd_args += ["--user", user]
    cmd_args += ["--", shell_bin]

    console.print(f"Entering [bold]{ct}[/bold] ({shell_bin})...")
    os.execvp("incus", cmd_args)


@cmd.command("root")
def shell_root() -> None:
    """Open a root shell inside the Waydroid container."""
    ct = _container_name()
    console.print(f"Opening root shell in [bold]{ct}[/bold]...")
    os.execvp("incus", ["incus", "exec", ct, "--", "/bin/bash"])


@cmd.command("exec")
@click.argument("command", nargs=-1, required=True)
@click.option("--user", "-u", default="", help="Run as this user.")
def shell_exec(command: tuple, user: str) -> None:
    """Run COMMAND inside the Waydroid container and exit.

    \b
    Examples:
      wdt shell exec -- waydroid status
      wdt shell exec -- sh -c 'ls /data'
      wdt shell exec --user 1000 -- id
    """
    ct = _container_name()
    cmd_args = ["incus", "exec", ct]
    if user:
        cmd_args += ["--user", user]
    cmd_args += ["--"] + list(command)

    result = subprocess.run(cmd_args)
    raise SystemExit(result.returncode)
