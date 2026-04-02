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
            from waydroid_toolkit.core.container import get_active, list_backends
            backends = [
                {"id": b.backend_type.value, "available": b.is_available()}
                for b in list_backends()
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
            from waydroid_toolkit.modules.extensions import list_extensions
            return [
                {
                    "id":          e.meta.id,
                    "name":        e.meta.name,
                    "description": e.meta.description,
                    "installed":   e.is_installed(),
                }
                for e in list_extensions()
            ]

        def _apply(data: list) -> None:
            self._extensions = data
            self.extensionsChanged.emit()

        self._run(_fetch, on_done=_apply)

    @Slot(str)
    def install(self, ext_id: str) -> None:
        def _do() -> None:
            from waydroid_toolkit.modules.extensions import get_extension
            get_extension(ext_id).install()
        self._run(_do, on_done=lambda _: self.refresh())

    @Slot(str)
    def uninstall(self, ext_id: str) -> None:
        def _do() -> None:
            from waydroid_toolkit.modules.extensions import get_extension
            get_extension(ext_id).uninstall()
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
    """Exposes image profile management to QML."""

    imagesChanged = Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._images: list[dict] = []

    @Property("QVariantList", notify=imagesChanged)
    def images(self) -> list: return self._images

    @Slot()
    def refresh(self) -> None:
        def _do() -> list:
            from waydroid_toolkit.modules.images.manager import list_images
            return [{"name": i.name, "active": i.active} for i in list_images()]

        def _apply(data: list) -> None:
            self._images = data
            self.imagesChanged.emit()

        self._run(_do, on_done=_apply)

    @Slot(str)
    def activate(self, name: str) -> None:
        def _do() -> None:
            from waydroid_toolkit.modules.images.manager import activate_image
            activate_image(name)
        self._run(_do, on_done=lambda _: self.refresh())


# ── Maintenance bridge ────────────────────────────────────────────────────────

class MaintenanceBridge(WdtBridgeBase):
    """Exposes maintenance tools (logcat, screenshot, debloat) to QML."""

    logcatOutput    = Signal(str)
    screenshotSaved = Signal(str)

    @Slot()
    def captureScreenshot(self) -> None:
        def _do() -> str:
            from waydroid_toolkit.modules.maintenance.tools import take_screenshot
            return take_screenshot()
        self._run(_do, on_done=lambda p: self.screenshotSaved.emit(p))

    @Slot()
    def startLogcat(self) -> None:
        def _do() -> str:
            from waydroid_toolkit.modules.maintenance.tools import get_logcat
            return get_logcat()
        self._run(_do, on_done=lambda out: self.logcatOutput.emit(out))
