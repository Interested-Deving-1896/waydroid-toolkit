"""Android package manager for Waydroid.

Installs/removes APKs and manages F-Droid repos.
Mirrors waydroid/waydroid-package-manager (wpm) behaviour.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional
from urllib.request import urlopen

from waydroid_toolkit.core.adb import install_apk, list_packages, uninstall_package
from waydroid_toolkit.utils.net import download

_REPOS_DIR = Path.home() / ".local/share/waydroid-toolkit/repos"
_FDROID_INDEX = "index-v1.json"


def install_apk_file(
    apk: Path,
    progress: Optional[Callable[[str], None]] = None,
) -> None:
    """Install a local APK file via ADB."""
    if not apk.exists():
        raise FileNotFoundError(f"APK not found: {apk}")
    if progress:
        progress(f"Installing {apk.name}...")
    result = install_apk(apk)
    if result.returncode != 0:
        raise RuntimeError(f"APK install failed: {result.stderr}")
    if progress:
        progress(f"{apk.name} installed.")


def install_apk_url(
    url: str,
    progress: Optional[Callable[[str], None]] = None,
) -> None:
    """Download an APK from url and install it."""
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "app.apk"
        if progress:
            progress(f"Downloading {url}...")
        download(url, dest)
        install_apk_file(dest, progress)


def remove_package(
    package: str,
    progress: Optional[Callable[[str], None]] = None,
) -> None:
    if progress:
        progress(f"Removing {package}...")
    result = uninstall_package(package)
    if result.returncode != 0:
        raise RuntimeError(f"Uninstall failed: {result.stderr}")
    if progress:
        progress(f"{package} removed.")


def get_installed_packages() -> list[str]:
    return list_packages()


# ── F-Droid repo management ──────────────────────────────────────────────────

def _repo_path(name: str) -> Path:
    return _REPOS_DIR / name


def add_repo(name: str, url: str, progress: Optional[Callable[[str], None]] = None) -> None:
    """Add an F-Droid repo and download its index."""
    repo_dir = _repo_path(name)
    repo_dir.mkdir(parents=True, exist_ok=True)
    meta = {"name": name, "url": url}
    (repo_dir / "meta.json").write_text(json.dumps(meta))
    _refresh_repo(name, url, progress)


def remove_repo(name: str) -> None:
    import shutil
    path = _repo_path(name)
    if path.exists():
        shutil.rmtree(path)


def list_repos() -> list[dict]:
    repos = []
    if not _REPOS_DIR.exists():
        return repos
    for meta_file in _REPOS_DIR.glob("*/meta.json"):
        repos.append(json.loads(meta_file.read_text()))
    return repos


def _refresh_repo(name: str, url: str, progress: Optional[Callable[[str], None]] = None) -> None:
    index_url = url.rstrip("/") + "/" + _FDROID_INDEX
    dest = _repo_path(name) / _FDROID_INDEX
    if progress:
        progress(f"Fetching index for repo '{name}'...")
    download(index_url, dest)


def search_repos(query: str) -> list[dict]:
    """Search all repo indices for packages matching query (by package name or id)."""
    results = []
    query_lower = query.lower()
    for meta_file in _REPOS_DIR.glob("*/meta.json"):
        index_file = meta_file.parent / _FDROID_INDEX
        if not index_file.exists():
            continue
        try:
            index = json.loads(index_file.read_text())
            for app in index.get("apps", []):
                pkg_id = app.get("packageName", "")
                name = app.get("name", "")
                if query_lower in pkg_id.lower() or query_lower in name.lower():
                    results.append({"id": pkg_id, "name": name, "repo": meta_file.parent.name})
        except (json.JSONDecodeError, KeyError):
            continue
    return results
