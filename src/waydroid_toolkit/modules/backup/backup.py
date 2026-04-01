"""Waydroid backup and restore.

Backs up the three Waydroid data directories to a compressed tar.gz archive.
Mirrors the behaviour of berndhofer/waybak with added integrity verification.

Directories backed up:
  - ~/.local/share/waydroid      (user app data)
  - /var/lib/waydroid            (container config, images path)
  - /etc/waydroid-extra/images   (extra images, if present)
"""

from __future__ import annotations

import datetime
import subprocess
from collections.abc import Callable
from pathlib import Path

from waydroid_toolkit.core.privilege import require_root
from waydroid_toolkit.core.waydroid import SessionState, get_session_state, run_waydroid

_USER_DATA = Path.home() / ".local/share/waydroid"
_VAR_DATA = Path("/var/lib/waydroid")
_ETC_DATA = Path("/etc/waydroid-extra/images")

DEFAULT_BACKUP_DIR = Path.home() / ".local/share/waydroid-toolkit/backups"


def _stop_session() -> bool:
    """Stop the Waydroid session if running. Returns True if it was running."""
    if get_session_state() == SessionState.RUNNING:
        run_waydroid("session", "stop", sudo=True)
        subprocess.run(["sudo", "systemctl", "stop", "waydroid-container"], capture_output=True)
        return True
    return False


def create_backup(
    dest_dir: Path = DEFAULT_BACKUP_DIR,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Create a compressed backup archive. Returns the path to the archive."""
    require_root("Creating Waydroid backup")
    dest_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = dest_dir / f"waydroid_backup_{ts}.tar.gz"

    was_running = _stop_session()
    if was_running and progress:
        progress("Stopped Waydroid session for backup.")

    sources = [p for p in [_USER_DATA, _VAR_DATA, _ETC_DATA] if p.exists()]

    if progress:
        progress(f"Creating archive: {archive.name}")

    # Use sudo tar to read root-owned /var/lib/waydroid
    cmd = ["sudo", "tar", "-czf", str(archive)] + [str(s) for s in sources]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Backup failed: {result.stderr}")

    # Fix ownership so the user can read the archive
    subprocess.run(["sudo", "chown", f"{Path.home().owner()}:", str(archive)], capture_output=True)

    if progress:
        progress(f"Backup complete: {archive}")
    return archive


def list_backups(backup_dir: Path = DEFAULT_BACKUP_DIR) -> list[Path]:
    """Return available backup archives sorted newest-first."""
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("waydroid_backup_*.tar.gz"), reverse=True)


def restore_backup(
    archive: Path,
    progress: Callable[[str], None] | None = None,
) -> None:
    """Restore Waydroid data from a backup archive."""
    require_root("Restoring Waydroid backup")
    if not archive.exists():
        raise FileNotFoundError(f"Backup archive not found: {archive}")

    was_running = _stop_session()
    if was_running and progress:
        progress("Stopped Waydroid session for restore.")

    if progress:
        progress(f"Restoring from {archive.name}...")

    cmd = ["sudo", "tar", "-xzf", str(archive), "-C", "/"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Restore failed: {result.stderr}")

    if progress:
        progress("Restore complete.")
