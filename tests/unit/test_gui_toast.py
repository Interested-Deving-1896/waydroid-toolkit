"""Tests for BasePage toast notification helpers.

gi (PyGObject) is not available in CI. This module stubs the entire gi
import chain before importing any GUI code, so the toast logic can be
tested without a display server or GTK installation.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def _install_gi_stubs() -> None:
    """Insert minimal gi stubs into sys.modules so GUI imports succeed."""
    if "gi" in sys.modules:
        return

    gi_mod = types.ModuleType("gi")
    gi_mod.require_version = lambda *a: None  # type: ignore[attr-defined]

    # Build a fake Adw.Toast that tracks title and timeout
    class FakeToast:
        def __init__(self, title: str = "", timeout: int = 3) -> None:
            self._title = title
            self._timeout = timeout

        def get_title(self) -> str:
            return self._title

        def get_timeout(self) -> int:
            return self._timeout

    class FakeToastOverlay:
        def __init__(self) -> None:
            self.toasts: list[FakeToast] = []

        def add_toast(self, toast: FakeToast) -> None:
            self.toasts.append(toast)

        def set_child(self, _child: object) -> None:
            pass

    adw_mod = types.ModuleType("gi.repository.Adw")
    adw_mod.Toast = FakeToast  # type: ignore[attr-defined]
    adw_mod.ToastOverlay = FakeToastOverlay  # type: ignore[attr-defined]
    adw_mod.Application = MagicMock  # type: ignore[attr-defined]
    adw_mod.ApplicationWindow = MagicMock  # type: ignore[attr-defined]
    adw_mod.HeaderBar = MagicMock  # type: ignore[attr-defined]
    adw_mod.NavigationSplitView = MagicMock  # type: ignore[attr-defined]
    adw_mod.NavigationPage = MagicMock  # type: ignore[attr-defined]
    adw_mod.ToolbarView = MagicMock  # type: ignore[attr-defined]
    adw_mod.WindowTitle = MagicMock  # type: ignore[attr-defined]
    adw_mod.PreferencesGroup = MagicMock  # type: ignore[attr-defined]
    adw_mod.ActionRow = MagicMock  # type: ignore[attr-defined]

    gtk_mod = types.ModuleType("gi.repository.Gtk")
    gtk_mod.Box = MagicMock  # type: ignore[attr-defined]
    gtk_mod.Button = MagicMock  # type: ignore[attr-defined]
    gtk_mod.Label = MagicMock  # type: ignore[attr-defined]
    gtk_mod.ListBox = MagicMock  # type: ignore[attr-defined]
    gtk_mod.ListBoxRow = MagicMock  # type: ignore[attr-defined]
    gtk_mod.ScrolledWindow = MagicMock  # type: ignore[attr-defined]
    gtk_mod.Stack = MagicMock  # type: ignore[attr-defined]
    gtk_mod.Widget = MagicMock  # type: ignore[attr-defined]
    gtk_mod.Orientation = MagicMock  # type: ignore[attr-defined]
    gtk_mod.Align = MagicMock  # type: ignore[attr-defined]
    gtk_mod.PolicyType = MagicMock  # type: ignore[attr-defined]
    gtk_mod.SelectionMode = MagicMock  # type: ignore[attr-defined]

    repo_mod = types.ModuleType("gi.repository")
    repo_mod.Adw = adw_mod  # type: ignore[attr-defined]
    repo_mod.Gtk = gtk_mod  # type: ignore[attr-defined]
    repo_mod.Gio = MagicMock()  # type: ignore[attr-defined]

    gi_mod.repository = repo_mod  # type: ignore[attr-defined]

    sys.modules["gi"] = gi_mod
    sys.modules["gi.repository"] = repo_mod
    sys.modules["gi.repository.Adw"] = adw_mod
    sys.modules["gi.repository.Gtk"] = gtk_mod
    sys.modules["gi.repository.Gio"] = MagicMock()


_install_gi_stubs()

# Now safe to import GUI modules
import waydroid_toolkit.gui.pages.base as base_module  # noqa: E402
from waydroid_toolkit.gui.pages.base import BasePage, register_toast_overlay  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_page() -> BasePage:
    """Return a BasePage instance bypassing GTK __init__."""
    page = object.__new__(BasePage)
    return page


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRegisterToastOverlay:
    def test_sets_module_variable(self) -> None:
        mock_overlay = MagicMock()
        register_toast_overlay(mock_overlay)
        assert base_module._toast_overlay is mock_overlay

    def test_can_be_overwritten(self) -> None:
        first = MagicMock()
        second = MagicMock()
        register_toast_overlay(first)
        register_toast_overlay(second)
        assert base_module._toast_overlay is second


class TestShowToast:
    def setup_method(self) -> None:
        self._saved = base_module._toast_overlay
        base_module._toast_overlay = None

    def teardown_method(self) -> None:
        base_module._toast_overlay = self._saved

    def test_noop_when_no_overlay_registered(self) -> None:
        page = _make_page()
        page._show_toast("hello")  # must not raise

    def test_calls_add_toast_on_overlay(self) -> None:
        mock_overlay = MagicMock()
        base_module._toast_overlay = mock_overlay
        page = _make_page()
        page._show_toast("hello")
        mock_overlay.add_toast.assert_called_once()

    def test_toast_carries_message(self) -> None:
        received: list = []
        mock_overlay = MagicMock()
        mock_overlay.add_toast.side_effect = received.append
        base_module._toast_overlay = mock_overlay
        page = _make_page()
        page._show_toast("my message")
        assert received[0].get_title() == "my message"

    def test_default_timeout_is_3(self) -> None:
        received: list = []
        mock_overlay = MagicMock()
        mock_overlay.add_toast.side_effect = received.append
        base_module._toast_overlay = mock_overlay
        page = _make_page()
        page._show_toast("msg")
        assert received[0].get_timeout() == 3

    def test_custom_timeout_respected(self) -> None:
        received: list = []
        mock_overlay = MagicMock()
        mock_overlay.add_toast.side_effect = received.append
        base_module._toast_overlay = mock_overlay
        page = _make_page()
        page._show_toast("msg", timeout=10)
        assert received[0].get_timeout() == 10


class TestShowError:
    def setup_method(self) -> None:
        self._saved = base_module._toast_overlay
        base_module._toast_overlay = None

    def teardown_method(self) -> None:
        base_module._toast_overlay = self._saved

    def test_prefixes_error_label(self) -> None:
        received: list = []
        mock_overlay = MagicMock()
        mock_overlay.add_toast.side_effect = received.append
        base_module._toast_overlay = mock_overlay
        page = _make_page()
        page._show_error("something went wrong")
        title = received[0].get_title()
        assert title.startswith("Error:")
        assert "something went wrong" in title

    def test_uses_timeout_5(self) -> None:
        received: list = []
        mock_overlay = MagicMock()
        mock_overlay.add_toast.side_effect = received.append
        base_module._toast_overlay = mock_overlay
        page = _make_page()
        page._show_error("oops")
        assert received[0].get_timeout() == 5

    def test_noop_when_no_overlay(self) -> None:
        page = _make_page()
        page._show_error("oops")  # must not raise
