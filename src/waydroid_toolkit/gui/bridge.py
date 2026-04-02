"""Qt/QML bridge — exposes Python backend logic to QML via QObject properties.

Each page in the QML UI has a corresponding bridge object registered as a
QML context property. The bridge runs blocking operations in a QThreadPool
worker and emits signals back to the QML thread on completion.

Pattern:
    QML calls a bridge slot (e.g. bridge.refreshStatus())
    Bridge spawns a QRunnable worker
    Worker emits a signal with the result
    QML receives the signal and updates the UI

All bridge classes inherit WdtBridgeBase which provides:
    - busy: bool property (true while a worker is running)
    - error: str property (last error message)
    - errorOccurred(message: str) signal
    - _run(fn, *args) helper that runs fn in a thread and emits on error
"""

from __future__ import annotations

import subprocess
import threading
import traceback
from collections.abc import Callable
from typing import Any

from waydroid_toolkit.gui.qt_compat import Property, QtCore, Signal, Slot


class _Worker(QtCore.QRunnable):
    """Generic thread-pool worker."""

    class Signals(QtCore.QObject):
        finished = Signal(object)   # result
        error    = Signal(str)      # error message

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _Worker.Signals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception:  # noqa: BLE001
            self.signals.error.emit(traceback.format_exc())


class WdtBridgeBase(QtCore.QObject):
    """Base class for all bridge objects."""

    busyChanged     = Signal()
    errorOccurred   = Signal(str)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._busy  = False
        self._error = ""
        self._pool  = QtCore.QThreadPool.globalInstance()

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    def _run(
        self,
        fn: Callable,
        *args: Any,
        on_done: Callable[[Any], None] | None = None,
        **kwargs: Any,
    ) -> None:
        """Run fn(*args, **kwargs) in the thread pool.

        on_done is called on the Qt thread with the return value when fn
        completes successfully. Errors are emitted via errorOccurred.
        """
        self._set_busy(True)
        worker = _Worker(fn, *args, **kwargs)

        def _finished(result: Any) -> None:
            self._set_busy(False)
            if on_done:
                on_done(result)

        def _error(msg: str) -> None:
            self._set_busy(False)
            self._error = msg
            self.errorOccurred.emit(msg)

        worker.signals.finished.connect(_finished)
        worker.signals.error.connect(_error)
        self._pool.start(worker)


# ── Status bridge ─────────────────────────────────────────────────────────────

class StatusBridge(WdtBridgeBase):
    """Exposes Waydroid runtime status to QML."""

    statusChanged = Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._installed   = False
        self._initialized = False
        self._session     = "stopped"
        self._backend     = ""
        self._adb_ready   = False
        self._images_path = ""

    @Property(bool,   notify=statusChanged)
    def installed(self)   -> bool: return self._installed

    @Property(bool,   notify=statusChanged)
    def initialized(self) -> bool: return self._initialized

    @Property(str,    notify=statusChanged)
    def session(self)     -> str:  return self._session

    @Property(str,    notify=statusChanged)
    def backend(self)     -> str:  return self._backend

    @Property(bool,   notify=statusChanged)
    def adbReady(self)    -> bool: return self._adb_ready

    @Property(str,    notify=statusChanged)
    def imagesPath(self)  -> str:  return self._images_path

    @Slot()
    def refresh(self) -> None:
        def _fetch() -> dict:
            from waydroid_toolkit.core.adb import (
                is_available as adb_available,
            )
            from waydroid_toolkit.core.adb import (
                is_connected as adb_connected,
            )
            from waydroid_toolkit.core.waydroid import (
                get_session_state,
                is_initialized,
                is_installed,
            )
            try:
                from waydroid_toolkit.core.container import get_active
                backend = get_active().backend_type.value
            except Exception:
                backend = "unknown"
            return {
                "installed":   is_installed(),
                "initialized": is_initialized(),
                "session":     get_session_state().value,
                "backend":     backend,
                "adb_ready":   adb_available() and adb_connected(),
                "images_path": "/var/lib/waydroid/images",
            }

        def _apply(data: dict) -> None:
            self._installed   = data["installed"]
            self._initialized = data["initialized"]
            self._session     = data["session"]
            self._backend     = data["backend"]
            self._adb_ready   = data["adb_ready"]
            self._images_path = data["images_path"]
            self.statusChanged.emit()

        self._run(_fetch, on_done=_apply)


# ── Backend bridge ────────────────────────────────────────────────────────────

class BackendBridge(WdtBridgeBase):
    """Exposes container backend selection to QML."""

    backendsChanged = Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._backends: list[dict] = []
        self._active = ""

    @Property("QVariantList", notify=backendsChanged)
    def backends(self) -> list: return self._backends

    @Property(str, notify=backendsChanged)
    def active(self) -> str: return self._active

    @Slot()
    def refresh(self) -> None:
        def _fetch() -> dict:
            from waydroid_toolkit.core.container import get_active, list_available
            backends = [
                {"id": b.backend_type.value, "available": b.is_available()}
                for b in list_available()
            ]
            try:
                active = get_active().backend_type.value
            except Exception:
                active = ""
            return {"backends": backends, "active": active}

        def _apply(data: dict) -> None:
            self._backends = data["backends"]
            self._active   = data["active"]
            self.backendsChanged.emit()

        self._run(_fetch, on_done=_apply)

    @Slot(str)
    def setActive(self, backend_id: str) -> None:
        def _set() -> None:
            from waydroid_toolkit.core.container import BackendType, set_active
            set_active(BackendType(backend_id))

        self._run(_set)


# ── Extensions bridge ─────────────────────────────────────────────────────────

class ExtensionsBridge(WdtBridgeBase):
    """Exposes extension install/uninstall to QML."""

    extensionsChanged = Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._extensions: list[dict] = []

    @Property("QVariantList", notify=extensionsChanged)
    def extensions(self) -> list: return self._extensions

    @Slot()
    def refresh(self) -> None:
        def _fetch() -> list:
            from waydroid_toolkit.modules.extensions import list_all
            return [
                {
                    "id":          e.meta.id,
                    "name":        e.meta.name,
                    "description": e.meta.description,
                    "installed":   e.is_installed(),
                }
                for e in list_all()
            ]

        def _apply(data: list) -> None:
            self._extensions = data
            self.extensionsChanged.emit()

        self._run(_fetch, on_done=_apply)

    @Slot(str)
    def install(self, ext_id: str) -> None:
        def _do() -> None:
            from waydroid_toolkit.modules.extensions import get
            get(ext_id).install()
        self._run(_do, on_done=lambda _: self.refresh())

    @Slot(str)
    def uninstall(self, ext_id: str) -> None:
        def _do() -> None:
            from waydroid_toolkit.modules.extensions import get
            get(ext_id).uninstall()
        self._run(_do, on_done=lambda _: self.refresh())


# ── Packages bridge ───────────────────────────────────────────────────────────

class PackagesBridge(WdtBridgeBase):
    """Exposes APK install and F-Droid repo management to QML."""

    packagesChanged = Signal()
    reposChanged    = Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._packages: list[dict] = []
        self._repos:    list[dict] = []

    @Property("QVariantList", notify=packagesChanged)
    def packages(self) -> list: return self._packages

    @Property("QVariantList", notify=reposChanged)
    def repos(self) -> list: return self._repos

    @Slot(str)
    def search(self, query: str) -> None:
        def _do() -> list:
            from waydroid_toolkit.modules.packages.manager import search_repos
            return [
                {"name": p.get("name", ""), "packageName": p.get("packageName", "")}
                for p in search_repos(query)
            ]

        def _apply(data: list) -> None:
            self._packages = data
            self.packagesChanged.emit()

        self._run(_do, on_done=_apply)

    @Slot(str)
    def installApk(self, path: str) -> None:
        def _do() -> None:
            from pathlib import Path

            from waydroid_toolkit.core.adb import install_apk
            result = install_apk(Path(path))
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip())
        self._run(_do)

    @Slot()
    def refreshRepos(self) -> None:
        def _do() -> list:
            from waydroid_toolkit.modules.packages.manager import list_repos
            return [{"url": r.url, "name": r.name} for r in list_repos()]

        def _apply(data: list) -> None:
            self._repos = data
            self.reposChanged.emit()

        self._run(_do, on_done=_apply)

    @Slot(str)
    def addRepo(self, url: str) -> None:
        def _do() -> None:
            from waydroid_toolkit.modules.packages.manager import add_repo
            add_repo(url)
        self._run(_do, on_done=lambda _: self.refreshRepos())

    @Slot(str)
    def removeRepo(self, url: str) -> None:
        def _do() -> None:
            from waydroid_toolkit.modules.packages.manager import remove_repo
            remove_repo(url)
        self._run(_do, on_done=lambda _: self.refreshRepos())


# ── Performance bridge ────────────────────────────────────────────────────────

class PerformanceBridge(WdtBridgeBase):
    """Exposes performance tuning to QML."""

    profileChanged = Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._active_profile = ""

    @Property(str, notify=profileChanged)
    def activeProfile(self) -> str: return self._active_profile

    @Slot(str)
    def applyProfile(self, profile: str) -> None:
        def _do() -> str:
            from waydroid_toolkit.modules.performance.tuner import apply_profile
            apply_profile(profile)
            return profile
        self._run(_do, on_done=lambda p: self._set_profile(p))

    def _set_profile(self, profile: str) -> None:
        self._active_profile = profile
        self.profileChanged.emit()


# ── Backup bridge ─────────────────────────────────────────────────────────────

class BackupBridge(WdtBridgeBase):
    """Exposes backup/restore to QML."""

    backupDone    = Signal(str)   # path of created backup
    restoreDone   = Signal()

    @Slot(str)
    def backup(self, dest_dir: str) -> None:
        def _do() -> str:
            from pathlib import Path

            from waydroid_toolkit.modules.backup.backup import create_backup
            return str(create_backup(Path(dest_dir)))
        self._run(_do, on_done=lambda p: self.backupDone.emit(p))

    @Slot(str)
    def restore(self, archive_path: str) -> None:
        def _do() -> None:
            from pathlib import Path

            from waydroid_toolkit.modules.backup.backup import restore_backup
            restore_backup(Path(archive_path))
        self._run(_do, on_done=lambda _: self.restoreDone.emit())


# ── Images bridge ─────────────────────────────────────────────────────────────

class ImagesBridge(WdtBridgeBase):
    """Exposes image profile management and OTA updates to QML."""

    imagesChanged    = Signal()
    updateInfoReady  = Signal("QVariantList")   # list of {channel, current, latest, available}
    downloadProgress = Signal(str)              # progress messages during download
    downloadDone     = Signal(bool, str)        # (success, message)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._images: list[dict] = []

    @Property("QVariantList", notify=imagesChanged)
    def images(self) -> list:
        return self._images

    @Slot()
    def refresh(self) -> None:
        def _do() -> list:
            from waydroid_toolkit.modules.images.manager import (
                get_active_profile,
                scan_profiles,
            )
            active = get_active_profile()
            return [
                {"name": p.name, "active": active is not None and p.name == active}
                for p in scan_profiles()
            ]

        def _apply(data: list) -> None:
            self._images = data
            self.imagesChanged.emit()

        self._run(_do, on_done=_apply)

    @Slot(str)
    def activate(self, name: str) -> None:
        def _do() -> None:
            from waydroid_toolkit.modules.images.manager import (
                scan_profiles,
                switch_profile,
            )
            profiles = scan_profiles()
            match = next((p for p in profiles if p.name == name), None)
            if match is None:
                raise ValueError(f"Profile '{name}' not found.")
            switch_profile(match)
        self._run(_do, on_done=lambda _: self.refresh())

    @Slot()
    def checkUpdate(self) -> None:
        """Fetch both OTA channels and emit updateInfoReady with the results."""
        def _do() -> list:
            from waydroid_toolkit.modules.images.ota import check_updates
            sys_info, vendor_info = check_updates()
            result = []
            for info in (sys_info, vendor_info):
                result.append({
                    "channel":   info.channel,
                    "current":   str(info.current_datetime) if info.current_datetime else "none",
                    "latest":    str(info.latest.datetime) if info.latest else "unavailable",
                    "available": info.update_available,
                })
            return result

        self._run(_do, on_done=lambda data: self.updateInfoReady.emit(data))

    @Slot(str)
    def downloadImages(self, destDir: str) -> None:
        """Download available OTA images into *destDir*, emitting progress messages."""
        def _do() -> tuple:
            from pathlib import Path

            from waydroid_toolkit.modules.images.ota import download_updates
            sys_path, vendor_path = download_updates(
                dest_dir=Path(destDir),
                progress=lambda msg: self.downloadProgress.emit(msg),
            )
            downloaded = [p.name for p in (sys_path, vendor_path) if p is not None]
            if downloaded:
                return True, "Downloaded: " + ", ".join(downloaded)
            return True, "Images are already up to date."

        def _finish(result: tuple) -> None:
            ok, msg = result
            self.downloadDone.emit(ok, msg)

        self._run(_do, on_done=_finish)


# ── Maintenance bridge ────────────────────────────────────────────────────────

class MaintenanceBridge(WdtBridgeBase):
    """Exposes maintenance tools (logcat, screenshot, screen record, debloat) to QML."""

    logcatOutput     = Signal(str)
    screenshotSaved  = Signal(str)
    recordingSaved   = Signal(str)   # emitted with the saved file path when recording stops
    recordingChanged = Signal()      # emitted when _recording state toggles

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._recording = False
        self._record_thread: threading.Thread | None = None
        self._record_stop = threading.Event()

    @Property(bool, notify=recordingChanged)
    def recording(self) -> bool:
        return self._recording

    def _set_recording(self, value: bool) -> None:
        if self._recording != value:
            self._recording = value
            self.recordingChanged.emit()

    @Slot()
    def captureScreenshot(self) -> None:
        def _do() -> str:
            from waydroid_toolkit.modules.maintenance.tools import take_screenshot
            return str(take_screenshot())
        self._run(_do, on_done=lambda p: self.screenshotSaved.emit(p))

    @Slot(int)
    def startRecording(self, duration_seconds: int = 60) -> None:
        """Begin a screen recording of up to *duration_seconds* seconds.

        The recording runs in a background thread. Call ``stopRecording()``
        to end it early. ``recordingSaved(path)`` is emitted when done.
        """
        if self._recording:
            return
        self._record_stop.clear()
        self._set_recording(True)

        def _worker() -> None:
            try:
                from waydroid_toolkit.modules.maintenance.tools import record_screen
                path = record_screen(duration_seconds=duration_seconds)
                self.recordingSaved.emit(str(path))
            except Exception:  # noqa: BLE001
                self.errorOccurred.emit(traceback.format_exc())
            finally:
                self._set_recording(False)

        self._record_thread = threading.Thread(target=_worker, daemon=True)
        self._record_thread.start()

    @Slot()
    def stopRecording(self) -> None:
        """Signal the recording thread to stop early.

        The underlying ``adb screenrecord`` process will be killed via ADB
        so the partial recording is still saved.
        """
        if not self._recording:
            return
        self._record_stop.set()
        try:
            from waydroid_toolkit.core import adb
            adb.shell("pkill -f screenrecord")
        except Exception:  # noqa: BLE001
            pass

    @Slot()
    def startLogcat(self) -> None:
        def _do() -> str:
            from waydroid_toolkit.modules.maintenance.tools import get_logcat
            return get_logcat()
        self._run(_do, on_done=lambda out: self.logcatOutput.emit(out))


# ── File manager bridge ───────────────────────────────────────────────────────

class FileBridge(WdtBridgeBase):
    """Exposes push/pull file transfer to QML."""

    transferDone = Signal(bool, str)   # (success, message)
    progressMsg  = Signal(str)

    @Slot(str, str)
    def pushFile(self, localPath: str, androidDest: str) -> None:
        """Push *localPath* on the host to *androidDest* inside Waydroid."""
        def _do() -> None:
            from pathlib import Path

            from waydroid_toolkit.modules.maintenance.tools import push_file
            push_file(Path(localPath), androidDest)

        def _finish(_: None) -> None:
            self.transferDone.emit(True, f"Pushed {localPath} → {androidDest}")

        self._run(_do, on_done=_finish)

    @Slot(str, str)
    def pullFile(self, androidSrc: str, localDest: str) -> None:
        """Pull *androidSrc* from Waydroid to *localDest* on the host."""
        def _do() -> None:
            from pathlib import Path

            from waydroid_toolkit.modules.maintenance.tools import pull_file
            pull_file(androidSrc, Path(localDest))

        def _finish(_: None) -> None:
            self.transferDone.emit(True, f"Pulled {androidSrc} → {localDest}")

        self._run(_do, on_done=_finish)


# ── Logcat bridge ─────────────────────────────────────────────────────────────

class LogcatBridge(QtCore.QObject):
    """Live logcat streaming bridge.

    Wraps ``stream_logcat`` in a background thread and emits each line
    to QML via ``lineReceived``. Supports tag and level filters that can
    be changed while streaming is active (restarts the stream).

    Lifecycle
    ---------
    QML calls ``start()`` to begin streaming.
    QML calls ``stop()`` to terminate the stream.
    ``streamingChanged`` is emitted whenever the running state changes.
    """

    lineReceived    = Signal(str)
    streamingChanged = Signal()
    errorOccurred   = Signal(str)

    _LEVELS = ("V", "D", "I", "W", "E", "F")

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._streaming = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._tag: str = ""
        self._level: str = ""   # empty = all levels

    # ── Properties ────────────────────────────────────────────────────────

    @Property(bool, notify=streamingChanged)
    def streaming(self) -> bool:
        return self._streaming

    @Property(str)
    def tag(self) -> str:
        return self._tag

    @Property(str)
    def level(self) -> str:
        return self._level

    # ── Slots ──────────────────────────────────────────────────────────────

    @Slot()
    def start(self) -> None:
        """Start (or restart) the logcat stream."""
        self.stop()
        self._stop_event.clear()
        self._set_streaming(True)
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()

    @Slot()
    def stop(self) -> None:
        """Stop the logcat stream."""
        self._stop_event.set()
        self._set_streaming(False)

    @Slot(str)
    def setTag(self, tag: str) -> None:
        """Filter by tag. Empty string = no tag filter. Restarts stream."""
        self._tag = tag.strip()
        if self._streaming:
            self.start()

    @Slot(str)
    def setLevel(self, level: str) -> None:
        """Filter by minimum level (V/D/I/W/E/F). Empty = all. Restarts stream."""
        lvl = level.strip().upper()
        if lvl and lvl not in self._LEVELS:
            self.errorOccurred.emit(
                f"Unknown log level '{level}'. Valid: {', '.join(self._LEVELS)}"
            )
            return
        self._level = lvl
        if self._streaming:
            self.start()

    # ── Internal ──────────────────────────────────────────────────────────

    def _set_streaming(self, value: bool) -> None:
        if self._streaming != value:
            self._streaming = value
            self.streamingChanged.emit()

    def _stream_loop(self) -> None:
        """Background thread: read logcat lines and emit signals."""
        try:
            from waydroid_toolkit.modules.maintenance.tools import stream_logcat
            errors_only = self._level == "E"
            tag = self._tag or None
            for line in stream_logcat(tag=tag, errors_only=errors_only):
                if self._stop_event.is_set():
                    break
                # Client-side level filter when not using errors_only shortcut
                if self._level and self._level not in ("E",):
                    if not self._line_matches_level(line, self._level):
                        continue
                self.lineReceived.emit(line)
        except Exception:  # noqa: BLE001
            if not self._stop_event.is_set():
                self.errorOccurred.emit(traceback.format_exc())
        finally:
            self._set_streaming(False)

    @staticmethod
    def _line_matches_level(line: str, min_level: str) -> bool:
        """Return True if the logcat line is at or above *min_level*.

        Standard logcat format: ``MM-DD HH:MM:SS.mmm PID TID LEVEL tag: msg``
        The level character is at index 4 of the space-split tokens.
        """
        levels = LogcatBridge._LEVELS
        try:
            parts = line.split()
            if len(parts) < 5:
                return True  # can't parse — let it through
            line_level = parts[4].upper()
            if line_level not in levels:
                return True
            return levels.index(line_level) >= levels.index(min_level)
        except (IndexError, ValueError):
            return True


# ── ADB shell bridge ──────────────────────────────────────────────────────────

class AdbShellBridge(QtCore.QObject):
    """Interactive adb shell terminal bridge for the native fallback UI.

    Maintains a persistent ``adb shell`` subprocess. A background thread
    reads stdout line-by-line and emits ``lineReceived`` on the Qt thread
    via a queued signal so QML can append each line to the terminal view.

    Lifecycle
    ---------
    QML calls ``connect()`` when the Terminal page becomes visible.
    The user types a command and QML calls ``sendLine(cmd)``.
    QML calls ``disconnect()`` when leaving the page (or on window close).

    If the persistent shell process dies unexpectedly ``sessionEnded`` is
    emitted so QML can show a reconnect prompt.
    """

    # Emitted for every line of output from the shell (including the prompt)
    lineReceived = Signal(str)
    # Emitted when the adb connection state changes
    connectedChanged = Signal()
    # Emitted when the shell process exits (code, or -1 on read error)
    sessionEnded = Signal(int)
    # Emitted when adb is not on PATH or the device is unreachable
    errorOccurred = Signal(str)

    _ADB_TARGET = "192.168.250.1:5555"

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._connected = False

    # ── Public properties ─────────────────────────────────────────────────

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self._connected

    # ── Slots ─────────────────────────────────────────────────────────────

    @Slot()
    def connectShell(self) -> None:
        """Open a persistent ``adb shell`` session to Waydroid."""
        if self._proc is not None:
            return  # already open

        try:
            subprocess.run(
                ["adb", "connect", self._ADB_TARGET],
                capture_output=True, timeout=8, check=False,
            )
            self._proc = subprocess.Popen(
                ["adb", "-s", self._ADB_TARGET, "shell"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self.errorOccurred.emit(
                "adb not found. Install android-tools-adb and try again."
            )
            return
        except Exception:  # noqa: BLE001
            self.errorOccurred.emit(traceback.format_exc())
            return

        self._set_connected(True)
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    @Slot()
    def disconnectShell(self) -> None:
        """Terminate the shell session."""
        proc = self._proc
        self._proc = None
        self._set_connected(False)
        if proc is not None:
            try:
                proc.stdin.close()  # type: ignore[union-attr]
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:  # noqa: BLE001
                proc.kill()

    @Slot(str)
    def sendLine(self, line: str) -> None:
        """Write *line* to the shell's stdin (newline appended automatically)."""
        if self._proc is None or self._proc.stdin is None:
            self.errorOccurred.emit("Shell is not connected.")
            return
        try:
            self._proc.stdin.write(line + "\n")
            self._proc.stdin.flush()
        except BrokenPipeError:
            self._handle_proc_exit(-1)

    @Slot(str, result=str)
    def runCommand(self, command: str) -> str:
        """Run a single ``adb shell <command>`` and return combined output.

        This is the one-shot fallback used when no persistent session is
        open (e.g. the user hasn't pressed Connect yet).
        """
        try:
            result = subprocess.run(
                ["adb", "-s", self._ADB_TARGET, "shell", command],
                capture_output=True, text=True, timeout=30,
            )
            return (result.stdout + result.stderr).rstrip()
        except FileNotFoundError:
            return "Error: adb not found. Install android-tools-adb."
        except subprocess.TimeoutExpired:
            return "Error: command timed out after 30 s."
        except Exception:  # noqa: BLE001
            return traceback.format_exc()

    # ── Internal ──────────────────────────────────────────────────────────

    def _set_connected(self, value: bool) -> None:
        if self._connected != value:
            self._connected = value
            self.connectedChanged.emit()

    def _read_loop(self) -> None:
        """Background thread: read lines from the shell and emit signals."""
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                if self._proc is None:
                    break  # disconnectShell() was called
                self.lineReceived.emit(line.rstrip("\n"))
            code = proc.wait()
        except Exception:  # noqa: BLE001
            code = -1
        # Only fire sessionEnded if we didn't initiate the disconnect
        if self._proc is not None:
            self._handle_proc_exit(code)

    def _handle_proc_exit(self, code: int) -> None:
        self._proc = None
        self._set_connected(False)
        self.sessionEnded.emit(code)
