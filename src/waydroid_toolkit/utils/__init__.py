"""Shared utilities — distro detection, networking, overlay helpers."""

from .distro import Distro, detect_distro, get_package_manager
from .net import download, verify_sha256
from .overlay import install_file, is_overlay_enabled, overlay_path, remove_file

__all__ = [
    "Distro",
    "detect_distro",
    "get_package_manager",
    "download",
    "verify_sha256",
    "install_file",
    "is_overlay_enabled",
    "overlay_path",
    "remove_file",
]
