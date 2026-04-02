"""Extension engine — install/uninstall GApps, Magisk, ARM translation, microG."""

from .base import Extension, ExtensionMeta, ExtensionState
from .registry import REGISTRY, get, list_all
from .resolver import (
    ConflictError,
    CyclicDependencyError,
    DependencyError,
    MissingDependencyError,
    install_with_deps,
    resolve,
)

__all__ = [
    "REGISTRY",
    "ConflictError",
    "CyclicDependencyError",
    "DependencyError",
    "Extension",
    "ExtensionMeta",
    "ExtensionState",
    "MissingDependencyError",
    "get",
    "install_with_deps",
    "list_all",
    "resolve",
]
