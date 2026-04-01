"""Status page — shows Waydroid runtime state at a glance."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib

from waydroid_toolkit.gui.presenters import get_status_data

from .base import BasePage


class StatusPage(BasePage):
    def __init__(self) -> None:
        super().__init__("Status")
        self._build()

    def _build(self) -> None:
        group = self.make_section("Waydroid Runtime")

        self._row_installed = Adw.ActionRow(title="Waydroid installed")
        self._row_initialized = Adw.ActionRow(title="Waydroid initialized")
        self._row_session = Adw.ActionRow(title="Session state")
        self._row_images = Adw.ActionRow(title="Images path")
        self._row_overlay = Adw.ActionRow(title="Overlay enabled")
        self._row_adb = Adw.ActionRow(title="ADB available")
        self._row_adb_conn = Adw.ActionRow(title="ADB connected")

        for row in (
            self._row_installed, self._row_initialized, self._row_session,
            self._row_images, self._row_overlay, self._row_adb, self._row_adb_conn,
        ):
            group.add(row)

        refresh_btn = self.make_button("Refresh", css_class="suggested-action")
        refresh_btn.connect("clicked", lambda _: self._refresh())

        self.append_to_body(group)
        self.append_to_body(refresh_btn)
        self._refresh()

    def _refresh(self) -> None:
        def _work() -> None:
            data = get_status_data()

            def _update() -> None:
                self._row_installed.set_subtitle("Yes" if data.installed else "No")
                self._row_initialized.set_subtitle("Yes" if data.initialized else "No")
                self._row_session.set_subtitle(data.session_state.value.capitalize())
                self._row_images.set_subtitle(data.images_path or "(not set)")
                self._row_overlay.set_subtitle("Yes" if data.mount_overlays else "No")
                self._row_adb.set_subtitle("Yes" if data.adb_available else "No")
                self._row_adb_conn.set_subtitle("Yes" if data.adb_connected else "No")

            GLib.idle_add(_update)

        threading.Thread(target=_work, daemon=True).start()
