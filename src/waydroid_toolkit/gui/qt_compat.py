"""Qt binding compatibility shim.

Tries PySide6 first, falls back to PyQt6. Application code imports from
this module rather than directly from PySide6 or PyQt6, so either binding
works at runtime.

Usage:
    from waydroid_toolkit.gui.qt_compat import (
        QtCore, QtGui, QtWidgets, QtQml, QtWebEngineQuick,
        Signal, Slot, Property, QT_BINDING,
    )

QT_BINDING is either "PySide6" or "PyQt6" — useful for conditional code
where the two APIs differ (e.g. exec() vs exec_()).
"""

from __future__ import annotations

import importlib

# ── Binding detection ─────────────────────────────────────────────────────────

def _try_import(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


if _try_import("PySide6"):
    QT_BINDING = "PySide6"
elif _try_import("PyQt6"):
    QT_BINDING = "PyQt6"
else:
    raise ImportError(
        "No Qt binding found. Install one of:\n"
        "  pip install 'waydroid-toolkit[gui]'        # PySide6\n"
        "  pip install 'waydroid-toolkit[gui-pyqt]'   # PyQt6"
    )

# ── Module imports ────────────────────────────────────────────────────────────

if QT_BINDING == "PySide6":
    from PySide6 import QtCore, QtGui, QtQml, QtWidgets
    from PySide6.QtCore import Property, Signal, Slot
    try:
        from PySide6 import QtWebEngineQuick
        HAS_WEBENGINE = True
    except ImportError:
        QtWebEngineQuick = None  # type: ignore[assignment]
        HAS_WEBENGINE = False

else:  # PyQt6
    from PyQt6 import QtCore, QtGui, QtQml, QtWidgets
    from PyQt6.QtCore import pyqtProperty as Property
    from PyQt6.QtCore import pyqtSignal as Signal
    from PyQt6.QtCore import pyqtSlot as Slot
    try:
        from PyQt6 import QtWebEngineQuick
        HAS_WEBENGINE = True
    except ImportError:
        QtWebEngineQuick = None  # type: ignore[assignment]
        HAS_WEBENGINE = False


# ── Unified exec() helper ─────────────────────────────────────────────────────
# PySide6 uses app.exec(); PyQt6 uses app.exec() too (since PyQt6 6.0).
# Both are consistent — no shim needed. Kept here for documentation.

def qt_exec(app: QtWidgets.QApplication) -> int:  # type: ignore[name-defined]
    """Run the Qt event loop and return the exit code."""
    return app.exec()


# ── Version info ──────────────────────────────────────────────────────────────

def qt_version() -> str:
    """Return the Qt runtime version string."""
    return QtCore.qVersion()  # type: ignore[attr-defined]


def binding_version() -> str:
    """Return the binding package version string."""
    if QT_BINDING == "PySide6":
        import PySide6
        return PySide6.__version__
    else:
        import PyQt6.QtCore
        return PyQt6.QtCore.PYQT_VERSION_STR


__all__ = [
    "QT_BINDING",
    "HAS_WEBENGINE",
    "QtCore",
    "QtGui",
    "QtQml",
    "QtWidgets",
    "QtWebEngineQuick",
    "Signal",
    "Slot",
    "Property",
    "qt_exec",
    "qt_version",
    "binding_version",
]
