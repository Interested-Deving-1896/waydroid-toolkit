"""Extensions page — install/remove GApps, Magisk, ARM translation, microG."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from waydroid_toolkit.gui.presenters import get_extension_rows
from waydroid_toolkit.modules.extensions import ExtensionState, list_all

from .base import BasePage


class ExtensionsPage(BasePage):
    def __init__(self) -> None:
        super().__init__("Extensions")
        self._rows: dict[str, tuple[Adw.ActionRow, Gtk.Button, Gtk.Button]] = {}
        self._build()

    def _build(self) -> None:
        group = self.make_section("Available Extensions")

        for ext in list_all():
            row = Adw.ActionRow(title=ext.meta.name, subtitle=ext.meta.description)

            install_btn = Gtk.Button(label="Install", css_classes=["suggested-action"],
                                     valign=Gtk.Align.CENTER)
            remove_btn = Gtk.Button(label="Remove", css_classes=["destructive-action"],
                                    valign=Gtk.Align.CENTER)

            install_btn.connect("clicked", self._on_install, ext.meta.id)
            remove_btn.connect("clicked", self._on_remove, ext.meta.id)

            row.add_suffix(install_btn)
            row.add_suffix(remove_btn)
            group.add(row)
            self._rows[ext.meta.id] = (row, install_btn, remove_btn)

        self.append_to_body(group)
        self._refresh_states()

    def _refresh_states(self) -> None:
        def _work() -> None:
            rows = get_extension_rows()
            states = {r.ext_id: r.state for r in rows}

            def _update() -> None:
                for ext_id, (row, install_btn, remove_btn) in self._rows.items():
                    state = states.get(ext_id, ExtensionState.UNKNOWN)
                    installed = state == ExtensionState.INSTALLED
                    install_btn.set_sensitive(not installed)
                    remove_btn.set_sensitive(installed)

            GLib.idle_add(_update)

        threading.Thread(target=_work, daemon=True).start()

    def _on_install(self, _btn: Gtk.Button, ext_id: str) -> None:
        from waydroid_toolkit.modules.extensions import get
        ext = get(ext_id)
        row, install_btn, remove_btn = self._rows[ext_id]
        install_btn.set_sensitive(False)
        row.set_subtitle("Installing…")

        def _work() -> None:
            try:
                ext.install()
                GLib.idle_add(lambda: row.set_subtitle("Installed. Restart Waydroid to apply."))
            except Exception as exc:
                msg = str(exc)
                GLib.idle_add(lambda: row.set_subtitle(f"Error: {msg}"))
            finally:
                GLib.idle_add(self._refresh_states)

        threading.Thread(target=_work, daemon=True).start()

    def _on_remove(self, _btn: Gtk.Button, ext_id: str) -> None:
        from waydroid_toolkit.modules.extensions import get
        ext = get(ext_id)
        row, install_btn, remove_btn = self._rows[ext_id]
        remove_btn.set_sensitive(False)
        row.set_subtitle("Removing…")

        def _work() -> None:
            try:
                ext.uninstall()
                GLib.idle_add(lambda: row.set_subtitle(ext.meta.description))
            except Exception as exc:
                msg = str(exc)
                GLib.idle_add(lambda: row.set_subtitle(f"Error: {msg}"))
            finally:
                GLib.idle_add(self._refresh_states)

        threading.Thread(target=_work, daemon=True).start()
