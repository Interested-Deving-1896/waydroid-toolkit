"""wdt stream — mirror the Waydroid display via scrcpy.

Ported from canonical/anbox-streaming-sdk (Apache-2.0).
The Anbox Stream Gateway (proprietary WebRTC broker) is replaced with scrcpy,
which mirrors the Waydroid container display over ADB.

Sub-commands
------------
  wdt stream start   -- launch scrcpy mirror session
  wdt stream stop    -- terminate a running session
  wdt stream status  -- show whether a session is active
  wdt stream check   -- verify streaming dependencies are installed
"""

from __future__ import annotations

import os
import signal
from pathlib import Path

import click
from rich.console import Console

from waydroid_toolkit.modules.streaming.stream import (
    WAYDROID_BRIDGE_IP,
    StreamConfig,
    check_dependencies,
    load_pid,
    save_pid,
    start_stream,
)

console = Console()

_PID_FILE = Path.home() / ".local" / "share" / "waydroid-toolkit" / "stream.pid"


@click.group("stream")
def cmd() -> None:
    """Mirror the Waydroid display via scrcpy (local) or WebRTC (browser)."""


@cmd.command("start")
@click.option("--host", default="", help="ADB host (default: auto-detect waydroid0 bridge IP).")
@click.option("--port", default=5555, show_default=True, help="ADB port.")
@click.option("--bitrate", default="8M", show_default=True, help="Video bitrate (e.g. 4M, 8M).")
@click.option("--max-fps", default=60, show_default=True, help="Maximum frame rate.")
@click.option("--max-size", default=0, help="Cap video width in pixels (0 = no limit).")
@click.option("--codec", default="h264", type=click.Choice(["h264", "h265", "av1"]),
              show_default=True, help="Video codec (requires scrcpy >= 2.0).")
@click.option("--no-audio", is_flag=True, help="Disable audio forwarding.")
@click.option("--fullscreen", is_flag=True, help="Open scrcpy in fullscreen mode.")
@click.option("--record", default="", metavar="FILE", help="Record stream to FILE (.mp4).")
@click.option("--title", default="Waydroid", show_default=True, help="Window title.")
@click.option("--gamepad", is_flag=True, help="Enable gamepad forwarding (scrcpy >= 2.1).")
def stream_start(
    host: str,
    port: int,
    bitrate: str,
    max_fps: int,
    max_size: int,
    codec: str,
    no_audio: bool,
    fullscreen: bool,
    record: str,
    title: str,
    gamepad: bool,
) -> None:
    """Start mirroring the Waydroid display with scrcpy.

    Connects to the Waydroid container over ADB and opens a scrcpy window.
    The session runs in the background; use 'wdt stream stop' to terminate it.

    \b
    Examples:
      wdt stream start
      wdt stream start --bitrate 4M --max-fps 30
      wdt stream start --record waydroid-session.mp4
      wdt stream start --fullscreen --no-audio
    """
    # Check if already running
    if _PID_FILE.exists():
        pid = load_pid(_PID_FILE)
        if pid:
            try:
                os.kill(pid, 0)
                console.print(f"[yellow]Stream already running (PID {pid}).[/yellow]")
                console.print("Stop it first with: wdt stream stop")
                raise SystemExit(1)
            except ProcessLookupError:
                _PID_FILE.unlink(missing_ok=True)

    config = StreamConfig(
        adb_host=host or WAYDROID_BRIDGE_IP,
        adb_port=port,
        bitrate=bitrate,
        max_fps=max_fps,
        max_size=max_size,
        video_codec=codec,
        audio=not no_audio,
        fullscreen=fullscreen,
        record_file=record,
        window_title=title,
        gamepad=gamepad,
    )

    console.print("[bold]Starting Waydroid stream...[/bold]")
    console.print(f"  ADB target : {config.adb_host}:{config.adb_port}")
    console.print(f"  Bitrate    : {config.bitrate}")
    console.print(f"  Max FPS    : {config.max_fps}")
    console.print(f"  Codec      : {config.video_codec}")
    if config.record_file:
        console.print(f"  Recording  : {config.record_file}")

    try:
        session = start_stream(config)
    except FileNotFoundError as exc:
        console.print(f"[red]Missing dependency:[/red] {exc}")
        console.print("Install with: sudo apt install scrcpy adb")
        raise SystemExit(1) from exc
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1) from exc

    save_pid(session, _PID_FILE)
    console.print(f"[green]Stream started[/green] (PID {session.pid})")
    console.print("Stop with: wdt stream stop")


@cmd.command("stop")
def stream_stop() -> None:
    """Stop the running scrcpy stream session."""
    pid = load_pid(_PID_FILE)
    if not pid:
        console.print("[yellow]No stream session found.[/yellow]")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]Stream stopped[/green] (PID {pid})")
    except ProcessLookupError:
        console.print(f"[yellow]Process {pid} was not running.[/yellow]")

    _PID_FILE.unlink(missing_ok=True)


@cmd.command("status")
def stream_status() -> None:
    """Show whether a scrcpy stream session is active."""
    pid = load_pid(_PID_FILE)
    if not pid:
        console.print("[yellow]No stream session.[/yellow]")
        return

    try:
        os.kill(pid, 0)
        console.print(f"[green]Stream running[/green] (PID {pid})")
    except ProcessLookupError:
        console.print("[yellow]Stream session PID not found — may have exited.[/yellow]")
        _PID_FILE.unlink(missing_ok=True)


@cmd.command("check")
def stream_check() -> None:
    """Check that streaming dependencies (adb, scrcpy) are installed."""
    deps = check_dependencies()
    all_ok = True

    for tool, available in deps.items():
        if available:
            console.print(f"  [green]✓[/green] {tool}")
        else:
            console.print(f"  [red]✗[/red] {tool} — not found")
            all_ok = False

    if not all_ok:
        console.print()
        console.print("Install missing tools:")
        if not deps.get("adb"):
            console.print("  sudo apt install adb")
        if not deps.get("scrcpy"):
            console.print("  sudo apt install scrcpy")
        if not deps.get("ws-scrcpy"):
            console.print("  # ws-scrcpy (optional, for browser WebRTC):")
            console.print("  npm install -g ws-scrcpy")
        raise SystemExit(1)

    console.print()
    console.print("[green]All streaming dependencies available.[/green]")
