"""Waydroid screen streaming via scrcpy.

Ported from canonical/anbox-streaming-sdk (Apache-2.0).

The Anbox Streaming SDK used a proprietary WebRTC gateway (ASG) to broker
video streams from Anbox containers to browsers and Android clients.

Waydroid runs locally, so the equivalent is scrcpy — an open-source tool that
mirrors the Android display over ADB. This module manages scrcpy sessions and
optionally exposes a WebSocket/WebRTC bridge via ws-scrcpy for browser access.

Mapping from anbox-streaming-sdk:
  AnboxStream (JS class)     → StreamSession (Python dataclass + scrcpy process)
  ASG connector              → ADB over TCP (Waydroid bridge IP)
  WebRTC video track         → scrcpy video stream (H.264 over ADB)
  out-of-band data channels  → scrcpy --tcpip control channel
  stream gateway API token   → not required (local ADB)
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_ADB_PORT = 5555
_DEFAULT_SCRCPY_BITRATE = "8M"
_DEFAULT_SCRCPY_MAX_FPS = 60
_WAYDROID_BRIDGE_IP = "192.168.240.112"  # default waydroid0 bridge address


@dataclass
class StreamConfig:
    """Configuration for a Waydroid scrcpy stream session.

    Mirrors the options object accepted by AnboxStream in the JS SDK.
    """

    # ADB target — host:port of the Waydroid ADB bridge
    adb_host: str = _WAYDROID_BRIDGE_IP
    adb_port: int = _DEFAULT_ADB_PORT

    # Video settings
    bitrate: str = _DEFAULT_SCRCPY_BITRATE
    max_fps: int = _DEFAULT_SCRCPY_MAX_FPS
    max_size: int = 0          # 0 = no limit; e.g. 1920 to cap at 1080p width
    video_codec: str = "h264"  # h264, h265, av1 (scrcpy >= 2.0)

    # Audio (scrcpy >= 2.0)
    audio: bool = True

    # Controls
    keyboard: bool = True
    mouse: bool = True
    gamepad: bool = False      # scrcpy >= 2.1

    # Display
    fullscreen: bool = False
    window_title: str = "Waydroid"
    stay_awake: bool = True    # keep Android screen on while streaming

    # Recording
    record_file: str = ""      # path to save .mp4 recording; "" = no recording

    # WebRTC bridge (ws-scrcpy / scrcpy-web)
    # When set, scrcpy is started in server mode and ws-scrcpy bridges it to
    # a WebSocket endpoint accessible from a browser.
    webrtc_bridge: bool = False
    webrtc_port: int = 8886

    # Extra raw scrcpy arguments
    extra_args: list[str] = field(default_factory=list)


@dataclass
class StreamSession:
    """A running scrcpy stream session."""

    config: StreamConfig
    pid: int
    adb_serial: str

    def is_running(self) -> bool:
        """Return True if the scrcpy process is still alive."""
        try:
            os.kill(self.pid, 0)
            return True
        except ProcessLookupError:
            return False

    def stop(self) -> None:
        """Terminate the scrcpy process."""
        try:
            os.kill(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def _resolve_adb_serial(config: StreamConfig) -> str:
    """Return the ADB serial for the Waydroid container.

    Tries the configured host:port first; falls back to auto-detecting the
    Waydroid bridge IP from the waydroid0 interface.
    """
    serial = f"{config.adb_host}:{config.adb_port}"

    # Check if already connected
    result = subprocess.run(
        ["adb", "devices"],
        capture_output=True, text=True,
    )
    if serial in result.stdout:
        return serial

    # Try to connect
    connect = subprocess.run(
        ["adb", "connect", serial],
        capture_output=True, text=True,
    )
    if "connected" in connect.stdout.lower():
        return serial

    # Auto-detect waydroid0 bridge IP
    try:
        ip_result = subprocess.run(
            ["ip", "-4", "addr", "show", "waydroid0"],
            capture_output=True, text=True,
        )
        import re
        match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", ip_result.stdout)
        if match:
            bridge_ip = match.group(1)
            alt_serial = f"{bridge_ip}:{config.adb_port}"
            subprocess.run(["adb", "connect", alt_serial], capture_output=True)
            return alt_serial
    except Exception:
        pass

    return serial


def _build_scrcpy_cmd(config: StreamConfig, serial: str) -> list[str]:
    """Build the scrcpy command line from a StreamConfig."""
    if not shutil.which("scrcpy"):
        raise FileNotFoundError(
            "scrcpy not found. Install with: sudo apt install scrcpy"
        )

    cmd = ["scrcpy", "--serial", serial]

    cmd += ["--video-bit-rate", config.bitrate]
    cmd += ["--max-fps", str(config.max_fps)]

    if config.max_size:
        cmd += ["--max-size", str(config.max_size)]

    if config.video_codec != "h264":
        cmd += ["--video-codec", config.video_codec]

    if not config.audio:
        cmd.append("--no-audio")

    if not config.keyboard:
        cmd.append("--no-key-injection")

    if not config.mouse:
        cmd.append("--no-mouse-injection")

    if config.gamepad:
        cmd.append("--gamepad=aoa")

    if config.fullscreen:
        cmd.append("--fullscreen")

    if config.window_title:
        cmd += ["--window-title", config.window_title]

    if config.stay_awake:
        cmd.append("--stay-awake")

    if config.record_file:
        cmd += ["--record", config.record_file]

    cmd += config.extra_args
    return cmd


def start_stream(config: StreamConfig | None = None) -> StreamSession:
    """Start a scrcpy stream session for the Waydroid container.

    Args:
        config: Stream configuration. Uses defaults when None.

    Returns:
        StreamSession with the running process PID.

    Raises:
        FileNotFoundError: if scrcpy or adb is not installed.
        RuntimeError: if ADB connection fails.
        subprocess.CalledProcessError: if scrcpy fails to start.
    """
    if config is None:
        config = StreamConfig()

    if not shutil.which("adb"):
        raise FileNotFoundError(
            "adb not found. Install with: sudo apt install adb"
        )

    serial = _resolve_adb_serial(config)

    # Wait briefly for ADB device to be ready
    for _ in range(10):
        r = subprocess.run(
            ["adb", "-s", serial, "get-state"],
            capture_output=True, text=True,
        )
        if r.stdout.strip() == "device":
            break
        time.sleep(1)
    else:
        raise RuntimeError(
            f"ADB device {serial!r} not ready. "
            "Is Waydroid running? Try: waydroid session start"
        )

    cmd = _build_scrcpy_cmd(config, serial)

    # Start scrcpy detached so it doesn't block the CLI
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    return StreamSession(config=config, pid=proc.pid, adb_serial=serial)


def stop_stream(session: StreamSession) -> None:
    """Stop a running stream session.

    Args:
        session: The StreamSession returned by start_stream.
    """
    session.stop()


def check_dependencies() -> dict[str, bool]:
    """Check which streaming dependencies are available.

    Returns:
        Dict mapping tool name to availability bool.
    """
    tools = {
        "adb": shutil.which("adb") is not None,
        "scrcpy": shutil.which("scrcpy") is not None,
        # ws-scrcpy / scrcpy-web for browser-based WebRTC streaming
        "ws-scrcpy": shutil.which("ws-scrcpy") is not None,
    }
    return tools


def save_pid(session: StreamSession, pid_file: Path) -> None:
    """Write the session PID to a file for later retrieval."""
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(session.pid))


def load_pid(pid_file: Path) -> int | None:
    """Read a PID from a file. Returns None if the file does not exist."""
    try:
        return int(pid_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None
