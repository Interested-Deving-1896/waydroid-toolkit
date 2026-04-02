"""Tests for LogcatBridge.

Qt is not available in CI. The qt_compat module is stubbed so that
bridge.py can be imported and LogcatBridge logic tested in isolation.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

# ── Qt stubs (same pattern as test_adb_shell_bridge.py) ──────────────────────

class _FakeSignal:
    def __init__(self, *types_):
        self._slots: list = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *args):
        for slot in self._slots:
            slot(*args)

    def __call__(self, *types_):
        return _FakeSignal(*types_)


_signal_factory = _FakeSignal()


class _FakeQObject:
    def __init__(self, parent=None):
        pass


_qtcore = types.SimpleNamespace(
    QObject=_FakeQObject,
    QRunnable=MagicMock,
    QThreadPool=MagicMock,
    Signal=_signal_factory,
    Slot=lambda *a, **kw: (lambda f: f),
    Property=lambda *a, **kw: (lambda f: f),
)
_qtwidgets = types.SimpleNamespace(
    QWidget=MagicMock,
    QLabel=MagicMock,
    QVBoxLayout=MagicMock,
    QAbstractTableModel=MagicMock,
    QTableView=MagicMock,
    QHeaderView=MagicMock,
    QSizePolicy=MagicMock,
)

_qt_compat_stub = types.ModuleType("waydroid_toolkit.gui.qt_compat")
_qt_compat_stub.QtCore = _qtcore  # type: ignore[attr-defined]
_qt_compat_stub.QtWidgets = _qtwidgets  # type: ignore[attr-defined]
_qt_compat_stub.Signal = _signal_factory  # type: ignore[attr-defined]
_qt_compat_stub.Slot = lambda *a, **kw: (lambda f: f)  # type: ignore[attr-defined]
_qt_compat_stub.Property = lambda *a, **kw: (lambda f: f)  # type: ignore[attr-defined]
_qt_compat_stub.QT_BINDING = "stub"  # type: ignore[attr-defined]
_qt_compat_stub.HAS_WEBENGINE = False  # type: ignore[attr-defined]

sys.modules["waydroid_toolkit.gui.qt_compat"] = _qt_compat_stub

for _mod in list(sys.modules):
    if _mod.startswith("waydroid_toolkit.gui.bridge"):
        del sys.modules[_mod]

from waydroid_toolkit.gui.bridge import LogcatBridge  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_bridge() -> LogcatBridge:
    bridge = object.__new__(LogcatBridge)
    import threading
    bridge._streaming = False
    bridge._thread = None
    bridge._stop_event = threading.Event()
    bridge._tag = ""
    bridge._level = ""
    bridge.lineReceived     = _signal_factory(str)
    bridge.streamingChanged = _signal_factory()
    bridge.errorOccurred    = _signal_factory(str)
    return bridge


# ── start / stop ──────────────────────────────────────────────────────────────

class TestStartStop:
    def test_start_sets_streaming_true(self) -> None:
        bridge = _make_bridge()
        with patch("threading.Thread"):
            bridge.start()
        assert bridge._streaming is True

    def test_stop_sets_streaming_false(self) -> None:
        bridge = _make_bridge()
        with patch("threading.Thread"):
            bridge.start()
        bridge.stop()
        assert bridge._streaming is False

    def test_stop_sets_stop_event(self) -> None:
        bridge = _make_bridge()
        bridge.stop()
        assert bridge._stop_event.is_set()

    def test_start_emits_streamingChanged(self) -> None:
        bridge = _make_bridge()
        fired: list = []
        bridge.streamingChanged.connect(lambda: fired.append(True))
        with patch("threading.Thread"):
            bridge.start()
        assert fired

    def test_start_restarts_if_already_streaming(self) -> None:
        bridge = _make_bridge()
        with patch("threading.Thread") as mock_thread:
            bridge.start()
            bridge.start()
        # Thread constructor called twice
        assert mock_thread.call_count == 2


# ── setTag / setLevel ─────────────────────────────────────────────────────────

class TestFilters:
    def test_setTag_updates_tag(self) -> None:
        bridge = _make_bridge()
        bridge.setTag("MyApp")
        assert bridge._tag == "MyApp"

    def test_setTag_strips_whitespace(self) -> None:
        bridge = _make_bridge()
        bridge.setTag("  MyApp  ")
        assert bridge._tag == "MyApp"

    def test_setLevel_updates_level(self) -> None:
        bridge = _make_bridge()
        bridge.setLevel("W")
        assert bridge._level == "W"

    def test_setLevel_normalises_to_uppercase(self) -> None:
        bridge = _make_bridge()
        bridge.setLevel("e")
        assert bridge._level == "E"

    def test_setLevel_invalid_emits_error(self) -> None:
        bridge = _make_bridge()
        errors: list[str] = []
        bridge.errorOccurred.connect(errors.append)
        bridge.setLevel("X")
        assert errors
        assert bridge._level == ""  # unchanged

    def test_setTag_restarts_stream_when_streaming(self) -> None:
        bridge = _make_bridge()
        with patch("threading.Thread"):
            bridge.start()
        with patch.object(bridge, "start") as mock_start:
            bridge.setTag("foo")
        mock_start.assert_called_once()

    def test_setLevel_restarts_stream_when_streaming(self) -> None:
        bridge = _make_bridge()
        with patch("threading.Thread"):
            bridge.start()
        with patch.object(bridge, "start") as mock_start:
            bridge.setLevel("W")
        mock_start.assert_called_once()

    def test_setTag_does_not_restart_when_stopped(self) -> None:
        bridge = _make_bridge()
        with patch.object(bridge, "start") as mock_start:
            bridge.setTag("foo")
        mock_start.assert_not_called()


# ── _line_matches_level ───────────────────────────────────────────────────────

class TestLineMatchesLevel:
    # Standard logcat line: "01-01 00:00:00.000  123  456 W MyTag: message"
    def _line(self, level: str) -> str:
        return f"01-01 00:00:00.000  123  456 {level} MyTag: hello"

    def test_exact_level_matches(self) -> None:
        assert LogcatBridge._line_matches_level(self._line("W"), "W") is True

    def test_higher_level_matches(self) -> None:
        assert LogcatBridge._line_matches_level(self._line("E"), "W") is True

    def test_lower_level_does_not_match(self) -> None:
        assert LogcatBridge._line_matches_level(self._line("D"), "W") is False

    def test_unparseable_line_passes_through(self) -> None:
        assert LogcatBridge._line_matches_level("short", "E") is True

    def test_unknown_level_in_line_passes_through(self) -> None:
        assert LogcatBridge._line_matches_level(self._line("?"), "W") is True


# ── _stream_loop ──────────────────────────────────────────────────────────────

class TestStreamLoop:
    def test_emits_lines(self) -> None:
        bridge = _make_bridge()
        received: list[str] = []
        bridge.lineReceived.connect(received.append)

        with patch(
            "waydroid_toolkit.modules.maintenance.tools.stream_logcat",
            return_value=iter(["line one", "line two"]),
        ):
            bridge._stream_loop()

        assert received == ["line one", "line two"]

    def test_stops_on_stop_event(self) -> None:
        bridge = _make_bridge()
        received: list[str] = []
        bridge.lineReceived.connect(received.append)
        bridge._stop_event.set()

        with patch(
            "waydroid_toolkit.modules.maintenance.tools.stream_logcat",
            return_value=iter(["line one", "line two"]),
        ):
            bridge._stream_loop()

        assert received == []

    def test_emits_error_on_exception(self) -> None:
        bridge = _make_bridge()
        errors: list[str] = []
        bridge.errorOccurred.connect(errors.append)

        def _bad_stream(**kw):
            raise RuntimeError("adb died")
            yield  # make it a generator

        with patch(
            "waydroid_toolkit.modules.maintenance.tools.stream_logcat",
            side_effect=_bad_stream,
        ):
            bridge._stream_loop()

        assert errors

    def test_sets_streaming_false_on_completion(self) -> None:
        bridge = _make_bridge()
        bridge._streaming = True

        with patch(
            "waydroid_toolkit.modules.maintenance.tools.stream_logcat",
            return_value=iter([]),
        ):
            bridge._stream_loop()

        assert bridge._streaming is False

    def test_level_filter_applied(self) -> None:
        bridge = _make_bridge()
        bridge._level = "W"
        received: list[str] = []
        bridge.lineReceived.connect(received.append)

        lines = [
            "01-01 00:00:00.000  1  1 D tag: debug msg",
            "01-01 00:00:00.000  1  1 W tag: warn msg",
            "01-01 00:00:00.000  1  1 E tag: error msg",
        ]
        with patch(
            "waydroid_toolkit.modules.maintenance.tools.stream_logcat",
            return_value=iter(lines),
        ):
            bridge._stream_loop()

        assert all("debug" not in line for line in received)
        assert any("warn" in line for line in received)
        assert any("error" in line for line in received)
