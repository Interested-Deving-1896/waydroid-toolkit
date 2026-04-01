"""Extension registry — central catalogue of all available extensions.

Usage:
    from waydroid_toolkit.modules.extensions.registry import REGISTRY

    for ext in REGISTRY.values():
        print(ext.meta.name, ext.state())
"""

from __future__ import annotations

from .arm_translation import LibhoudiniExtension, LibndkExtension
from .base import Extension
from .gapps import GAppsExtension
from .magisk import MagiskExtension
from .microg import MicroGExtension

REGISTRY: dict[str, Extension] = {
    "gapps": GAppsExtension(),
    "microg": MicroGExtension(),
    "magisk": MagiskExtension(),
    "libhoudini": LibhoudiniExtension(),
    "libndk": LibndkExtension(),
}


def get(extension_id: str) -> Extension:
    if extension_id not in REGISTRY:
        raise KeyError(f"Unknown extension: {extension_id!r}. Available: {list(REGISTRY)}")
    return REGISTRY[extension_id]


def list_all() -> list[Extension]:
    return list(REGISTRY.values())
