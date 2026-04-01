"""Waydroid installer module.

Handles detection of the host distro and installs Waydroid via the
appropriate package manager. Covers Debian/Ubuntu, Arch, Fedora, openSUSE.
After package installation it runs `waydroid init` with the chosen image type.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from enum import Enum

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.utils.distro import Distro


class ImageType(Enum):
    VANILLA = "VANILLA"
    GAPPS = "GAPPS"


class ImageArch(Enum):
    X86_64 = "x86_64"
    ARM64 = "arm64"


# Official Waydroid repo setup scripts per distro family
_REPO_SETUP: dict[Distro, list[str]] = {
    Distro.DEBIAN: [
        "curl -s https://repo.waydro.id | sudo bash",
    ],
    Distro.UBUNTU: [
        "curl -s https://repo.waydro.id | sudo bash",
    ],
    Distro.FEDORA: [
        "sudo dnf copr enable aleasto/waydroid -y",
    ],
    Distro.ARCH: [],  # waydroid is in AUR / community
    Distro.OPENSUSE: [],
}

_INSTALL_CMD: dict[Distro, list[str]] = {
    Distro.DEBIAN: ["sudo", "apt", "install", "-y", "waydroid"],
    Distro.UBUNTU: ["sudo", "apt", "install", "-y", "waydroid"],
    Distro.FEDORA: ["sudo", "dnf", "install", "-y", "waydroid"],
    Distro.ARCH: ["sudo", "pacman", "-S", "--noconfirm", "waydroid"],
    Distro.OPENSUSE: ["sudo", "zypper", "install", "-y", "waydroid"],
}


def is_waydroid_installed() -> bool:
    return shutil.which("waydroid") is not None


def setup_repo(distro: Distro, progress: Callable[[str], None] | None = None) -> None:
    """Add the Waydroid package repository for the given distro."""
    cmds = _REPO_SETUP.get(distro, [])
    for cmd in cmds:
        if progress:
            progress(f"Running: {cmd}")
        subprocess.run(cmd, shell=True, check=True)


def install_package(distro: Distro, progress: Callable[[str], None] | None = None) -> None:
    """Install the waydroid package via the distro package manager."""
    require_root("Installing Waydroid")
    cmd = _INSTALL_CMD.get(distro)
    if cmd is None:
        raise NotImplementedError(f"Automatic install not supported for {distro.value}")
    if progress:
        progress(f"Installing waydroid via {distro.value} package manager...")
    subprocess.run(cmd, check=True)


def init_waydroid(
    image_type: ImageType = ImageType.VANILLA,
    arch: ImageArch = ImageArch.X86_64,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Initialise Waydroid with the chosen image type and architecture."""
    require_root("Initialising Waydroid")
    cmd = [
        "sudo", "waydroid", "init",
        "-s", image_type.value,
        "-f",
    ]
    if progress:
        progress(f"Initialising Waydroid ({image_type.value}, {arch.value})...")
    subprocess.run(cmd, check=True)


def uninstall_waydroid(distro: Distro, progress: Callable[[str], None] | None = None) -> None:
    """Stop Waydroid, remove the package, and optionally purge data."""
    require_root("Uninstalling Waydroid")
    if progress:
        progress("Stopping Waydroid session...")
    subprocess.run(["sudo", "waydroid", "session", "stop"], capture_output=True)
    subprocess.run(["sudo", "systemctl", "stop", "waydroid-container"], capture_output=True)

    remove_cmds: dict[Distro, list[str]] = {
        Distro.DEBIAN: ["sudo", "apt", "remove", "-y", "waydroid"],
        Distro.UBUNTU: ["sudo", "apt", "remove", "-y", "waydroid"],
        Distro.FEDORA: ["sudo", "dnf", "remove", "-y", "waydroid"],
        Distro.ARCH: ["sudo", "pacman", "-R", "--noconfirm", "waydroid"],
        Distro.OPENSUSE: ["sudo", "zypper", "remove", "-y", "waydroid"],
    }
    cmd = remove_cmds.get(distro)
    if cmd:
        if progress:
            progress("Removing waydroid package...")
        subprocess.run(cmd, check=True)
