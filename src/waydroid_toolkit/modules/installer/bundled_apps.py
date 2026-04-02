"""Bundled app installation — runs after `waydroid init`.

Apps are pre-installed into the Waydroid image in two groups:

GitLab Releases (AuroraOSS projects — APKs embedded in release descriptions):
  - F-Droid              https://f-droid.org/F-Droid.apk  (direct stable URL)
  - AuroraStore          gitlab.com/AuroraOSS/AuroraStore
  - AuroraDroid          gitlab.com/AuroraOSS/AuroraDroid
  - AuroraServices       gitlab.com/AuroraOSS/AuroraServices

GitHub Releases (latest .apk asset, silently skipped if none exists):
  - Authenticator        whyorean/Authenticator
  - YalpStore            whyorean/YalpStore
  - GitHub-Store         OpenHub-Store/GitHub-Store

All downloads are cached under /tmp/waydroid-toolkit/bundled/ so repeated
calls (e.g. re-init) avoid redundant network traffic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from waydroid_toolkit.core.adb import connect, install_apk
from waydroid_toolkit.utils.github_releases import download_latest_apk as gh_download
from waydroid_toolkit.utils.gitlab_releases import download_latest_apk as gl_download
from waydroid_toolkit.utils.net import download

_CACHE_DIR = Path("/tmp/waydroid-toolkit/bundled")


@dataclass
@dataclass
class _DirectApp:
    """App with a fixed, stable download URL."""
    name: str
    url: str


@dataclass
class _GitLabApp:
    """App distributed via GitLab Releases upload links."""
    name: str
    namespace: str
    project: str
    variant: str | None = None


@dataclass
class _GitHubApp:
    """App distributed via GitHub Releases APK assets."""
    name: str
    owner: str
    repo: str


# ── App registry ──────────────────────────────────────────────────────────────

_DIRECT_APPS: list[_DirectApp] = [
    _DirectApp("F-Droid", "https://f-droid.org/F-Droid.apk"),
]

_GITLAB_APPS: list[_GitLabApp] = [
    _GitLabApp("AuroraStore",    "AuroraOSS", "AuroraStore"),
    _GitLabApp("AuroraDroid",    "AuroraOSS", "AuroraDroid"),
    _GitLabApp("AuroraServices", "AuroraOSS", "AuroraServices"),
]

_GITHUB_APPS: list[_GitHubApp] = [
    _GitHubApp("Authenticator", "whyorean",      "Authenticator"),
    _GitHubApp("YalpStore",     "whyorean",      "YalpStore"),
    _GitHubApp("GitHub-Store",  "OpenHub-Store", "GitHub-Store"),
]


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class InstallResult:
    name: str
    success: bool
    skipped: bool = False
    reason: str = ""


# ── Public API ────────────────────────────────────────────────────────────────

def install_bundled_apps(
    progress: Callable[[str], None] | None = None,
) -> list[InstallResult]:
    """Download and install all bundled apps into the running Waydroid session.

    Requires an active Waydroid session (ADB must be reachable). Each app is
    attempted independently — a failure on one does not abort the rest.

    Returns a list of InstallResult for callers that want to report outcomes.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _p(msg: str) -> None:
        if progress:
            progress(msg)

    _p("Connecting to Waydroid via ADB...")
    if not connect(retries=5, delay=2.0):
        raise RuntimeError(
            "Could not connect to Waydroid via ADB. "
            "Ensure the session is running before installing bundled apps."
        )

    results: list[InstallResult] = []

    for direct_app in _DIRECT_APPS:
        results.append(_install_direct(direct_app, _p))

    for gitlab_app in _GITLAB_APPS:
        results.append(_install_gitlab(gitlab_app, _p))

    for github_app in _GITHUB_APPS:
        results.append(_install_github(github_app, _p))

    return results


def bundled_app_names() -> list[str]:
    """Return the display names of all bundled apps."""
    return (
        [a.name for a in _DIRECT_APPS]
        + [a.name for a in _GITLAB_APPS]
        + [a.name for a in _GITHUB_APPS]
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _push_apk(name: str, apk: Path, progress: Callable[[str], None]) -> InstallResult:
    progress(f"Installing {name}...")
    result = install_apk(apk)
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        return InstallResult(name=name, success=False, reason=err)
    progress(f"{name} installed.")
    return InstallResult(name=name, success=True)


def _install_direct(app: _DirectApp, progress: Callable[[str], None]) -> InstallResult:
    filename = app.url.rsplit("/", 1)[-1]
    dest = _CACHE_DIR / filename
    try:
        if not dest.exists():
            progress(f"Downloading {app.name}...")
            download(app.url, dest)
        else:
            progress(f"{app.name}: using cached APK.")
        return _push_apk(app.name, dest, progress)
    except Exception as exc:  # noqa: BLE001
        progress(f"Warning: {app.name} failed — {exc}")
        return InstallResult(name=app.name, success=False, reason=str(exc))


def _install_gitlab(app: _GitLabApp, progress: Callable[[str], None]) -> InstallResult:
    try:
        progress(f"Fetching latest release for {app.name}...")
        apk = gl_download(app.namespace, app.project, _CACHE_DIR, app.variant)
        if apk is None:
            progress(f"{app.name}: no APK in latest release, skipping.")
            return InstallResult(
                name=app.name, success=False, skipped=True,
                reason="No APK found in latest GitLab release.",
            )
        return _push_apk(app.name, apk, progress)
    except Exception as exc:  # noqa: BLE001
        progress(f"Warning: {app.name} failed — {exc}")
        return InstallResult(name=app.name, success=False, reason=str(exc))


def _install_github(app: _GitHubApp, progress: Callable[[str], None]) -> InstallResult:
    try:
        progress(f"Fetching latest release for {app.name}...")
        apk = gh_download(app.owner, app.repo, _CACHE_DIR)
        if apk is None:
            progress(f"{app.name}: no APK release found, skipping.")
            return InstallResult(
                name=app.name, success=False, skipped=True,
                reason="No APK asset in latest GitHub release.",
            )
        return _push_apk(app.name, apk, progress)
    except Exception as exc:  # noqa: BLE001
        progress(f"Warning: {app.name} failed — {exc}")
        return InstallResult(name=app.name, success=False, reason=str(exc))
