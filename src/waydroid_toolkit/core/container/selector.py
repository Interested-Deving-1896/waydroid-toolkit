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


class ConfigError(ValueError):
    """Raised when the toolkit config file is present but invalid."""


def _read_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        with _CONFIG_PATH.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"Config file is not valid TOML: {_CONFIG_PATH}\n"
            f"  {exc}\n"
            "Fix or delete the file and try again."
        ) from exc
    _validate_config(data)
    return data


def _validate_config(data: dict) -> None:
    """Raise ConfigError if the config contains unrecognised or invalid values."""
    container = data.get("container", {})
    if not isinstance(container, dict):
        raise ConfigError(
            f"[container] section in {_CONFIG_PATH} must be a table, "
            f"got {type(container).__name__}."
        )
    backend_name = container.get("backend", "")
    if backend_name:
        valid = {bt.value for bt in BackendType}
        if backend_name.lower() not in valid:
            raise ConfigError(
                f"Unknown backend '{backend_name}' in {_CONFIG_PATH}. "
                f"Valid values: {', '.join(sorted(valid))}. "
                "Run 'wdt backend list' to see available backends."
            )


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
