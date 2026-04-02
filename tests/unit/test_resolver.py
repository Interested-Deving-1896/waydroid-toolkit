"""Tests for waydroid_toolkit.modules.extensions.resolver."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from waydroid_toolkit.modules.extensions.base import Extension, ExtensionMeta
from waydroid_toolkit.modules.extensions.resolver import (
    ConflictError,
    CyclicDependencyError,
    MissingDependencyError,
    install_with_deps,
    resolve,
)

# ── Test fixtures ─────────────────────────────────────────────────────────────

def _make_ext(
    ext_id: str,
    requires: list[str] | None = None,
    conflicts: list[str] | None = None,
    installed: bool = False,
) -> Extension:
    """Build a minimal mock Extension."""
    meta = ExtensionMeta(
        id=ext_id,
        name=ext_id.capitalize(),
        description="",
        requires=requires or [],
        conflicts=conflicts or [],
    )
    ext = MagicMock(spec=Extension)
    ext.meta = meta
    ext.is_installed.return_value = installed
    return ext


def _registry(*exts: Extension) -> dict[str, Extension]:
    return {e.meta.id: e for e in exts}


# ── resolve — basic ordering ──────────────────────────────────────────────────

class TestResolveOrdering:
    def test_single_extension_no_deps(self) -> None:
        reg = _registry(_make_ext("a"))
        assert resolve(["a"], reg) == ["a"]

    def test_dependency_comes_before_dependent(self) -> None:
        reg = _registry(
            _make_ext("a", requires=["b"]),
            _make_ext("b"),
        )
        order = resolve(["a"], reg)
        assert order.index("b") < order.index("a")

    def test_transitive_dependency_resolved(self) -> None:
        # a → b → c
        reg = _registry(
            _make_ext("a", requires=["b"]),
            _make_ext("b", requires=["c"]),
            _make_ext("c"),
        )
        order = resolve(["a"], reg)
        assert order.index("c") < order.index("b") < order.index("a")

    def test_multiple_requested_merged(self) -> None:
        reg = _registry(
            _make_ext("a", requires=["c"]),
            _make_ext("b", requires=["c"]),
            _make_ext("c"),
        )
        order = resolve(["a", "b"], reg)
        assert "c" in order
        assert order.index("c") < order.index("a")
        assert order.index("c") < order.index("b")

    def test_shared_dep_appears_once(self) -> None:
        reg = _registry(
            _make_ext("a", requires=["c"]),
            _make_ext("b", requires=["c"]),
            _make_ext("c"),
        )
        order = resolve(["a", "b"], reg)
        assert order.count("c") == 1

    def test_no_deps_returns_all_requested(self) -> None:
        reg = _registry(_make_ext("x"), _make_ext("y"), _make_ext("z"))
        order = resolve(["x", "y", "z"], reg)
        assert set(order) == {"x", "y", "z"}

    def test_already_in_requested_not_duplicated(self) -> None:
        reg = _registry(
            _make_ext("a", requires=["b"]),
            _make_ext("b"),
        )
        order = resolve(["a", "b"], reg)
        assert order.count("b") == 1

    def test_diamond_dependency(self) -> None:
        # a → b, a → c, b → d, c → d
        reg = _registry(
            _make_ext("a", requires=["b", "c"]),
            _make_ext("b", requires=["d"]),
            _make_ext("c", requires=["d"]),
            _make_ext("d"),
        )
        order = resolve(["a"], reg)
        assert order.index("d") < order.index("b")
        assert order.index("d") < order.index("c")
        assert order.index("b") < order.index("a")
        assert order.index("c") < order.index("a")
        assert order.count("d") == 1


# ── resolve — error cases ─────────────────────────────────────────────────────

class TestResolveErrors:
    def test_unknown_requested_raises_missing(self) -> None:
        reg = _registry(_make_ext("a"))
        with pytest.raises(MissingDependencyError) as exc_info:
            resolve(["unknown"], reg)
        assert "unknown" in str(exc_info.value)

    def test_missing_transitive_dep_raises(self) -> None:
        reg = _registry(_make_ext("a", requires=["missing"]))
        with pytest.raises(MissingDependencyError) as exc_info:
            resolve(["a"], reg)
        assert "missing" in str(exc_info.value)
        assert exc_info.value.required_by == "a"

    def test_conflict_raises(self) -> None:
        reg = _registry(
            _make_ext("a", conflicts=["b"]),
            _make_ext("b"),
        )
        with pytest.raises(ConflictError) as exc_info:
            resolve(["a", "b"], reg)
        assert "a" in str(exc_info.value) or "b" in str(exc_info.value)

    def test_conflict_via_dependency_raises(self) -> None:
        # a requires b; b conflicts with c; c is also requested
        reg = _registry(
            _make_ext("a", requires=["b"]),
            _make_ext("b", conflicts=["c"]),
            _make_ext("c"),
        )
        with pytest.raises(ConflictError):
            resolve(["a", "c"], reg)

    def test_cyclic_dependency_raises(self) -> None:
        reg = _registry(
            _make_ext("a", requires=["b"]),
            _make_ext("b", requires=["a"]),
        )
        with pytest.raises(CyclicDependencyError) as exc_info:
            resolve(["a"], reg)
        assert "a" in exc_info.value.cycle or "b" in exc_info.value.cycle

    def test_three_node_cycle_raises(self) -> None:
        reg = _registry(
            _make_ext("a", requires=["b"]),
            _make_ext("b", requires=["c"]),
            _make_ext("c", requires=["a"]),
        )
        with pytest.raises(CyclicDependencyError):
            resolve(["a"], reg)

    def test_conflict_error_attributes(self) -> None:
        reg = _registry(
            _make_ext("gapps", conflicts=["microg"]),
            _make_ext("microg"),
        )
        with pytest.raises(ConflictError) as exc_info:
            resolve(["gapps", "microg"], reg)
        err = exc_info.value
        assert {err.ext_a, err.ext_b} == {"gapps", "microg"}

    def test_missing_dep_error_attributes(self) -> None:
        reg = _registry(_make_ext("a", requires=["ghost"]))
        with pytest.raises(MissingDependencyError) as exc_info:
            resolve(["a"], reg)
        err = exc_info.value
        assert err.missing_id == "ghost"
        assert err.required_by == "a"


# ── install_with_deps ─────────────────────────────────────────────────────────

class TestInstallWithDeps:
    def test_installs_in_order(self) -> None:
        call_order: list[str] = []

        def _make_installing_ext(ext_id: str, requires: list[str] | None = None) -> Extension:
            ext = _make_ext(ext_id, requires=requires, installed=False)
            ext.install.side_effect = lambda progress=None: call_order.append(ext_id)
            return ext

        reg = _registry(
            _make_installing_ext("a", requires=["b"]),
            _make_installing_ext("b"),
        )
        install_with_deps(["a"], reg)
        assert call_order.index("b") < call_order.index("a")

    def test_skips_already_installed(self) -> None:
        b = _make_ext("b", installed=True)
        a = _make_ext("a", requires=["b"], installed=False)
        reg = _registry(a, b)
        installed = install_with_deps(["a"], reg)
        assert "b" not in installed
        assert "a" in installed
        b.install.assert_not_called()

    def test_returns_installed_ids(self) -> None:
        reg = _registry(
            _make_ext("x", installed=False),
            _make_ext("y", installed=False),
        )
        result = install_with_deps(["x", "y"], reg)
        assert set(result) == {"x", "y"}

    def test_progress_called_for_each_install(self) -> None:
        messages: list[str] = []
        reg = _registry(_make_ext("a", installed=False))
        install_with_deps(["a"], reg, progress=messages.append)
        assert any("a" in m.lower() or "A" in m for m in messages)

    def test_progress_called_for_skipped(self) -> None:
        messages: list[str] = []
        reg = _registry(_make_ext("a", installed=True))
        install_with_deps(["a"], reg, progress=messages.append)
        assert any("skip" in m.lower() for m in messages)

    def test_propagates_dependency_errors(self) -> None:
        reg = _registry(_make_ext("a", requires=["missing"]))
        with pytest.raises(MissingDependencyError):
            install_with_deps(["a"], reg)

    def test_empty_request_returns_empty(self) -> None:
        reg = _registry(_make_ext("a"))
        result = install_with_deps([], reg)
        assert result == []


# ── Real registry smoke test ──────────────────────────────────────────────────

class TestRealRegistry:
    def test_resolve_gapps_no_error(self) -> None:
        from waydroid_toolkit.modules.extensions.registry import REGISTRY
        # gapps has no requires in the real registry — should resolve cleanly
        order = resolve(["gapps"], REGISTRY)
        assert "gapps" in order

    def test_resolve_all_extensions_no_cycle(self) -> None:
        from waydroid_toolkit.modules.extensions.registry import REGISTRY
        # Exclude one side of each known conflict pair:
        #   gapps ↔ microg, libhoudini ↔ libndk
        safe_set = [k for k in REGISTRY if k not in ("microg", "libndk")]
        order = resolve(safe_set, REGISTRY)
        assert set(order) == set(safe_set)

    def test_gapps_microg_conflict(self) -> None:
        from waydroid_toolkit.modules.extensions.registry import REGISTRY
        with pytest.raises(ConflictError):
            resolve(["gapps", "microg"], REGISTRY)
