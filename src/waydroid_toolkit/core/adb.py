"""ADB interface for Waydroid.

Waydroid exposes an ADB endpoint at 192.168.250.1:5555 by default.
All ADB-dependent features (screenshot, screen record, file transfer,
app management) go through this module.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

_WAYDROID_ADB_HOST = "192.168.250.1"
_WAYDROID_ADB_PORT = 5555
_ADB_TARGET = f"{_WAYDROID_ADB_HOST}:{_WAYDROID_ADB_PORT}"


def _adb(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["adb", "-s", _ADB_TARGET, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def is_available() -> bool:
    """Return True if adb binary is on PATH."""
    try:
        subprocess.run(["adb", "version"], capture_output=True, timeout=3)
        return True
    except FileNotFoundError:
        return False


def connect(retries: int = 3, delay: float = 1.5) -> bool:
    """Connect to the Waydroid ADB endpoint. Returns True on success."""
    for _ in range(retries):
        result = subprocess.run(
            ["adb", "connect", _ADB_TARGET],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if "connected" in result.stdout.lower():
            return True
        time.sleep(delay)
    return False


def disconnect() -> None:
    subprocess.run(["adb", "disconnect", _ADB_TARGET], capture_output=True, timeout=5)


def is_connected() -> bool:
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
    return _ADB_TARGET in result.stdout


def shell(command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return _adb("shell", command, timeout=timeout)


def install_apk(apk_path: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return _adb("install", "-r", str(apk_path), timeout=timeout)


def uninstall_package(package: str) -> subprocess.CompletedProcess[str]:
    return _adb("uninstall", package)


def list_packages() -> list[str]:
    result = shell("pm list packages -3")
    packages = []
    for line in result.stdout.splitlines():
        if line.startswith("package:"):
            packages.append(line.removeprefix("package:").strip())
    return packages


def push(local: Path, remote: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return _adb("push", str(local), remote, timeout=timeout)


def pull(remote: str, local: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return _adb("pull", remote, str(local), timeout=timeout)


def screenshot(dest: Path | None = None) -> Path:
    """Capture a screenshot and save it to dest (default: ~/Pictures/Waydroid/)."""
    if dest is None:
        pictures = Path.home() / "Pictures" / "Waydroid"
        pictures.mkdir(parents=True, exist_ok=True)
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = pictures / f"screenshot_{ts}.png"
    _adb("exec-out", "screencap", "-p", timeout=10)
    subprocess.run(
        ["adb", "-s", _ADB_TARGET, "exec-out", "screencap", "-p"],
        stdout=open(dest, "wb"),
        timeout=10,
    )
    return dest


def logcat(tag: str | None = None, errors_only: bool = False) -> subprocess.Popen[str]:
    """Return a Popen handle streaming logcat output."""
    args = ["adb", "-s", _ADB_TARGET, "logcat"]
    if errors_only:
        args += ["*:E"]
    elif tag:
        args += [f"{tag}:V", "*:S"]
    return subprocess.Popen(args, stdout=subprocess.PIPE, text=True)
