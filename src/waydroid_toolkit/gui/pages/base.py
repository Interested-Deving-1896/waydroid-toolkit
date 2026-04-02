"""Base Qt Widget page.

All data-heavy pages that use QTableView/QListView inherit from WdtPage.
Provides:
  - title and subtitle labels
  - content_layout (QVBoxLayout) for subclasses to populate
  - show_toast(msg, error) signal forwarded to the parent window
  - run_async(fn, on_done) for background work via QThreadPool
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from waydroid_toolkit.gui.qt_compat import QtCore, QtWidgets, Signal


class _Worker(QtCore.QRunnable):
    class Signals(QtCore.QObject):
        finished = Signal(object)
        error    = Signal(str)

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn      = fn
        self.args    = args
        self.kwargs  = kwargs
        self.signals = _Worker.Signals()

    def run(self) -> None:
        try:
            self.signals.finished.emit(self.fn(*self.args, **self.kwargs))
        except Exception:  # noqa: BLE001
            self.signals.error.emit(traceback.format_exc())


class WdtPage(QtWidgets.QWidget):
    """Base class for all Qt Widget pages."""

    toastRequested = Signal(str, bool)  # (message, is_error)

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pool = QtCore.QThreadPool.globalInstance()
        self._build_ui(title, subtitle)

    def _build_ui(self, title: str, subtitle: str) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title_lbl = QtWidgets.QLabel(title)
        f = title_lbl.font()
        f.setPixelSize(22)
        f.setBold(True)
        title_lbl.setFont(f)
        root.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QtWidgets.QLabel(subtitle)
            sub_lbl.setWordWrap(True)
            sub_lbl.setStyleSheet("color: grey;")
            root.addWidget(sub_lbl)

        self.content_layout = QtWidgets.QVBoxLayout()
        self.content_layout.setSpacing(12)
        root.addLayout(self.content_layout)
        root.addStretch()

    def show_toast(self, message: str, error: bool = False) -> None:
        self.toastRequested.emit(message, error)

    def run_async(
        self,
        fn: Callable,
        *args: Any,
        on_done: Callable[[Any], None] | None = None,
        **kwargs: Any,
    ) -> None:
        worker = _Worker(fn, *args, **kwargs)
        if on_done:
            worker.signals.finished.connect(on_done)
        worker.signals.error.connect(lambda msg: self.show_toast(msg, error=True))
        self._pool.start(worker)
