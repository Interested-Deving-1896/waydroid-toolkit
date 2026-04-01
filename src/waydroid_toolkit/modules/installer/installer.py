"""Waydroid installer module.

Handles detection of the host distro and installs Waydroid via the
appropriate package manager. Covers Debian/Ubuntu, Arch, Fedora, openSUSE,
NixOS, Void, Alpine, and Gentoo.
After package installation it runs `waydroid init` with the chosen image type.

Custom image installation
-------------------------
`waydroid init` does not accept image paths as CLI flags. Instead it checks
two pre-defined directories for a pre-installed system.img + vendor.img:

  /etc/waydroid-extra/images   (system-wide, requires root)
  /usr/share/waydroid-extra/images

When `system_img` and `vendor_img` are supplied to `init_waydroid()`, the
images are staged into `/etc/waydroid-extra/images/` via hard-links (same
filesystem) or copies (cross-filesystem) before `waydroid init` runs.
Waydroid detects them automatically and skips the OTA download.
The staged copies are removed after init completes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.utils.distro import Distro

# Waydroid's pre-installed images directory (checked before OTA download)
_PREINSTALLED_IMAGES_DIR = Path("/etc/waydroid-extra/images")


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


def _stage_images(
    system_img: Path,
    vendor_img: Path,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Copy or hard-link system.img and vendor.img into the waydroid-extra dir.

    waydroid init checks /etc/waydroid-extra/images/ for pre-installed images
    before attempting an OTA download. Staging the manifest images there lets
    waydroid init use them directly.

    Hard-links are used when source and destination are on the same filesystem
    (instant, no extra disk space). Falls back to a full copy otherwise.
    """
    dest = _PREINSTALLED_IMAGES_DIR
    subprocess.run(["sudo", "mkdir", "-p", str(dest)], check=True)

    for src, name in [(system_img, "system.img"), (vendor_img, "vendor.img")]:
        dst = dest / name
        if progress:
            progress(f"Staging {name} → {dst}")
        # Remove any existing file first (sudo required — dest is root-owned)
        subprocess.run(["sudo", "rm", "-f", str(dst)], check=True)
        try:
            # Try hard-link first (same filesystem, zero copy cost)
            os.link(src, dst)
        except OSError:
            # Cross-filesystem or permission error — fall back to sudo cp
            subprocess.run(["sudo", "cp", "--reflink=auto", str(src), str(dst)], check=True)


def _unstage_images(progress: Callable[[str], None] | None = None) -> None:
    """Remove staged images from the waydroid-extra directory after init."""
    dest = _PREINSTALLED_IMAGES_DIR
    for name in ("system.img", "vendor.img"):
        path = dest / name
        subprocess.run(["sudo", "rm", "-f", str(path)], capture_output=True)
    # Remove the directory only if it is now empty
    subprocess.run(
        ["sudo", "rmdir", "--ignore-fail-on-non-empty", str(dest)],
        capture_output=True,
    )
    if progress:
        progress("Cleaned up staged images.")


def init_waydroid(
    image_type: ImageType = ImageType.VANILLA,
    arch: ImageArch = ImageArch.X86_64,
    install_apps: bool = True,
    system_img: Path | None = None,
    vendor_img: Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Initialise Waydroid with the chosen image type and architecture.

    Custom images
    -------------
    When system_img and vendor_img are both provided, they are staged into
    /etc/waydroid-extra/images/ before `waydroid init` runs. Waydroid detects
    them automatically and skips the OTA download. The staged files are removed
    after init completes regardless of success or failure.

    Both paths must be provided together — supplying only one raises ValueError.

    Bundled apps
    ------------
    When install_apps is True (default), F-Droid, AuroraStore, AuroraDroid,
    AuroraServices, and selected GitHub-Releases apps are installed into the
    image after init completes. Pass install_apps=False to skip this step.
    """
    if (system_img is None) != (vendor_img is None):
        raise ValueError(
            "system_img and vendor_img must both be provided or both omitted."
        )

    require_root("Initialising Waydroid")

    staged = False
    try:
        if system_img is not None and vendor_img is not None:
            _stage_images(system_img, vendor_img, progress)
            staged = True

        cmd = ["sudo", "waydroid", "init", "-s", image_type.value, "-f"]
        if progress:
            mode = "custom images" if staged else f"{image_type.value}, {arch.value}"
            progress(f"Initialising Waydroid ({mode})...")
        subprocess.run(cmd, check=True)

    finally:
        if staged:
            _unstage_images(progress)

    if install_apps:
        from waydroid_toolkit.modules.installer.bundled_apps import install_bundled_apps
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
