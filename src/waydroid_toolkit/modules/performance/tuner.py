"""Performance tuning for Waydroid gaming.

Applies host-side optimisations: ZRAM configuration, CPU governor,
and GameMode integration. Mirrors lil-xhris/Waydroid-boost- behaviour.

All operations require root and are designed for Debian/Ubuntu hosts,
though CPU governor and GameMode work on any systemd-based distro.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from waydroid_toolkit.core.privilege import require_root

_SYSTEMD_SERVICE = Path("/etc/systemd/system/waydroid-boost.service")

_SERVICE_TEMPLATE = """\
[Unit]
Description=WayDroid Toolkit performance tuning
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/wdt-boost apply
ExecStop=/usr/local/bin/wdt-boost restore

[Install]
WantedBy=multi-user.target
"""


@dataclass
class PerformanceProfile:
    zram_size_mb: int = 4096          # ZRAM swap size in MB
    zram_algorithm: str = "lz4"       # lz4 is fastest; zstd gives better ratio
    cpu_governor: str = "performance" # performance | schedutil | powersave
    enable_turbo: bool = True
    use_gamemode: bool = True         # requires gamemode package


def _set_zram(size_mb: int, algorithm: str) -> None:
    """Configure ZRAM swap."""
    # Remove existing zram devices
    subprocess.run(["sudo", "swapoff", "-a"], capture_output=True)
    for dev in Path("/dev").glob("zram*"):
        subprocess.run(["sudo", "zramctl", "--reset", str(dev)], capture_output=True)

    result = subprocess.run(
        ["sudo", "zramctl", "--find", "--size", f"{size_mb}M", "--algorithm", algorithm],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"zramctl failed: {result.stderr}")
    zram_dev = result.stdout.strip()
    subprocess.run(["sudo", "mkswap", zram_dev], check=True, capture_output=True)
    subprocess.run(
        ["sudo", "swapon", "--priority", "100", zram_dev], check=True, capture_output=True,
    )


def _set_cpu_governor(governor: str) -> None:
    for policy in Path("/sys/devices/system/cpu/cpufreq").glob("policy*"):
        gov_file = policy / "scaling_governor"
        if gov_file.exists():
            subprocess.run(["sudo", "tee", str(gov_file)],
                           input=governor, capture_output=True, text=True)


def _set_turbo(enabled: bool) -> None:
    turbo_file = Path("/sys/devices/system/cpu/intel_pstate/no_turbo")
    if turbo_file.exists():
        value = "0" if enabled else "1"
        subprocess.run(["sudo", "tee", str(turbo_file)],
                       input=value, capture_output=True, text=True)


def apply_profile(
    profile: PerformanceProfile = PerformanceProfile(),
    progress: Callable[[str], None] | None = None,
) -> None:
    """Apply the performance profile to the host system."""
    require_root("Applying performance profile")

    if progress:
        progress(f"Configuring ZRAM ({profile.zram_size_mb}MB, {profile.zram_algorithm})...")
    _set_zram(profile.zram_size_mb, profile.zram_algorithm)

    if progress:
        progress(f"Setting CPU governor to '{profile.cpu_governor}'...")
    _set_cpu_governor(profile.cpu_governor)

    if profile.enable_turbo:
        if progress:
            progress("Enabling CPU Turbo Boost...")
        _set_turbo(True)

    if profile.use_gamemode and shutil.which("gamemoded"):
        if progress:
            progress("Starting GameMode daemon...")
        subprocess.run(["gamemoded", "-r"], capture_output=True)

    if progress:
        progress("Performance profile applied.")


def restore_defaults(progress: Callable[[str], None] | None = None) -> None:
    """Restore conservative defaults (schedutil governor, disable ZRAM boost)."""
    require_root("Restoring performance defaults")
    if progress:
        progress("Restoring CPU governor to 'schedutil'...")
    _set_cpu_governor("schedutil")
    if progress:
        progress("Defaults restored.")


def install_systemd_service(progress: Callable[[str], None] | None = None) -> None:
    """Install a systemd service so the profile persists across reboots."""
    require_root("Installing performance systemd service")
    subprocess.run(
        ["sudo", "tee", str(_SYSTEMD_SERVICE)],
        input=_SERVICE_TEMPLATE, capture_output=True, text=True,
    )
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
    subprocess.run(["sudo", "systemctl", "enable", "--now", "waydroid-boost.service"], check=True)
    if progress:
        progress("waydroid-boost.service installed and enabled.")
