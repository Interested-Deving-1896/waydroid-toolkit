"""Maintenance tools — debloat, display settings, device info, logcat, file transfer.

Consolidates functionality from:
  - waydroid/waydroid-linux_tools  (debloater)
  - Nigel1992/Waydroid-Advanced-Manager (display, device info, logcat, file transfer)
  - core/adb  (underlying ADB calls)
"""

from __future__ import annotations

import datetime
import subprocess
from pathlib import Path
from typing import Callable, Iterator, Optional

from waydroid_toolkit.core import adb
from waydroid_toolkit.core.waydroid import run_waydroid


# ── Display settings ─────────────────────────────────────────────────────────

def set_resolution(width: int, height: int) -> None:
    run_waydroid("prop", "set", "persist.waydroid.width", str(width), sudo=True)
    run_waydroid("prop", "set", "persist.waydroid.height", str(height), sudo=True)


def set_density(dpi: int) -> None:
    run_waydroid("prop", "set", "persist.waydroid.density", str(dpi), sudo=True)


def reset_display() -> None:
    for prop in ("persist.waydroid.width", "persist.waydroid.height", "persist.waydroid.density"):
        run_waydroid("prop", "set", prop, "", sudo=True)


# ── Device info ───────────────────────────────────────────────────────────────

def get_device_info() -> dict[str, str]:
    """Return a dict of Android device properties via ADB shell."""
    props = {
        "android_version": "getprop ro.build.version.release",
        "sdk_version": "getprop ro.build.version.sdk",
        "product_model": "getprop ro.product.model",
        "cpu_abi": "getprop ro.product.cpu.abi",
        "display": "wm size",
        "density": "wm density",
    }
    info: dict[str, str] = {}
    for key, cmd in props.items():
        result = adb.shell(cmd)
        info[key] = result.stdout.strip() if result.returncode == 0 else "unavailable"
    return info


# ── Screenshot / screen record ────────────────────────────────────────────────

def take_screenshot(dest: Optional[Path] = None) -> Path:
    return adb.screenshot(dest)


def record_screen(
    dest: Optional[Path] = None,
    duration_seconds: int = 60,
) -> Path:
    if dest is None:
        videos = Path.home() / "Videos" / "Waydroid"
        videos.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = videos / f"recording_{ts}.mp4"
    adb.shell(f"screenrecord --time-limit {duration_seconds} /sdcard/wdt_record.mp4")
    adb.pull("/sdcard/wdt_record.mp4", dest)
    adb.shell("rm /sdcard/wdt_record.mp4")
    return dest


# ── File transfer ─────────────────────────────────────────────────────────────

def push_file(local: Path, android_dest: str) -> None:
    result = adb.push(local, android_dest)
    if result.returncode != 0:
        raise RuntimeError(f"Push failed: {result.stderr}")


def pull_file(android_src: str, local: Path) -> None:
    result = adb.pull(android_src, local)
    if result.returncode != 0:
        raise RuntimeError(f"Pull failed: {result.stderr}")


# ── Logcat ────────────────────────────────────────────────────────────────────

def stream_logcat(
    tag: Optional[str] = None,
    errors_only: bool = False,
) -> Iterator[str]:
    """Yield logcat lines as a generator. Caller is responsible for stopping."""
    proc = adb.logcat(tag=tag, errors_only=errors_only)
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            yield line.rstrip()
    finally:
        proc.terminate()


# ── App management ────────────────────────────────────────────────────────────

def freeze_app(package: str) -> None:
    """Disable (freeze) an app without uninstalling it."""
    result = adb.shell(f"pm disable-user --user 0 {package}")
    if result.returncode != 0:
        raise RuntimeError(f"Failed to freeze {package}: {result.stderr}")


def unfreeze_app(package: str) -> None:
    result = adb.shell(f"pm enable {package}")
    if result.returncode != 0:
        raise RuntimeError(f"Failed to unfreeze {package}: {result.stderr}")


def clear_app_data(package: str, cache_only: bool = False) -> None:
    cmd = f"pm clear {package}" if not cache_only else f"pm trim-caches 999999999 {package}"
    adb.shell(cmd)


def launch_app(package: str) -> None:
    adb.shell(
        f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
    )


# ── Debloater ─────────────────────────────────────────────────────────────────

# Common LineageOS bloatware package names
DEFAULT_BLOAT = [
    "org.lineageos.jelly",
    "org.lineageos.recorder",
    "org.lineageos.eleven",
    "com.android.email",
    "com.android.calendar",
]


def debloat(
    packages: Optional[list[str]] = None,
    progress: Optional[Callable[[str], None]] = None,
) -> list[str]:
    """Uninstall bloatware packages. Returns list of successfully removed packages."""
    targets = packages or DEFAULT_BLOAT
    removed = []
    for pkg in targets:
        result = adb.shell(f"pm uninstall -k --user 0 {pkg}")
        if result.returncode == 0:
            removed.append(pkg)
            if progress:
                progress(f"Removed: {pkg}")
    return removed
