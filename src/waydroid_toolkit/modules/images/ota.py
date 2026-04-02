"""Waydroid OTA image update checker and downloader.

The Waydroid OTA server returns a JSON manifest at the channel URL:

    GET https://ota.waydro.id/system
    {"response": [
        {
            "datetime":  1680000000,
            "filename":  "system.img.zip",
            "url":       "https://...",
            "id":        "<sha256hex>"
        },
        ...
    ]}

The ``datetime`` field is a Unix timestamp. An update is available when
the server's latest ``datetime`` is greater than the value stored in
``waydroid.cfg`` (``system_datetime`` / ``vendor_datetime``).

The downloaded zip contains a single ``system.img`` or ``vendor.img``
file that is extracted directly into the target images directory.
"""

from __future__ import annotations

import configparser
import hashlib
import json
import subprocess
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from waydroid_toolkit.core.waydroid import WaydroidConfig

_CFG_PATH = Path("/var/lib/waydroid/waydroid.cfg")
_DOWNLOAD_TIMEOUT = 30  # seconds for the manifest fetch


@dataclass
class OtaEntry:
    """A single entry from an OTA channel manifest."""

    datetime: int
    filename: str
    url: str
    sha256: str  # ``id`` field in the manifest


@dataclass
class UpdateInfo:
    """Result of an update check for one image (system or vendor)."""

    channel: str          # "system" or "vendor"
    current_datetime: int
    latest: OtaEntry | None  # None when the channel returned no entries
    update_available: bool


# ── Manifest fetching ─────────────────────────────────────────────────────────

def fetch_manifest(url: str, timeout: int = _DOWNLOAD_TIMEOUT) -> list[OtaEntry]:
    """Fetch and parse an OTA channel manifest. Returns entries newest-first."""
    req = urllib.request.Request(url, headers={"User-Agent": "waydroid-toolkit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())

    entries = []
    for item in data.get("response", []):
        entries.append(OtaEntry(
            datetime=int(item["datetime"]),
            filename=item["filename"],
            url=item["url"],
            sha256=item["id"],
        ))
    # Sort newest first so entries[0] is always the latest build
    entries.sort(key=lambda e: e.datetime, reverse=True)
    return entries


# ── Update check ──────────────────────────────────────────────────────────────

def check_updates(cfg: WaydroidConfig | None = None) -> tuple[UpdateInfo, UpdateInfo]:
    """Check both OTA channels for available updates.

    Returns ``(system_info, vendor_info)``. Does not download anything.
    Raises ``urllib.error.URLError`` / ``OSError`` on network failure.
    """
    if cfg is None:
        cfg = WaydroidConfig.load()

    def _check(channel: str, url: str, current_dt: int) -> UpdateInfo:
        entries = fetch_manifest(url)
        latest = entries[0] if entries else None
        available = latest is not None and latest.datetime > current_dt
        return UpdateInfo(
            channel=channel,
            current_datetime=current_dt,
            latest=latest,
            update_available=available,
        )

    system_info = _check("system", cfg.system_ota, cfg.system_datetime)
    vendor_info  = _check("vendor", cfg.vendor_ota,  cfg.vendor_datetime)
    return system_info, vendor_info


# ── Download helpers ──────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_with_progress(
    url: str,
    dest: Path,
    progress: Callable[[str], None] | None,
) -> None:
    """Stream *url* to *dest*, calling *progress* with human-readable status."""
    req = urllib.request.Request(url, headers={"User-Agent": "waydroid-toolkit/1.0"})
    with urllib.request.urlopen(req) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with dest.open("wb") as fh:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if progress and total:
                    pct = downloaded * 100 // total
                    mb = downloaded / 1_048_576
                    total_mb = total / 1_048_576
                    progress(f"  {mb:.1f} / {total_mb:.1f} MB ({pct}%)")


def _save_datetime(channel: str, dt: int) -> None:
    """Persist the updated datetime back to waydroid.cfg (requires root)."""
    key = f"{channel}_datetime"
    parser = configparser.ConfigParser()
    if _CFG_PATH.exists():
        parser.read(_CFG_PATH)
    if "waydroid" not in parser:
        parser["waydroid"] = {}
    parser["waydroid"][key] = str(dt)
    tmp = _CFG_PATH.with_suffix(".tmp")
    with tmp.open("w") as fh:
        parser.write(fh)
    subprocess.run(["sudo", "mv", str(tmp), str(_CFG_PATH)], check=True)


# ── Download + install ────────────────────────────────────────────────────────

def download_image(
    entry: OtaEntry,
    dest_dir: Path,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Download *entry* into *dest_dir*, verify SHA-256, extract the image.

    Returns the path to the extracted ``.img`` file.
    Raises ``RuntimeError`` on hash mismatch (partial download deleted).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="wdt-ota-") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / entry.filename

        if progress:
            progress(f"Downloading {entry.filename}…")
        _download_with_progress(entry.url, zip_path, progress)

        if progress:
            progress("Verifying SHA-256…")
        actual = _sha256(zip_path)
        if actual != entry.sha256:
            raise RuntimeError(
                f"SHA-256 mismatch for {entry.filename}:\n"
                f"  expected: {entry.sha256}\n"
                f"  got:      {actual}\n"
                "The download may be corrupt. Try again."
            )

        if progress:
            progress(f"Extracting to {dest_dir}…")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)

        # Return the path to the extracted image (system.img or vendor.img)
        img_name = entry.filename.replace(".zip", "")
        return dest_dir / img_name


def download_updates(
    dest_dir: Path,
    cfg: WaydroidConfig | None = None,
    progress: Callable[[str], None] | None = None,
    update_cfg: bool = True,
) -> tuple[Path | None, Path | None]:
    """Download any available system and vendor image updates.

    Returns ``(system_img_path, vendor_img_path)``. Either may be ``None``
    if that channel had no update available.

    When *update_cfg* is True (default), persists the new ``datetime``
    values to ``waydroid.cfg`` after each successful download.
    """
    if cfg is None:
        cfg = WaydroidConfig.load()

    system_path: Path | None = None
    vendor_path: Path | None = None

    system_info, vendor_info = check_updates(cfg)

    if system_info.update_available and system_info.latest:
        if progress:
            progress("System image update available.")
        system_path = download_image(system_info.latest, dest_dir, progress)
        if update_cfg:
            _save_datetime("system", system_info.latest.datetime)
    else:
        if progress:
            progress("System image is up to date.")

    if vendor_info.update_available and vendor_info.latest:
        if progress:
            progress("Vendor image update available.")
        vendor_path = download_image(vendor_info.latest, dest_dir, progress)
        if update_cfg:
            _save_datetime("vendor", vendor_info.latest.datetime)
    else:
        if progress:
            progress("Vendor image is up to date.")

    return system_path, vendor_path
