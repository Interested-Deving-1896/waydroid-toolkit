"""Host Linux distribution detection."""

from __future__ import annotations

import shutil
from enum import Enum
from pathlib import Path


class Distro(Enum):
    DEBIAN = "debian"
    UBUNTU = "ubuntu"
    FEDORA = "fedora"
    ARCH = "arch"
    OPENSUSE = "opensuse"
    UNKNOWN = "unknown"


def detect_distro() -> Distro:
    """Detect the host distro by reading /etc/os-release."""
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return Distro.UNKNOWN

    data: dict[str, str] = {}
    for line in os_release.read_text().splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            data[k.strip()] = v.strip().strip('"')

    id_like = data.get("ID_LIKE", "").lower()
    distro_id = data.get("ID", "").lower()

    for val in (distro_id, id_like):
        if "ubuntu" in val:
            return Distro.UBUNTU
        if "debian" in val:
            return Distro.DEBIAN
        if "fedora" in val or "rhel" in val:
            return Distro.FEDORA
        if "arch" in val:
            return Distro.ARCH
        if "suse" in val or "opensuse" in val:
            return Distro.OPENSUSE

    return Distro.UNKNOWN


def get_package_manager() -> str | None:
    """Return the name of the available package manager binary."""
    for pm in ("apt", "dnf", "pacman", "zypper", "yum"):
        if shutil.which(pm):
            return pm
    return None
