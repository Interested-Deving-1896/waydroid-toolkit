"""Tests for WdtPage toast notification helpers.

Qt is not available in CI. This module stubs the entire qt_compat module
and the Qt classes it re-exports so that pages.base can be imported and
tested without a display server or Qt installation.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock  # noqa: F401

# ── Minimal Signal implementation ─────────────────────────────────────────────

class _FakeSignal:
    """Minimal Signal that supports connect/emit without Qt."""

    def __init__(self, *types_):
        self._types = types_
        self._slots: list = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *args):
        for slot in self._slots:
            slot(*args)

    def __call__(self, *types_):
        # Called as Signal(str, bool) at class-body time -> return new instance
        return _FakeSignal(*types_)


_signal_factory = _FakeSignal()


# ── Stub Qt classes used by pages/base.py ─────────────────────────────────────

class _FakeQObject:
    pass


class _FakeQRunnable:
    def run(self):
        pass


class _FakeQThreadPool:
    @staticmethod
    def globalInstance():
        return _FakeQThreadPool()

    def start(self, runnable):
        pass


class _FakeQWidget:
    def __init__(self, *a, **kw):
        pass


class _FakeQLabel:
    def __init__(self, *a, **kw):
        pass

    def font(self):
        return MagicMock()

    def setFont(self, f):
        pass

    def setWordWrap(self, v):
        pass

    def setStyleSheet(self, s):
        pass


class _FakeQVBoxLayout:
    def __init__(self, *a, **kw):
        pass

    def setContentsMargins(self, *a):
        pass

    def setSpacing(self, v):
        pass

    def addWidget(self, w):
        pass

    def addLayout(self, layout):
        pass

    def addStretch(self):
        pass


# ── Build fake QtCore / QtWidgets modules ─────────────────────────────────────

_qtcore = types.SimpleNamespace(
    QObject=_FakeQObject,
    QRunnable=_FakeQRunnable,
    QThreadPool=_FakeQThreadPool,
    Signal=_signal_factory,
    Slot=lambda *a, **kw: (lambda f: f),
    Property=lambda *a, **kw: (lambda f: f),
)

_qtwidgets = types.SimpleNamespace(
    QWidget=_FakeQWidget,
    QLabel=_FakeQLabel,
    QVBoxLayout=_FakeQVBoxLayout,
    QAbstractTableModel=MagicMock,
    QTableView=MagicMock,
    QHeaderView=MagicMock,
    QSizePolicy=MagicMock,
)


# ── Stub the qt_compat module entirely ───────────────────────────────────────

_qt_compat_stub = types.ModuleType("waydroid_toolkit.gui.qt_compat")
_qt_compat_stub.QtCore = _qtcore  # type: ignore[attr-defined]
_qt_compat_stub.QtWidgets = _qtwidgets  # type: ignore[attr-defined]
_qt_compat_stub.Signal = _signal_factory  # type: ignore[attr-defined]
_qt_compat_stub.Slot = lambda *a, **kw: (lambda f: f)  # type: ignore[attr-defined]
_qt_compat_stub.Property = lambda *a, **kw: (lambda f: f)  # type: ignore[attr-defined]
_qt_compat_stub.QT_BINDING = "stub"  # type: ignore[attr-defined]
_qt_compat_stub.HAS_WEBENGINE = False  # type: ignore[attr-defined]

# Inject before any gui module is imported
sys.modules["waydroid_toolkit.gui.qt_compat"] = _qt_compat_stub

# Remove any previously cached gui imports
for _mod in list(sys.modules):
    if _mod.startswith("waydroid_toolkit.gui.pages"):
        del sys.modules[_mod]

from waydroid_toolkit.gui.pages.base import WdtPage  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_page() -> WdtPage:
    """Return a WdtPage instance bypassing Qt __init__."""
    page = object.__new__(WdtPage)
    # Attach a live FakeSignal so connect/emit work
    page.toastRequested = _signal_factory(str, bool)
    return page


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestShowToast:
    def test_emits_signal_with_message(self) -> None:
        page = _make_page()
        received: list = []
        page.toastRequested.connect(lambda msg, err: received.append((msg, err)))
        page.show_toast("hello")
        assert received == [("hello", False)]

    def test_error_flag_false_by_default(self) -> None:
        page = _make_page()
        received: list = []
        page.toastRequested.connect(lambda msg, err: received.append(err))
        page.show_toast("msg")
        assert received == [False]

    def test_error_flag_true_when_requested(self) -> None:
        page = _make_page()
        received: list = []
        page.toastRequested.connect(lambda msg, err: received.append(err))
        page.show_toast("oops", error=True)
        assert received == [True]

    def test_multiple_slots_all_called(self) -> None:
        page = _make_page()
        a: list = []
        b: list = []
        page.toastRequested.connect(lambda msg, err: a.append(msg))
        page.toastRequested.connect(lambda msg, err: b.append(msg))
        page.show_toast("broadcast")
        assert a == ["broadcast"]
        assert b == ["broadcast"]

    def test_no_slots_does_not_raise(self) -> None:
        page = _make_page()
        page.show_toast("silent")  # must not raise
