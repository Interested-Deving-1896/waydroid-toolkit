"""NFS shared-storage management for the Waydroid Incus container.

Ported from canonical/anbox-cloud-nfs-operator (Apache-2.0).
Juju charm replaced with direct incus config device commands.
LXD node NFS mounts replaced with Incus container disk devices.

The Anbox charm mounted NFS at /media/anbox-data inside LXD nodes.
Here we mount NFS (or any network path) as an Incus disk device inside
the Waydroid container, making shared data (e.g. game assets, media)
available at a configurable container path.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

_DEFAULT_CONTAINER = "waydroid"
_DEFAULT_CONTAINER_PATH = "/data/shared"


@dataclass
class NfsMount:
    """Represents an NFS disk device attached to the Waydroid container."""

    device_name: str
    source: str          # NFS host:/path or local path
    container_path: str  # mount point inside the container
    mount_type: str      # "nfs", "efs", or "disk"
    options: str         # extra mount options (e.g. "soft,async,fsc")


def _container_name() -> str:
    try:
        from waydroid_toolkit.core.container import get_active as get_backend
        return get_backend().get_info().container_name  # type: ignore[attr-defined]
    except Exception:
        return _DEFAULT_CONTAINER


def add_nfs_mount(
    source: str,
    container_path: str = _DEFAULT_CONTAINER_PATH,
    device_name: str = "",
    mount_type: str = "nfs",
    extra_options: str = "soft,async",
) -> NfsMount:
    """Attach an NFS share to the Waydroid container as an Incus disk device.

    Args:
        source: NFS path in host:/path format (or local path for bind mounts).
        container_path: Mount point inside the container.
        device_name: Incus device name; defaults to nfs-<sanitised-path>.
        mount_type: "nfs", "efs", or "disk" (disk = local bind mount).
        extra_options: Additional mount options appended to the base set.

    Returns:
        NfsMount describing the created device.

    Raises:
        subprocess.CalledProcessError: if the incus command fails.
        ValueError: if mount_type is not recognised.
    """
    allowed = ("nfs", "efs", "disk")
    if mount_type not in allowed:
        raise ValueError(f"mount_type must be one of {allowed}, got {mount_type!r}")

    ct = _container_name()
    if not device_name:
        safe = source.replace("/", "-").replace(":", "-").strip("-")
        device_name = f"nfs-{safe}"[:63]  # Incus device name limit

    # Build the incus device add command.
    # For NFS/EFS we use a disk device with the source as the NFS path.
    # Incus disk devices support NFS sources via the source= parameter when
    # the host has nfs-common installed and the path is pre-mounted, or via
    # a raw.mount.options override for direct NFS mounting.
    cmd = [
        "incus", "config", "device", "add", ct, device_name, "disk",
        f"source={source}",
        f"path={container_path}",
    ]
    if extra_options:
        cmd.append(f"raw.mount.options={extra_options}")

    subprocess.run(cmd, check=True)
    return NfsMount(
        device_name=device_name,
        source=source,
        container_path=container_path,
        mount_type=mount_type,
        options=extra_options,
    )


def remove_nfs_mount(device_name: str) -> None:
    """Remove an NFS disk device from the Waydroid container.

    Args:
        device_name: The Incus device name to remove.

    Raises:
        subprocess.CalledProcessError: if the incus command fails.
    """
    ct = _container_name()
    subprocess.run(
        ["incus", "config", "device", "remove", ct, device_name],
        check=True,
    )


def list_nfs_mounts() -> list[NfsMount]:
    """Return all disk devices attached to the Waydroid container.

    Returns only devices of type "disk" (which includes NFS mounts).
    """
    import json

    ct = _container_name()
    result = subprocess.run(
        ["incus", "config", "device", "show", ct, "--format", "json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    try:
        devices: dict = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    mounts = []
    for name, cfg in devices.items():
        if cfg.get("type") != "disk":
            continue
        mounts.append(NfsMount(
            device_name=name,
            source=cfg.get("source", ""),
            container_path=cfg.get("path", ""),
            mount_type="disk",
            options=cfg.get("raw.mount.options", ""),
        ))
    return mounts
