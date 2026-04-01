"""Tests for the extension registry and base class."""

import pytest

from waydroid_toolkit.modules.extensions import REGISTRY, get, list_all
from waydroid_toolkit.modules.extensions.base import ExtensionState


def test_registry_contains_expected_extensions() -> None:
    expected = {"gapps", "microg", "magisk", "libhoudini", "libndk"}
    assert expected == set(REGISTRY.keys())


def test_get_known_extension() -> None:
    ext = get("gapps")
    assert ext.meta.id == "gapps"
    assert ext.meta.name


def test_get_unknown_extension_raises() -> None:
    with pytest.raises(KeyError, match="Unknown extension"):
        get("nonexistent")


def test_list_all_returns_all() -> None:
    exts = list_all()
    assert len(exts) == len(REGISTRY)


def test_gapps_conflicts_with_microg() -> None:
    gapps = get("gapps")
    assert "microg" in gapps.meta.conflicts


def test_microg_conflicts_with_gapps() -> None:
    microg = get("microg")
    assert "gapps" in microg.meta.conflicts


def test_libhoudini_conflicts_with_libndk() -> None:
    houdini = get("libhoudini")
    assert "libndk" in houdini.meta.conflicts


def test_extension_state_returns_enum(monkeypatch) -> None:
    ext = get("gapps")
    monkeypatch.setattr(ext, "is_installed", lambda: False)
    assert ext.state() == ExtensionState.NOT_INSTALLED

    monkeypatch.setattr(ext, "is_installed", lambda: True)
    assert ext.state() == ExtensionState.INSTALLED

    monkeypatch.setattr(ext, "is_installed", lambda: (_ for _ in ()).throw(RuntimeError("oops")))
    assert ext.state() == ExtensionState.UNKNOWN
