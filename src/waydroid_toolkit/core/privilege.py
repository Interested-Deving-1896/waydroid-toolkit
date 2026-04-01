"""Privilege and sudo helpers.

Operations that modify /var/lib/waydroid or system images require root.
This module provides a consistent way to check and request elevation.
"""

from __future__ import annotations

import os
import subprocess


def is_root() -> bool:
    return os.geteuid() == 0


def sudo_run(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    """Run a command with sudo, raising PermissionError if sudo is unavailable."""
    try:
        return subprocess.run(
            ["sudo", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise PermissionError("sudo is not available on this system") from exc


def require_root(operation: str = "this operation") -> None:
    """Raise PermissionError if not running as root and sudo is unavailable."""
    if is_root():
        return
    result = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=5)
    if result.returncode != 0:
        raise PermissionError(
            f"{operation} requires root privileges. Run with sudo or as root."
        )
