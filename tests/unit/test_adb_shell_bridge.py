"""Tests for AdbShellBridge.

Qt is not available in CI. The qt_compat module is stubbed out so that
bridge.py can be imported and the AdbShellBridge logic tested in isolation.
"""

from __future__ import annotations

import subprocess
import sys
import types
from unittest.mock import MagicMock, patch

# ── Qt stubs (same pattern as test_gui_toast.py) ──────────────────────────────

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


class _FakeQRunnable:
    pass


class _FakeQThreadPool:
    @staticmethod
    def globalInstance():
        return _FakeQThreadPool()

    def start(self, r):
        pass


_qtcore = types.SimpleNamespace(
    QObject=_FakeQObject,
    QRunnable=_FakeQRunnable,
    QThreadPool=_FakeQThreadPool,
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

from waydroid_toolkit.gui.bridge import AdbShellBridge  # noqa: E402

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_bridge() -> AdbShellBridge:
    """Return an AdbShellBridge with live FakeSignals attached."""
    bridge = object.__new__(AdbShellBridge)
    bridge._proc = None
    bridge._reader = None
    bridge._connected = False
    bridge.lineReceived    = _signal_factory(str)
    bridge.connectedChanged = _signal_factory()
    bridge.sessionEnded    = _signal_factory(int)
    bridge.errorOccurred   = _signal_factory(str)
    return bridge


def _fake_popen(lines: list[str], returncode: int = 0) -> MagicMock:
    """Return a mock Popen whose stdout yields *lines*."""
    proc = MagicMock(spec=subprocess.Popen)
    proc.stdout = iter(lines)
    proc.stdin = MagicMock()
    proc.returncode = returncode
    proc.wait.return_value = returncode
    return proc


# ── connectShell ──────────────────────────────────────────────────────────────

class TestConnectShell:
    def test_sets_connected_true(self) -> None:
        bridge = _make_bridge()
        # Patch Thread so the reader never runs and races the assertion
        with patch("subprocess.run"), \
             patch("subprocess.Popen", return_value=_fake_popen([])), \
             patch("threading.Thread"):
            bridge.connectShell()
        assert bridge._connected is True

    def test_emits_connectedChanged(self) -> None:
        bridge = _make_bridge()
        fired: list = []
        bridge.connectedChanged.connect(lambda: fired.append(True))
        with patch("subprocess.run"), \
             patch("subprocess.Popen", return_value=_fake_popen([])), \
             patch("threading.Thread"):
            bridge.connectShell()
        assert fired

    def test_noop_when_already_connected(self) -> None:
        bridge = _make_bridge()
        bridge._proc = MagicMock()  # simulate existing session
        bridge._connected = True
        with patch("subprocess.Popen") as mock_popen:
            bridge.connectShell()
        mock_popen.assert_not_called()

    def test_emits_error_when_adb_missing(self) -> None:
        bridge = _make_bridge()
        errors: list[str] = []
        bridge.errorOccurred.connect(errors.append)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            bridge.connectShell()
        assert any("adb not found" in e for e in errors)
        assert bridge._connected is False


# ── disconnectShell ───────────────────────────────────────────────────────────

class TestDisconnectShell:
    def test_sets_connected_false(self) -> None:
        bridge = _make_bridge()
        proc = _fake_popen([])
        bridge._proc = proc
        bridge._connected = True
        bridge.disconnectShell()
        assert bridge._connected is False

    def test_terminates_process(self) -> None:
        bridge = _make_bridge()
        proc = _fake_popen([])
        bridge._proc = proc
        bridge._connected = True
        bridge.disconnectShell()
        proc.terminate.assert_called_once()

    def test_noop_when_not_connected(self) -> None:
        bridge = _make_bridge()
        bridge.disconnectShell()  # must not raise


# ── sendLine ──────────────────────────────────────────────────────────────────

class TestSendLine:
    def test_writes_to_stdin(self) -> None:
        bridge = _make_bridge()
        proc = _fake_popen([])
        bridge._proc = proc
        bridge._connected = True
        bridge.sendLine("ls /")
        proc.stdin.write.assert_called_once_with("ls /\n")
        proc.stdin.flush.assert_called_once()

    def test_emits_error_when_not_connected(self) -> None:
        bridge = _make_bridge()
        errors: list[str] = []
        bridge.errorOccurred.connect(errors.append)
        bridge.sendLine("ls /")
        assert errors

    def test_handles_broken_pipe(self) -> None:
        bridge = _make_bridge()
        proc = _fake_popen([])
        proc.stdin.write.side_effect = BrokenPipeError
        bridge._proc = proc
        bridge._connected = True
        # Should not raise; should mark disconnected
        bridge.sendLine("ls /")
        assert bridge._connected is False


# ── runCommand ────────────────────────────────────────────────────────────────

class TestRunCommand:
    def test_returns_stdout(self) -> None:
        bridge = _make_bridge()
        mock_result = MagicMock()
        mock_result.stdout = "hello\n"
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            out = bridge.runCommand("echo hello")
        assert out == "hello"

    def test_returns_error_when_adb_missing(self) -> None:
        bridge = _make_bridge()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            out = bridge.runCommand("ls")
        assert "adb not found" in out

    def test_returns_error_on_timeout(self) -> None:
        bridge = _make_bridge()
        with patch("subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="adb", timeout=30)):
            out = bridge.runCommand("sleep 999")
        assert "timed out" in out


# ── _read_loop ────────────────────────────────────────────────────────────────

class TestReadLoop:
    def test_emits_lines(self) -> None:
        bridge = _make_bridge()
        received: list[str] = []
        bridge.lineReceived.connect(received.append)

        proc = _fake_popen(["line1\n", "line2\n"])
        bridge._proc = proc
        bridge._connected = True

        # Run the read loop synchronously (it's normally in a thread)
        bridge._read_loop()

        assert received == ["line1", "line2"]

    def test_emits_sessionEnded_on_exit(self) -> None:
        bridge = _make_bridge()
        ended: list[int] = []
        bridge.sessionEnded.connect(ended.append)

        proc = _fake_popen([], returncode=1)
        bridge._proc = proc
        bridge._connected = True

        bridge._read_loop()

        assert ended == [1]

    def test_no_sessionEnded_after_explicit_disconnect(self) -> None:
        """If disconnectShell() clears _proc before the loop exits, no signal."""
        bridge = _make_bridge()
        ended: list[int] = []
        bridge.sessionEnded.connect(ended.append)

        proc = _fake_popen([])
        bridge._proc = proc
        bridge._connected = True

        # Simulate disconnectShell() having cleared _proc before loop exits
        bridge._proc = None
        bridge._connected = False

        bridge._read_loop()

        assert ended == []
