"""Base class for all GUI pages.

Each page is a Gtk.Box wrapped in an Adw.ToolbarView so it gets a
consistent header bar with a title. Subclasses call self.set_body(widget)
to place their content below the header.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


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
