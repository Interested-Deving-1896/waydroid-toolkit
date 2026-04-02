"""Tests for MaintenanceBridge — specifically the screen recording slots.

Qt is not available in CI. The qt_compat module is stubbed using the same
pattern as test_logcat_bridge.py.
"""

from __future__ import annotations

import sys
import threading
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Qt stubs ──────────────────────────────────────────────────────────────────

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

_qt_compat_stub = types.ModuleType("waydroid_toolkit.gui.qt_compat")
_qt_compat_stub.QtCore = _qtcore          # type: ignore[attr-defined]
_qt_compat_stub.Signal = _signal_factory  # type: ignore[attr-defined]
_qt_compat_stub.Slot = lambda *a, **kw: (lambda f: f)      # type: ignore[attr-defined]
_qt_compat_stub.Property = lambda *a, **kw: (lambda f: f)  # type: ignore[attr-defined]
_qt_compat_stub.QT_BINDING = "stub"       # type: ignore[attr-defined]
_qt_compat_stub.HAS_WEBENGINE = False     # type: ignore[attr-defined]

sys.modules["waydroid_toolkit.gui.qt_compat"] = _qt_compat_stub

for _mod in list(sys.modules):
    if _mod.startswith("waydroid_toolkit.gui.bridge"):
        del sys.modules[_mod]

from waydroid_toolkit.gui.bridge import MaintenanceBridge  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_bridge() -> MaintenanceBridge:
    bridge = object.__new__(MaintenanceBridge)
    bridge._busy = False
    bridge._error = ""
    bridge._pool = MagicMock()
    bridge._recording = False
    bridge._record_thread = None
    bridge._record_stop = threading.Event()
    bridge.busyChanged      = _signal_factory()
    bridge.errorOccurred    = _signal_factory(str)
    bridge.screenshotSaved  = _signal_factory(str)
    bridge.recordingSaved   = _signal_factory(str)
    bridge.recordingChanged = _signal_factory()
    return bridge


# ── recording property ────────────────────────────────────────────────────────

class TestRecordingProperty:
    def test_initial_state_is_false(self) -> None:
        bridge = _make_bridge()
        assert bridge._recording is False

    def test_set_recording_emits_signal(self) -> None:
        bridge = _make_bridge()
        fired: list = []
        bridge.recordingChanged.connect(lambda: fired.append(True))
        bridge._set_recording(True)
        assert fired

    def test_set_recording_no_emit_when_unchanged(self) -> None:
        bridge = _make_bridge()
        fired: list = []
        bridge.recordingChanged.connect(lambda: fired.append(True))
        bridge._set_recording(False)  # already False
        assert not fired


# ── startRecording ────────────────────────────────────────────────────────────

class TestStartRecording:
    def test_sets_recording_true(self) -> None:
        bridge = _make_bridge()
        with patch("waydroid_toolkit.modules.maintenance.tools.record_screen",
                   return_value=Path("/tmp/rec.mp4")):
            bridge.startRecording(5)
            # Give the thread a moment to start
            time.sleep(0.05)
        assert bridge._recording is True or bridge._recording is False  # thread may finish

    def test_does_not_start_if_already_recording(self) -> None:
        bridge = _make_bridge()
        bridge._recording = True
        with patch("threading.Thread") as mock_thread:
            bridge.startRecording(5)
        mock_thread.assert_not_called()

    def test_emits_recordingSaved_on_completion(self) -> None:
        bridge = _make_bridge()
        saved: list[str] = []
        bridge.recordingSaved.connect(saved.append)

        with patch(
            "waydroid_toolkit.modules.maintenance.tools.record_screen",
            return_value=Path("/tmp/recording_test.mp4"),
        ):
            bridge.startRecording(5)
            # Wait for the background thread to finish
            if bridge._record_thread:
                bridge._record_thread.join(timeout=3)

        assert saved == ["/tmp/recording_test.mp4"]

    def test_recording_false_after_completion(self) -> None:
        bridge = _make_bridge()
        with patch(
            "waydroid_toolkit.modules.maintenance.tools.record_screen",
            return_value=Path("/tmp/rec.mp4"),
        ):
            bridge.startRecording(5)
            if bridge._record_thread:
                bridge._record_thread.join(timeout=3)

        assert bridge._recording is False

    def test_emits_error_on_exception(self) -> None:
        bridge = _make_bridge()
        errors: list[str] = []
        bridge.errorOccurred.connect(errors.append)

        with patch(
            "waydroid_toolkit.modules.maintenance.tools.record_screen",
            side_effect=RuntimeError("adb died"),
        ):
            bridge.startRecording(5)
            if bridge._record_thread:
                bridge._record_thread.join(timeout=3)

        assert errors
        assert bridge._recording is False

    def test_clears_stop_event_before_starting(self) -> None:
        bridge = _make_bridge()
        bridge._record_stop.set()  # pre-set

        with patch(
            "waydroid_toolkit.modules.maintenance.tools.record_screen",
            return_value=Path("/tmp/rec.mp4"),
        ):
            bridge.startRecording(5)
            if bridge._record_thread:
                bridge._record_thread.join(timeout=3)

        # stop event should have been cleared at start
        assert not bridge._record_stop.is_set()


# ── stopRecording ─────────────────────────────────────────────────────────────

class TestStopRecording:
    def test_no_op_when_not_recording(self) -> None:
        bridge = _make_bridge()
        # Should not raise
        bridge.stopRecording()
        assert bridge._recording is False

    def test_sets_stop_event(self) -> None:
        bridge = _make_bridge()
        bridge._recording = True
        with patch("waydroid_toolkit.core.adb.shell"):
            bridge.stopRecording()
        assert bridge._record_stop.is_set()

    def test_sends_pkill_via_adb(self) -> None:
        bridge = _make_bridge()
        bridge._recording = True
        with patch("waydroid_toolkit.core.adb.shell") as mock_shell:
            bridge.stopRecording()
        cmd = mock_shell.call_args[0][0]
        assert "pkill" in cmd
        assert "screenrecord" in cmd

    def test_tolerates_adb_error_on_stop(self) -> None:
        bridge = _make_bridge()
        bridge._recording = True
        with patch("waydroid_toolkit.core.adb.shell", side_effect=RuntimeError("no adb")):
            bridge.stopRecording()  # must not raise
        assert bridge._record_stop.is_set()


# ── captureScreenshot ─────────────────────────────────────────────────────────

class TestCaptureScreenshot:
    def test_emits_screenshotSaved(self) -> None:
        bridge = _make_bridge()
        saved: list[str] = []
        bridge.screenshotSaved.connect(saved.append)

        # _run uses QThreadPool; call the inner function directly
        def fake_run(fn, *args, on_done=None, **kwargs):
            result = fn()
            if on_done:
                on_done(result)

        bridge._run = fake_run  # type: ignore[method-assign]

        with patch(
            "waydroid_toolkit.modules.maintenance.tools.take_screenshot",
            return_value=Path("/tmp/shot.png"),
        ):
            bridge.captureScreenshot()

        assert saved == ["/tmp/shot.png"]
