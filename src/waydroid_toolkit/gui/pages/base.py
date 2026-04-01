"""Base class for all GUI pages.

Each page is a Gtk.Box wrapped in an Adw.ToolbarView so it gets a
consistent header bar with a title. Subclasses call self.set_body(widget)
to place their content below the header.

Error reporting
---------------
Background operations should call self._show_error(msg) from a
GLib.idle_add callback when they fail. This posts an Adw.Toast via the
application-wide ToastOverlay registered by MainWindow at startup, so
errors are visible regardless of which page is currently shown.

Usage in a background thread::

    def _work() -> None:
        try:
            do_something()
        except Exception as exc:
            msg = str(exc)
            GLib.idle_add(lambda: self._show_error(msg))

    threading.Thread(target=_work, daemon=True).start()
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

# Application-wide toast overlay, set by MainWindow._build_ui().
# Pages post toasts here so notifications appear regardless of which
# page is currently visible.
_toast_overlay: Adw.ToastOverlay | None = None


def register_toast_overlay(overlay: Adw.ToastOverlay) -> None:
    """Register the application-wide ToastOverlay. Called once by MainWindow."""
    global _toast_overlay
    _toast_overlay = overlay


class BasePage(Gtk.Box):
    def __init__(self, title: str) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._title = title

        self._toolbar_view = Adw.ToolbarView()
        self.append(self._toolbar_view)

        header = Adw.HeaderBar(show_back_button=False)
        title_widget = Adw.WindowTitle(title=title, subtitle="")
        header.set_title_widget(title_widget)
        self._toolbar_view.add_top_bar(header)

        self._body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                             margin_start=24, margin_end=24,
                             margin_top=12, margin_bottom=24)
        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(self._body)
        self._toolbar_view.set_content(scroll)

    def set_body(self, widget: Gtk.Widget) -> None:
        """Replace the page body with widget."""
        child = self._body.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._body.remove(child)
            child = next_child
        self._body.append(widget)

    def append_to_body(self, widget: Gtk.Widget) -> None:
        self._body.append(widget)

    @staticmethod
    def make_section(title: str) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=title)
        return group

    @staticmethod
    def make_action_row(title: str, subtitle: str = "") -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        return row

    @staticmethod
    def make_button(label: str, css_class: str = "suggested-action") -> Gtk.Button:
        btn = Gtk.Button(label=label, css_classes=[css_class], halign=Gtk.Align.START)
        return btn

    # ── Toast notifications ───────────────────────────────────────────────────

    def _show_toast(self, message: str, timeout: int = 3) -> None:
        """Post a toast notification via the application-wide ToastOverlay.

        Safe to call from GLib.idle_add callbacks. Falls back silently if
        the overlay has not been registered (e.g. in unit tests).
        """
        if _toast_overlay is None:
            return
        toast = Adw.Toast(title=message, timeout=timeout)
        _toast_overlay.add_toast(toast)

    def _show_error(self, message: str) -> None:
        """Post an error toast. Prefixes the message with 'Error: '."""
        self._show_toast(f"Error: {message}", timeout=5)
