"""Performance tuning module — ZRAM, CPU governor, GameMode."""

from .tuner import PerformanceProfile, apply_profile, install_systemd_service, restore_defaults

__all__ = ["PerformanceProfile", "apply_profile", "install_systemd_service", "restore_defaults"]
