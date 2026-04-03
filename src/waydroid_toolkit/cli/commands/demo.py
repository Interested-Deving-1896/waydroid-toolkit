"""wdt demo — manage a local incus-demo-server instance.

incus-demo-server is a Go daemon that exposes a REST API for spinning up
short-lived, resource-capped Incus instances on demand — the backend behind
linuxcontainers.org/incus/try-it.

References:
  https://github.com/lxc/incus-demo-server
  https://linuxcontainers.org/incus/try-it

Sub-commands
------------
  wdt demo install          Install the binary via go install
  wdt demo config [--edit]  Show or edit the generated config.yaml
  wdt demo start            Start the server in the background
  wdt demo stop             Stop the running server
  wdt demo restart          Stop then start
  wdt demo status           Show whether the server is running
  wdt demo logs [--follow]  Show server logs
  wdt demo url              Print the API base URL
  wdt demo test             Smoke-test the running server via curl
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import click
from rich.console import Console

console = Console()

_DEFAULT_DIR = Path.home() / ".local" / "share" / "waydroid-toolkit" / "demo-server"
_MODULE = "github.com/lxc/incus-demo-server/cmd/incus-demo-server@latest"


def _demo_dir() -> Path:
    return Path(os.environ.get("WDT_DEMO_DIR", str(_DEFAULT_DIR)))


def _demo_bin() -> Path:
    return _demo_dir() / "incus-demo-server"


def _demo_cfg() -> Path:
    return _demo_dir() / "config.yaml"


def _demo_pid() -> Path:
    return _demo_dir() / "demo-server.pid"


def _demo_log() -> Path:
    return _demo_dir() / "demo-server.log"


def _demo_addr() -> str:
    return os.environ.get("WDT_DEMO_ADDR", "[::]:8080")


def _demo_port() -> str:
    return _demo_addr().rsplit(":", 1)[-1]


def _demo_url() -> str:
    return f"http://localhost:{_demo_port()}"


def _is_running() -> bool:
    pid_file = _demo_pid()
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, OSError):
        return False


def _write_config() -> None:
    cfg = _demo_cfg()
    cfg.parent.mkdir(parents=True, exist_ok=True)
    expiry = os.environ.get("WDT_DEMO_EXPIRY", "3600")
    image = os.environ.get("WDT_DEMO_IMAGE", "ubuntu/24.04")
    addr = _demo_addr()
    cfg.write_text(f"""\
server:
  api:
    address: "{addr}"
  limits:
    total: {os.environ.get("WDT_DEMO_TOTAL", "10")}
    ip: {os.environ.get("WDT_DEMO_IP_LIMIT", "2")}
  terms: |
    This is a local wdt demo server.
    Instances expire after {expiry} seconds.
incus:
  instance:
    allocate:
      count: {os.environ.get("WDT_DEMO_PREALLOCATE", "2")}
    expiry: {expiry}
    source:
      image: "{image}"
      type: "container"
    profiles:
      - default
    limits:
      cpu: {os.environ.get("WDT_DEMO_CPU", "1")}
      disk: {os.environ.get("WDT_DEMO_DISK", "5GiB")}
      memory: {os.environ.get("WDT_DEMO_MEMORY", "512MiB")}
  session:
    command: ["bash"]
    expiry: {expiry}
    console_only: true
""")


@click.group("demo")
def cmd() -> None:
    """Manage a local incus-demo-server instance.

    incus-demo-server is the backend behind linuxcontainers.org/incus/try-it.
    See https://github.com/lxc/incus-demo-server
    """


@cmd.command("install")
def demo_install() -> None:
    """Install the incus-demo-server binary via go install."""
    if not shutil.which("go"):
        console.print("[red]go is required.[/red] See https://go.dev/dl/")
        raise SystemExit(1)
    _demo_dir().mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GOBIN": str(_demo_dir())}
    console.print(f"Installing [bold]{_MODULE}[/bold]...")
    try:
        subprocess.run(["go", "install", _MODULE], env=env, check=True)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]go install failed:[/red] {exc}")
        raise SystemExit(1) from exc
    console.print(f"[green]Installed:[/green] {_demo_bin()}")
    console.print("Generate config with: wdt demo config")


@cmd.command("config")
@click.option("--edit", "-e", is_flag=True, help="Open config in $EDITOR.")
def demo_config(edit: bool) -> None:
    """Show or generate the demo server config.yaml."""
    cfg = _demo_cfg()
    if not cfg.exists():
        _write_config()
        console.print(f"[green]Config written:[/green] {cfg}")

    if edit:
        editor = os.environ.get("EDITOR", "vi")
        os.execvp(editor, [editor, str(cfg)])
    else:
        console.print(cfg.read_text())


@cmd.command("start")
def demo_start() -> None:
    """Start the demo server in the background."""
    if not _demo_bin().exists():
        console.print("[red]Not installed.[/red] Run: wdt demo install")
        raise SystemExit(1)

    if not _demo_cfg().exists():
        _write_config()
        console.print(f"Generated config: {_demo_cfg()}")

    if _is_running():
        pid = int(_demo_pid().read_text().strip())
        console.print(f"[yellow]Already running (PID {pid}).[/yellow]")
        return

    _demo_dir().mkdir(parents=True, exist_ok=True)
    log_file = _demo_log().open("a")
    proc = subprocess.Popen(
        [str(_demo_bin())],
        cwd=str(_demo_dir()),
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
    )
    _demo_pid().write_text(str(proc.pid))
    time.sleep(1)

    if _is_running():
        console.print(f"[green]Demo server started[/green] (PID {proc.pid})")
        console.print(f"  API : {_demo_url()}")
        console.print("Test with: wdt demo test")
    else:
        console.print("[red]Failed to start.[/red] Check: wdt demo logs")
        raise SystemExit(1)


@cmd.command("stop")
def demo_stop() -> None:
    """Stop the running demo server."""
    if not _is_running():
        console.print("[yellow]Not running.[/yellow]")
        return
    pid = int(_demo_pid().read_text().strip())
    os.kill(pid, signal.SIGTERM)
    _demo_pid().unlink(missing_ok=True)
    console.print(f"[green]Demo server stopped[/green] (was PID {pid})")


@cmd.command("restart")
@click.pass_context
def demo_restart(ctx: click.Context) -> None:
    """Stop then start the demo server."""
    ctx.invoke(demo_stop)
    time.sleep(1)
    ctx.invoke(demo_start)


@cmd.command("status")
def demo_status() -> None:
    """Show whether the demo server is running."""
    if _is_running():
        pid = int(_demo_pid().read_text().strip())
        console.print(f"[green]Running[/green] (PID {pid})")
        console.print(f"  API : {_demo_url()}")
        console.print(f"  Log : {_demo_log()}")
    else:
        console.print("[yellow]Stopped[/yellow]")


@cmd.command("logs")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (tail -f).")
def demo_logs(follow: bool) -> None:
    """Show demo server logs."""
    log = _demo_log()
    if not log.exists():
        console.print(f"[yellow]No log file:[/yellow] {log}")
        return
    if follow:
        subprocess.run(["tail", "-f", str(log)])
    else:
        console.print(log.read_text())


@cmd.command("url")
def demo_url() -> None:
    """Print the demo server API base URL."""
    console.print(_demo_url())


@cmd.command("test")
def demo_test() -> None:
    """Smoke-test the running demo server via curl."""
    if not shutil.which("curl"):
        console.print("[red]curl is required.[/red]")
        raise SystemExit(1)

    url = _demo_url()
    console.print(f"Testing demo server at [bold]{url}[/bold]...")

    for endpoint in ["/1.0", "/1.0/terms"]:
        try:
            subprocess.run(
                ["curl", "--silent", "--fail", "--max-time", "5", f"{url}{endpoint}"],
                check=True,
                capture_output=True,
            )
            console.print(f"  [green]✓[/green] {endpoint}")
        except subprocess.CalledProcessError:
            console.print(f"  [red]✗[/red] {endpoint} — not responding")
            console.print("Is the server running? Try: wdt demo start")
            raise SystemExit(1)

    console.print()
    console.print("[green]Server is healthy.[/green]")
    console.print(f"Start a session: curl -X POST {url}/1.0/start")
