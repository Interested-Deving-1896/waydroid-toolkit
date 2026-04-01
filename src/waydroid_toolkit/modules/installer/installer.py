"""Waydroid installer module.

Handles detection of the host distro and installs Waydroid via the
appropriate package manager. Covers Debian/Ubuntu, Arch, Fedora, openSUSE,
NixOS, Void, Alpine, and Gentoo.
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
    Distro.ARCH: [],      # waydroid is in AUR / community
    Distro.OPENSUSE: [],  # waydroid is in OBS
    Distro.NIXOS: [],     # managed via nixpkgs / NixOS module
    Distro.VOID: [],      # waydroid is in void-packages
    Distro.ALPINE: [],    # waydroid is in Alpine community
    Distro.GENTOO: [],    # waydroid is in ::guru overlay
}

_INSTALL_CMD: dict[Distro, list[str]] = {
    Distro.DEBIAN:  ["sudo", "apt", "install", "-y", "waydroid"],
    Distro.UBUNTU:  ["sudo", "apt", "install", "-y", "waydroid"],
    Distro.FEDORA:  ["sudo", "dnf", "install", "-y", "waydroid"],
    Distro.ARCH:    ["sudo", "pacman", "-S", "--noconfirm", "waydroid"],
    Distro.OPENSUSE: ["sudo", "zypper", "install", "-y", "waydroid"],
    Distro.VOID:    ["sudo", "xbps-install", "-y", "waydroid"],
    Distro.ALPINE:  ["sudo", "apk", "add", "waydroid"],
    Distro.GENTOO:  ["sudo", "emerge", "--ask=n", "app-containers/waydroid"],
    # NixOS: declarative only — no imperative install command
}


def is_waydroid_installed() -> bool:
    return shutil.which("waydroid") is not None


def is_repo_configured(distro: Distro) -> bool:
    """Return True if the Waydroid repo is already configured on this system.

    Avoids re-running the repo setup script on subsequent installs.
    """
    if distro in (Distro.DEBIAN, Distro.UBUNTU):
        # The waydro.id script drops a .list file in /etc/apt/sources.list.d/
        import glob
        return bool(glob.glob("/etc/apt/sources.list.d/waydroid*.list"))
    if distro == Distro.FEDORA:
        result = subprocess.run(
            ["dnf", "copr", "list", "--enabled"],
            capture_output=True, text=True,
        )
        return "waydroid" in result.stdout.lower()
    # Other distros don't need a separate repo setup step
    return True


def setup_repo(distro: Distro, progress: Callable[[str], None] | None = None) -> None:
    """Add the Waydroid package repository for the given distro.

    Skips silently if the repo is already configured.
    """
    if is_repo_configured(distro):
        if progress:
            progress("Repository already configured, skipping.")
        return
    cmds = _REPO_SETUP.get(distro, [])
    for cmd in cmds:
        if progress:
            progress(f"Running: {cmd}")
        subprocess.run(cmd, shell=True, check=True)


def install_package(distro: Distro, progress: Callable[[str], None] | None = None) -> None:
    """Install the waydroid package via the distro package manager."""
    require_root("Installing Waydroid")
    if distro == Distro.NIXOS:
        raise NotImplementedError(
            "NixOS uses declarative configuration. Add 'virtualisation.waydroid.enable = true;'"
            " to your configuration.nix and run 'nixos-rebuild switch'."
        )
    cmd = _INSTALL_CMD.get(distro)
    if cmd is None:
        raise NotImplementedError(f"Automatic install not supported for {distro.value}")
    if progress:
        progress(f"Installing waydroid via {distro.value} package manager...")
    subprocess.run(cmd, check=True)


def init_waydroid(
    image_type: ImageType = ImageType.VANILLA,
    arch: ImageArch = ImageArch.X86_64,
    install_apps: bool = True,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Initialise Waydroid with the chosen image type and architecture.

    When install_apps is True (default), bundled apps (F-Droid, AuroraStore,
    AuroraDroid, AuroraServices, and GitHub-Releases apps) are installed into
    the image after init completes. Pass install_apps=False to skip this step.
    """
    require_root("Initialising Waydroid")
    cmd = [
        "sudo", "waydroid", "init",
        "-s", image_type.value,
        "-f",
    ]
    if progress:
        progress(f"Initialising Waydroid ({image_type.value}, {arch.value})...")
    subprocess.run(cmd, check=True)

    if install_apps:
        # Lazy import — bundled_apps pulls in ADB/network deps not needed
        # for the plain install path.
        from waydroid_toolkit.modules.installer.bundled_apps import (
            install_bundled_apps,
        )
        if progress:
            progress("Installing bundled apps...")
        results = install_bundled_apps(progress)
        failed = [r for r in results if not r.success and not r.skipped]
        if failed and progress:
            names = ", ".join(r.name for r in failed)
            progress(f"Warning: some apps failed to install: {names}")


def uninstall_waydroid(distro: Distro, progress: Callable[[str], None] | None = None) -> None:
    """Stop Waydroid, remove the package, and optionally purge data."""
    require_root("Uninstalling Waydroid")
    if progress:
        progress("Stopping Waydroid session...")
    subprocess.run(["sudo", "waydroid", "session", "stop"], capture_output=True)
    subprocess.run(["sudo", "systemctl", "stop", "waydroid-container"], capture_output=True)

    remove_cmds: dict[Distro, list[str]] = {
        Distro.DEBIAN:   ["sudo", "apt", "remove", "-y", "waydroid"],
        Distro.UBUNTU:   ["sudo", "apt", "remove", "-y", "waydroid"],
        Distro.FEDORA:   ["sudo", "dnf", "remove", "-y", "waydroid"],
        Distro.ARCH:     ["sudo", "pacman", "-R", "--noconfirm", "waydroid"],
        Distro.OPENSUSE: ["sudo", "zypper", "remove", "-y", "waydroid"],
        Distro.VOID:     ["sudo", "xbps-remove", "-y", "waydroid"],
        Distro.ALPINE:   ["sudo", "apk", "del", "waydroid"],
        Distro.GENTOO:   ["sudo", "emerge", "--ask=n", "--unmerge", "app-containers/waydroid"],
    }
    cmd = remove_cmds.get(distro)
    if cmd:
        if progress:
            progress("Removing waydroid package...")
        subprocess.run(cmd, check=True)
