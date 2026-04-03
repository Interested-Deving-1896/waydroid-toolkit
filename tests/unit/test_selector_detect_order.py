"""Tests for selector.detect() Incus-first preference (change A)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.core.container.selector import detect


def _make_backend(available: bool, backend_type_value: str) -> MagicMock:
    b = MagicMock()
    b.is_available.return_value = available
    b.backend_type.value = backend_type_value
    return b


class TestDetectOrder:
    def test_prefers_incus_when_both_available(self) -> None:
        """detect() returns Incus when both Incus and LXC are available."""
        incus_instance = _make_backend(True, "incus")
        lxc_instance = _make_backend(True, "lxc")

        with patch(
            "waydroid_toolkit.core.container.selector.IncusBackend",
            return_value=incus_instance,
        ):
            with patch(
                "waydroid_toolkit.core.container.selector.LxcBackend",
                return_value=lxc_instance,
            ):
                result = detect()

        assert result is incus_instance
        lxc_instance.is_available.assert_not_called()

    def test_falls_back_to_lxc_when_incus_unavailable(self, capsys: pytest.CaptureFixture[str]) -> None:
        """detect() returns LXC and prints a warning when Incus is absent."""
        incus_instance = _make_backend(False, "incus")
        lxc_instance = _make_backend(True, "lxc")

        with patch(
            "waydroid_toolkit.core.container.selector.IncusBackend",
            return_value=incus_instance,
        ):
            with patch(
                "waydroid_toolkit.core.container.selector.LxcBackend",
                return_value=lxc_instance,
            ):
                result = detect()

        assert result is lxc_instance
        captured = capsys.readouterr()
        assert "Incus not found" in captured.err
        assert "wdt backend switch incus" in captured.err

    def test_raises_when_neither_available(self) -> None:
        """detect() raises RuntimeError when no backend binary is found."""
        incus_instance = _make_backend(False, "incus")
        lxc_instance = _make_backend(False, "lxc")

        with patch(
            "waydroid_toolkit.core.container.selector.IncusBackend",
            return_value=incus_instance,
        ):
            with patch(
                "waydroid_toolkit.core.container.selector.LxcBackend",
                return_value=lxc_instance,
            ):
                with pytest.raises(RuntimeError, match="No container backend found"):
                    detect()

    def test_incus_only_no_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """No warning is printed when Incus is selected."""
        incus_instance = _make_backend(True, "incus")
        lxc_instance = _make_backend(True, "lxc")

        with patch(
            "waydroid_toolkit.core.container.selector.IncusBackend",
            return_value=incus_instance,
        ):
            with patch(
                "waydroid_toolkit.core.container.selector.LxcBackend",
                return_value=lxc_instance,
            ):
                detect()

        captured = capsys.readouterr()
        assert captured.err == ""
