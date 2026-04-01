"""Shared utilities — distro detection, networking, overlay helpers."""

from .distro import Distro, detect_distro, get_package_manager
from .github_releases import download_latest_apk as gh_download_apk
from .github_releases import latest_apk_url as gh_latest_apk_url
from .gitlab_releases import download_latest_apk as gl_download_apk
from .gitlab_releases import latest_apk_url as gl_latest_apk_url
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
    "gh_download_apk",
    "gh_latest_apk_url",
    "gl_download_apk",
    "gl_latest_apk_url",
]
