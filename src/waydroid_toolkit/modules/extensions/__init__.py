"""Extension engine — install/uninstall GApps, Magisk, ARM translation, microG."""

from .base import Extension, ExtensionMeta, ExtensionState
from .registry import REGISTRY, get, list_all

__all__ = ["Extension", "ExtensionMeta", "ExtensionState", "REGISTRY", "get", "list_all"]
