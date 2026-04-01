"""GitLab Releases APK fetcher.

Queries the GitLab REST API for the latest release of a project and extracts
APK download URLs from the release description (GitLab upload links). This is
necessary for projects like AuroraStore that attach APKs as description links
rather than formal release assets.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

_API_BASE = "https://gitlab.com/api/v4"
_TIMEOUT = 15
_APK_LINK_RE = re.compile(r"\[([^\]]+\.apk)\]\((/uploads/[^)]+\.apk)\)")


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": "waydroid-toolkit/0.1",
    }


def latest_apk_url(namespace: str, project: str, variant: str | None = None) -> str | None:
    """Return the download URL of the latest APK from a GitLab release.

    APKs are extracted from upload links embedded in the release description.
    When multiple APKs exist (e.g. AuroraStore ships standard, -hw, -preload
    variants), the first match is returned unless variant is specified.

    variant: substring to match against the APK filename (e.g. None for the
             first/standard APK, "hw" to prefer the hardware-accelerated build).

    Returns None when the project has no releases or no APK links.
    """
    proj_path = quote(f"{namespace}/{project}", safe="")
    url = f"{_API_BASE}/projects/{proj_path}/releases?per_page=1"
    req = Request(url, headers=_headers())
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:
            releases = json.loads(resp.read())
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise ConnectionError(f"GitLab API error for {namespace}/{project}: {exc}") from exc
    except URLError as exc:
        raise ConnectionError(f"Network error fetching {namespace}/{project}: {exc}") from exc

    if not releases:
        return None

    desc = releases[0].get("description", "")
    base = f"https://gitlab.com/{namespace}/{project}"
    matches = _APK_LINK_RE.findall(desc)

    if not matches:
        return None

    if variant:
        for name, path in matches:
            if variant.lower() in name.lower():
                return f"{base}{path}"

    # Default: return the first APK that is NOT a special variant
    # (avoid -hw, -preload, -debug unless that's all there is)
    _VARIANT_SUFFIXES = ("-hw", "-preload", "-debug", "-unsigned")
    for name, path in matches:
        if not any(s in name.lower() for s in _VARIANT_SUFFIXES):
            return f"{base}{path}"

    # All are variants — return the first one
    return f"{base}{matches[0][1]}"


def download_latest_apk(
    namespace: str,
    project: str,
    dest_dir: Path,
    variant: str | None = None,
) -> Path | None:
    """Download the latest APK from a GitLab project into dest_dir.

    Returns the local Path on success, None if no APK is available.
    """
    url = latest_apk_url(namespace, project, variant)
    if url is None:
        return None

    filename = url.rsplit("/", 1)[-1]
    dest = dest_dir / filename
    if dest.exists():
        return dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers=_headers())
    try:
        with urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
    except URLError as exc:
        raise ConnectionError(f"Failed to download {url}: {exc}") from exc
    return dest
