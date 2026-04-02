"""Key mapper extension — gamepad and keyboard-to-touch input bridge.

Installs ``waydroid-input-bridge`` (a Python daemon + Android APK pair)
that translates gamepad buttons and keyboard shortcuts into Android touch
events, enabling controller support for games.

Sources
-------
Daemon + APK: https://github.com/waydroid/waydroid-input-bridge

Installation steps
------------------
1. Download the APK from GitHub releases.
2. Install it into Waydroid via ``adb install``.
3. Install the Python daemon package via pip (user-level).
4. Write a systemd user unit so the daemon starts with the session.

The daemon communicates with the APK over a local socket. No root is
required for the daemon itself; ``adb install`` requires a running
Waydroid session.
"""

from __future__ import annotations

import subprocess
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

from waydroid_toolkit.core import adb

from .base import Extension, ExtensionMeta

# ── Constants ─────────────────────────────────────────────────────────────────

_APK_URL = (
    "https://github.com/waydroid/waydroid-input-bridge/releases/latest/download/"
    "waydroid-input-bridge.apk"
)
_DAEMON_PKG = "waydroid-input-bridge"
_APK_PACKAGE = "id.waydroid.inputbridge"
_SYSTEMD_UNIT_NAME = "waydroid-input-bridge.service"
_SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
_CACHE_DIR = Path("/tmp/waydroid-toolkit")

_SYSTEMD_UNIT = """\
[Unit]
Description=Waydroid Input Bridge daemon
After=graphical-session.target

[Service]
ExecStart=waydroid-input-bridge
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pip_install(package: str) -> None:
    subprocess.run(
        ["pip", "install", "--user", "--quiet", package],
        check=True,
    )


def _pip_uninstall(package: str) -> None:
    subprocess.run(
        ["pip", "uninstall", "--yes", package],
        check=True,
    )


def _daemon_on_path() -> bool:
    import shutil
    return shutil.which("waydroid-input-bridge") is not None


def _apk_installed() -> bool:
    """Return True if the APK is installed in the running Waydroid session."""
    try:
        result = subprocess.run(
            ["adb", "-s", "192.168.250.1:5555", "shell",
             "pm", "list", "packages", _APK_PACKAGE],
            capture_output=True, text=True, timeout=10,
        )
        return _APK_PACKAGE in result.stdout
    except Exception:  # noqa: BLE001
        return False


def _write_systemd_unit() -> None:
    _SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    unit_path = _SYSTEMD_USER_DIR / _SYSTEMD_UNIT_NAME
    unit_path.write_text(_SYSTEMD_UNIT)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(
        ["systemctl", "--user", "enable", _SYSTEMD_UNIT_NAME], check=False
    )


def _remove_systemd_unit() -> None:
    unit_path = _SYSTEMD_USER_DIR / _SYSTEMD_UNIT_NAME
    subprocess.run(
        ["systemctl", "--user", "disable", "--now", _SYSTEMD_UNIT_NAME],
        check=False,
    )
    unit_path.unlink(missing_ok=True)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)


# ── Extension class ───────────────────────────────────────────────────────────

class KeyMapperExtension(Extension):
    """Installs the Waydroid input bridge for gamepad/keyboard support.

    Requires a running Waydroid session for APK installation.
    The daemon is installed as a systemd user service.
    """

    @property
    def meta(self) -> ExtensionMeta:
        return ExtensionMeta(
            id="keymapper",
            name="Key Mapper (waydroid-input-bridge)",
            description=(
                "Translates gamepad buttons and keyboard shortcuts into "
                "Android touch events. Requires a running Waydroid session."
            ),
            requires_root=False,
        )

    def is_installed(self) -> bool:
        return _daemon_on_path() and _apk_installed()

    def install(self, progress: Callable[[str], None] | None = None) -> None:
        # Step 1: install Python daemon
        if progress:
            progress("Installing waydroid-input-bridge daemon via pip…")
        _pip_install(_DAEMON_PKG)

        # Step 2: download and install APK
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        apk_path = _CACHE_DIR / "waydroid-input-bridge.apk"

        if progress:
            progress("Downloading waydroid-input-bridge APK…")
        req = urllib.request.Request(
            _APK_URL, headers={"User-Agent": "waydroid-toolkit/1.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp, \
                apk_path.open("wb") as fh:
            fh.write(resp.read())

        if progress:
            progress("Installing APK into Waydroid (requires running session)…")
        try:
            subprocess.run(
                ["adb", "connect", "192.168.250.1:5555"],
                capture_output=True, timeout=8, check=False,
            )
            subprocess.run(
                ["adb", "-s", "192.168.250.1:5555", "install", "-r", str(apk_path)],
                check=True, timeout=60,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                "APK installation failed. Make sure Waydroid is running and "
                "adb is available on PATH."
            ) from exc
        except FileNotFoundError as exc:
            raise RuntimeError(
                "adb not found. Install android-tools-adb and try again."
            ) from exc

        # Step 3: write systemd user unit
        if progress:
            progress("Writing systemd user unit…")
        _write_systemd_unit()

        if progress:
            progress(
                "Key mapper installed. Start the daemon with:\n"
                "  systemctl --user start waydroid-input-bridge"
            )

    def uninstall(self, progress: Callable[[str], None] | None = None) -> None:
        # Remove systemd unit
        if progress:
            progress("Removing systemd unit…")
        _remove_systemd_unit()

        # Uninstall APK from Waydroid
        if progress:
            progress("Uninstalling APK from Waydroid…")
        try:
            subprocess.run(
                ["adb", "-s", "192.168.250.1:5555", "uninstall", _APK_PACKAGE],
                check=False, timeout=30,
            )
        except Exception:  # noqa: BLE001
            pass  # Waydroid may not be running; APK removal is best-effort

        # Uninstall daemon
        if progress:
            progress("Uninstalling daemon via pip…")
        try:
            _pip_uninstall(_DAEMON_PKG)
        except subprocess.CalledProcessError:
            pass  # already removed

        if progress:
            progress("Key mapper removed.")
