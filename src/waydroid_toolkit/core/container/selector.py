"""Backend selector — reads/writes the active backend from toolkit config.

The selected backend is stored in:
    ~/.config/waydroid-toolkit/config.toml

under the key:
    [container]
    backend = "lxc"   # or "incus"

If the file does not exist, or no backend is configured, the selector
auto-detects: LXC is preferred if available, then Incus, then raises.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from .base import BackendType, ContainerBackend
from .incus_backend import IncusBackend
from .lxc_backend import LxcBackend

_CONFIG_PATH = Path.home() / ".config" / "waydroid-toolkit" / "config.toml"

_BACKENDS: dict[BackendType, type[ContainerBackend]] = {
    BackendType.LXC: LxcBackend,
    BackendType.INCUS: IncusBackend,
}


def _read_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    with _CONFIG_PATH.open("rb") as fh:
        return tomllib.load(fh)


def _write_config(data: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _CONFIG_PATH.open("wb") as fh:
        tomli_w.dump(data, fh)


def detect() -> ContainerBackend:
    """Return the first available backend (LXC preferred, then Incus)."""
    for backend_cls in (LxcBackend, IncusBackend):
        backend = backend_cls()
        if backend.is_available():
            return backend
    raise RuntimeError(
        "No container backend found. Install lxc or incus."
    )


def get_active() -> ContainerBackend:
    """Return the configured backend, falling back to auto-detect."""
    cfg = _read_config()
    backend_name = cfg.get("container", {}).get("backend", "")
    if backend_name:
        try:
            backend_type = BackendType(backend_name.lower())
            backend = _BACKENDS[backend_type]()
            if not backend.is_available():
                raise RuntimeError(
                    f"Configured backend '{backend_name}' is not available "
                    f"(binary not found). Run 'wdt backend detect' to switch."
                )
            return backend
        except ValueError:
            pass  # unknown value in config — fall through to auto-detect
    return detect()


def set_active(backend_type: BackendType) -> None:
    """Persist the chosen backend to the toolkit config file."""
    cfg = _read_config()
    if "container" not in cfg:
        cfg["container"] = {}
    cfg["container"]["backend"] = backend_type.value
    _write_config(cfg)


def list_available() -> list[ContainerBackend]:
    """Return all backends whose binary is present on PATH."""
    return [cls() for cls in _BACKENDS.values() if cls().is_available()]
