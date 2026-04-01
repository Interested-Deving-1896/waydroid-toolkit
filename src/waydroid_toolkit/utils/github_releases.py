"""GitHub Releases APK fetcher.

Queries the GitHub REST API for the latest release of a repo and returns
the download URL of the first .apk asset found. Authentication uses the
GH_TOKEN or GITHUB_TOKEN environment variable when present; falls back to
unauthenticated requests (60 req/hour limit).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen  # noqa: S310

_API_BASE = "https://api.github.com"
_TIMEOUT = 15


def _auth_headers() -> dict[str, str]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "waydroid-toolkit/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def latest_apk_url(owner: str, repo: str) -> str | None:
    """Return the download URL of the latest .apk release asset, or None.

    Returns None (rather than raising) when the repo has no releases or no
    .apk asset, so callers can silently skip unavailable sources.
    """
    url = f"{_API_BASE}/repos/{owner}/{repo}/releases/latest"
    req = Request(url, headers=_auth_headers())
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise ConnectionError(f"GitHub API error for {owner}/{repo}: {exc}") from exc
    except URLError as exc:
        raise ConnectionError(f"Network error fetching {owner}/{repo}: {exc}") from exc

    for asset in data.get("assets", []):
        if asset.get("name", "").endswith(".apk"):
            return asset["browser_download_url"]
    return None


def download_latest_apk(owner: str, repo: str, dest_dir: Path) -> Path | None:
    """Download the latest .apk from a GitHub repo into dest_dir.

    Returns the local Path on success, None if no APK asset exists.
    """
    url = latest_apk_url(owner, repo)
    if url is None:
        return None

    filename = url.rsplit("/", 1)[-1]
    dest = dest_dir / filename
    if dest.exists():
        return dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers=_auth_headers())
    try:
        with urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
    except URLError as exc:
        raise ConnectionError(f"Failed to download {url}: {exc}") from exc
    return dest
