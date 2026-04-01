"""Android package management — APK install/remove, F-Droid repo management."""

from .manager import (
    add_repo,
    get_installed_packages,
    install_apk_file,
    install_apk_url,
    list_repos,
    remove_package,
    remove_repo,
    search_repos,
)

__all__ = [
    "add_repo", "get_installed_packages", "install_apk_file",
    "install_apk_url", "list_repos", "remove_package", "remove_repo", "search_repos",
]
