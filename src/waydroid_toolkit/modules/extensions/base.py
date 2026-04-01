"""Extension plugin base class.

Each installable extension (GApps, Magisk, ARM translation, Widevine, microG)
implements this interface. The extension engine discovers and runs them uniformly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class ExtensionState(Enum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"


@dataclass
class ExtensionMeta:
    id: str                          # machine-readable slug, e.g. "gapps"
    name: str                        # human-readable, e.g. "Google Apps (OpenGApps)"
    description: str
    requires_root: bool = True
    conflicts: list[str] = field(default_factory=list)   # ids of conflicting extensions
    requires: list[str] = field(default_factory=list)    # ids of required extensions


class Extension(ABC):
    """Abstract base for all installable Waydroid extensions."""

    @property
    @abstractmethod
    def meta(self) -> ExtensionMeta:
        ...

    @abstractmethod
    def is_installed(self) -> bool:
        ...

    @abstractmethod
    def install(self, progress: Optional[Callable[[str], None]] = None) -> None:
        ...

    @abstractmethod
    def uninstall(self, progress: Optional[Callable[[str], None]] = None) -> None:
        ...

    def state(self) -> ExtensionState:
        try:
            return ExtensionState.INSTALLED if self.is_installed() else ExtensionState.NOT_INSTALLED
        except Exception:
            return ExtensionState.UNKNOWN
