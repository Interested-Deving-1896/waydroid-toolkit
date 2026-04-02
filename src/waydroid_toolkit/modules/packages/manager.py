"""Android package manager for Waydroid.

Installs/removes APKs and manages F-Droid repos.
Mirrors waydroid/waydroid-package-manager (wpm) behaviour.

F-Droid index format
--------------------
Modern repos (F-Droid >= 1.14) publish index-v2.json. Older repos and
mirrors still publish index-v1.json. This module tries v2 first and falls
back to v1. Both are normalised into the same internal dict shape:
    {"packageName": str, "name": str}
so search_repos() works identically regardless of which format was fetched.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from pathlib import Path

from waydroid_toolkit.core.adb import install_apk, list_packages, uninstall_package
from waydroid_toolkit.utils.net import download

_REPOS_DIR = Path.home() / ".local/share/waydroid-toolkit/repos"
_INDEX_V2 = "index-v2.json"
_INDEX_V1 = "index-v1.json"


# ── APK install / remove ──────────────────────────────────────────────────────

def install_apk_file(
    apk: Path,
    progress: Callable[[str], None] | None = None,
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
    progress: Callable[[str], None] | None = None,
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
    progress: Callable[[str], None] | None = None,
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


# ── F-Droid repo management ───────────────────────────────────────────────────

def _repo_path(name: str) -> Path:
    return _REPOS_DIR / name


def add_repo(
    name: str,
    url: str,
    progress: Callable[[str], None] | None = None,
) -> None:
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


def refresh_all_repos(progress: Callable[[str], None] | None = None) -> None:
    """Re-download the index for every configured repo."""
    for repo in list_repos():
        _refresh_repo(repo["name"], repo["url"], progress)


def _refresh_repo(
    name: str,
    url: str,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Download the F-Droid index for a repo, trying v2 then v1.

    Validates the downloaded JSON before accepting it so a partial download
    or HTML error page is not silently stored as the index.
    """
    repo_dir = _repo_path(name)
    base_url = url.rstrip("/")

    if progress:
        progress(f"Fetching index for '{name}'...")

    for index_name in (_INDEX_V2, _INDEX_V1):
        index_url = f"{base_url}/{index_name}"
        dest = repo_dir / index_name
        try:
            download(index_url, dest)
            _validate_index(dest, index_name)
            # Record which format was successfully fetched
            meta_path = repo_dir / "meta.json"
            meta = json.loads(meta_path.read_text())
            meta["index_format"] = index_name
            meta_path.write_text(json.dumps(meta))
            if progress:
                progress(f"Index for '{name}' updated ({index_name}).")
            return
        except (ConnectionError, ValueError, json.JSONDecodeError):
            if dest.exists():
                dest.unlink()
            continue

    raise RuntimeError(
        f"Could not fetch index for repo '{name}' from {base_url}. "
        "Check the URL and your network connection."
    )


def _validate_index(path: Path, index_name: str) -> None:
    """Raise ValueError if the file is not a recognisable F-Droid index."""
    data = json.loads(path.read_text())
    if index_name == _INDEX_V2:
        if "repo" not in data and "packages" not in data:
            raise ValueError(f"Unexpected index-v2 structure in {path}")
    else:
        if "apps" not in data and "repo" not in data:
            raise ValueError(f"Unexpected index-v1 structure in {path}")


def _normalise_apps(index_data: dict, index_name: str) -> list[dict]:
    """Return a flat list of {packageName, name} dicts from either index format."""
    if index_name == _INDEX_V2:
        apps = []
        for pkg_id, pkg_data in index_data.get("packages", {}).items():
            metadata = pkg_data.get("metadata", {})
            name = metadata.get("name", pkg_id)
            if isinstance(name, dict):
                name = next(iter(name.values()), pkg_id)
            apps.append({"packageName": pkg_id, "name": name})
        return apps
    return index_data.get("apps", [])


def search_repos(query: str) -> list[dict]:
    """Search all repo indices for packages matching query (name or package id)."""
    results = []
    query_lower = query.lower()
    for meta_file in _REPOS_DIR.glob("*/meta.json"):
        meta = json.loads(meta_file.read_text())
        index_name = meta.get("index_format", _INDEX_V1)
        index_file = meta_file.parent / index_name
        if not index_file.exists():
            for candidate in (_INDEX_V2, _INDEX_V1):
                candidate_path = meta_file.parent / candidate
                if candidate_path.exists():
                    index_file = candidate_path
                    index_name = candidate
                    break
            else:
                continue
        try:
            index = json.loads(index_file.read_text())
            apps = _normalise_apps(index, index_name)
            for app in apps:
                pkg_id = app.get("packageName", "")
                name = app.get("name", "")
                if query_lower in pkg_id.lower() or query_lower in name.lower():
                    results.append({
                        "id": pkg_id,
                        "name": name,
                        "repo": meta_file.parent.name,
                    })
        except (json.JSONDecodeError, KeyError):
            continue
    return results
