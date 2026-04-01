"""Network helpers — download with progress, checksum verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError


def download(
    url: str,
    dest: Path,
    progress: Optional[Callable[[int, int], None]] = None,
    chunk_size: int = 65536,
) -> Path:
    """Download url to dest, calling progress(bytes_done, total_bytes) each chunk."""
    req = Request(url, headers={"User-Agent": "waydroid-toolkit/0.1"})
    try:
        with urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            done = 0
            with dest.open("wb") as fh:
                while chunk := resp.read(chunk_size):
                    fh.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
    except URLError as exc:
        raise ConnectionError(f"Failed to download {url}: {exc}") from exc
    return dest


def verify_sha256(path: Path, expected: str) -> bool:
    """Return True if the file's SHA-256 matches expected."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()
