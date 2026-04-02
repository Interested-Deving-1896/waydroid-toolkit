"""WayDroid Toolkit Qt/QML application entry point.

Supports both PySide6 and PyQt6 via the qt_compat shim.
Launches a QML ApplicationWindow (Material style) with bridge objects
registered as context properties.

Launch via:
    wdt gui
or:
    python -m waydroid_toolkit.gui.app

WebEngine / wadb terminal
-------------------------
When PySide6-WebEngine (or PyQt6-WebEngine) is installed, the Terminal
page loads a local HTML page that uses the wadb TypeScript library over
WebUSB for a full ADB shell experience. The wadb HTML is built from
vendor/wadb and served from a QWebEngineUrlSchemeHandler on the
wdt:// scheme so it can access WebUSB without CORS restrictions.

When WebEngine is not installed, the Terminal page falls back to showing
logcat output via the native adb binary.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from waydroid_toolkit import __version__
from waydroid_toolkit.gui.qt_compat import (
    HAS_WEBENGINE,
    QT_BINDING,
    QtCore,
    QtQml,
    QtWidgets,
    qt_exec,
)

# QML source root
_QML_DIR = Path(__file__).parent / "qml"
# wadb built HTML (vendor/wadb/demo/index.html or dist/)
_WADB_DIR = Path(__file__).parent.parent.parent.parent.parent / "vendor" / "wadb"


def _wadb_html_url() -> str:
    """Return the URL for the wadb terminal HTML page, or empty string."""
    candidates = [
        _WADB_DIR / "demo" / "index.html",
        _WADB_DIR / "dist" / "index.html",
    ]
    for path in candidates:
        if path.exists():
            return path.as_uri()
    return ""


def _setup_webengine() -> None:
    """Initialise QtWebEngine before QApplication is created (required)."""
    if not HAS_WEBENGINE:
        return
    from waydroid_toolkit.gui.qt_compat import QtWebEngineQuick
    if QtWebEngineQuick is not None:
        QtWebEngineQuick.initialize()


def _register_bridges(engine: QtQml.QQmlApplicationEngine) -> None:  # type: ignore[name-defined]
    """Instantiate all bridge objects and expose them as QML context properties."""
    from waydroid_toolkit.gui.bridge import (
        AdbShellBridge,
        BackendBridge,
        BackupBridge,
        ExtensionsBridge,
        FileBridge,
        ImagesBridge,
        LogcatBridge,
        MaintenanceBridge,
        PackagesBridge,
        PerformanceBridge,
        StatusBridge,
    )

    ctx = engine.rootContext()

    bridges = {
        "statusBridge":      StatusBridge(),
        "backendBridge":     BackendBridge(),
        "extensionsBridge":  ExtensionsBridge(),
        "packagesBridge":    PackagesBridge(),
        "performanceBridge": PerformanceBridge(),
        "backupBridge":      BackupBridge(),
        "imagesBridge":      ImagesBridge(),
        "maintenanceBridge": MaintenanceBridge(),
        "fileBridge":        FileBridge(),
        "logcatBridge":      LogcatBridge(),
        "adbShellBridge":    AdbShellBridge(),
    }

    for name, bridge in bridges.items():
        ctx.setContextProperty(name, bridge)

    # App metadata
    ctx.setContextProperty("appVersion", f"v{__version__}")
    ctx.setContextProperty("qtBinding", QT_BINDING)
    ctx.setContextProperty("_wadbUrl", _wadb_html_url())


def run(argv: list[str] | None = None) -> int:
    """Start the Qt GUI application. Returns the process exit code."""
    if argv is None:
        argv = sys.argv

    # WebEngine must be initialised before QApplication
    _setup_webengine()

    # High-DPI scaling (Qt6 enables this by default, but be explicit)
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QtWidgets.QApplication(argv)
    app.setApplicationName("WayDroid Toolkit")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("waydroid-toolkit")

    # Material style is set per-component in QML via Material.theme/accent.
    # Set the Qt Quick Controls style globally here.
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")

    engine = QtQml.QQmlApplicationEngine()

    # Register QML import path so components/ and pages/ resolve correctly
    engine.addImportPath(str(_QML_DIR))

    _register_bridges(engine)

    main_qml = _QML_DIR / "Main.qml"
    if not main_qml.exists():
        print(f"ERROR: QML entry point not found: {main_qml}", file=sys.stderr)
        return 1

    engine.load(QtCore.QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        print("ERROR: Failed to load QML — check for syntax errors.", file=sys.stderr)
        return 1

    return qt_exec(app)


if __name__ == "__main__":
    sys.exit(run())

main = run  # entry point alias for pyproject.toml gui_scripts
