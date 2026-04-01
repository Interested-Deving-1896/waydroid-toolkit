"""WayDroid Toolkit GTK4/Adwaita GUI application.

Requires: PyGObject >= 3.44, libadwaita >= 1.4

Launch via:
    waydroid-toolkit
or:
    python -m waydroid_toolkit.gui.app
"""

from __future__ import annotations

import sys

try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio, Gtk
except (ImportError, ValueError) as exc:
    print(
        f"GUI dependencies not available: {exc}\n"
        "Install with: pip install waydroid-toolkit[gui]\n"
        "and ensure libgtk-4 and libadwaita are installed on your system.",
        file=sys.stderr,
    )
    sys.exit(1)

from waydroid_toolkit import __version__

from .pages.backend import BackendPage
from .pages.backup import BackupPage
from .pages.extensions import ExtensionsPage
from .pages.images import ImagesPage
from .pages.maintenance import MaintenancePage
from .pages.packages import PackagesPage
from .pages.performance import PerformancePage
from .pages.status import StatusPage


class WayDroidToolkitApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="id.waydro.toolkit",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, app: Adw.Application) -> None:
        win = MainWindow(application=app)
        win.present()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(
            title=f"WayDroid Toolkit {__version__}",
            default_width=960,
            default_height=680,
            **kwargs,
        )
        self._build_ui()

    def _build_ui(self) -> None:
        # Root split view: sidebar + content
        split = Adw.NavigationSplitView()
        self.set_content(split)

        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar_nav = Adw.NavigationPage(title="WayDroid Toolkit")
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_nav.set_child(sidebar_box)

        header = Adw.HeaderBar()
        sidebar_box.append(header)

        self._list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self._list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._list.connect("row-selected", self._on_nav_selected)

        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(self._list)
        sidebar_box.append(scroll)

        split.set_sidebar(sidebar_nav)

        # ── Content stack ─────────────────────────────────────────────────────
        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        content_nav = Adw.NavigationPage(title="")
        content_nav.set_child(self._stack)
        split.set_content(content_nav)

        # ── Pages ─────────────────────────────────────────────────────────────
        self._pages: list[tuple[str, str, Gtk.Widget]] = [
            ("status",      "Status",       StatusPage()),
            ("backend",     "Backend",      BackendPage()),
            ("extensions",  "Extensions",   ExtensionsPage()),
            ("images",      "Images",       ImagesPage()),
            ("packages",    "Packages",     PackagesPage()),
            ("backup",      "Backup",       BackupPage()),
            ("performance", "Performance",  PerformancePage()),
            ("maintenance", "Maintenance",  MaintenancePage()),
        ]

        for page_id, label, widget in self._pages:
            self._stack.add_named(widget, page_id)
            row = Gtk.ListBoxRow()
            row_label = Gtk.Label(
                label=label,
                xalign=0,
                margin_start=12,
                margin_end=12,
                margin_top=8,
                margin_bottom=8,
            )
            row.set_child(row_label)
            row.set_name(page_id)
            self._list.append(row)

        # Select first row by default
        self._list.select_row(self._list.get_row_at_index(0))

    def _on_nav_selected(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is not None:
            self._stack.set_visible_child_name(row.get_name())


def main() -> None:
    app = WayDroidToolkitApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
