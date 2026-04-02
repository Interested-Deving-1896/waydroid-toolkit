"""Image profile management module."""

from .androidtv import (
    apply_atv_props,
    apply_standard_props,
    is_atv_profile,
    profile_is_atv_configured,
)
from .manager import ImageProfile, get_active_profile, scan_profiles, switch_profile
from .ota import OtaEntry, UpdateInfo, check_updates, download_image, download_updates

__all__ = [
    "ImageProfile",
    "OtaEntry",
    "UpdateInfo",
    "apply_atv_props",
    "apply_standard_props",
    "check_updates",
    "download_image",
    "download_updates",
    "get_active_profile",
    "is_atv_profile",
    "profile_is_atv_configured",
    "scan_profiles",
    "switch_profile",
]
