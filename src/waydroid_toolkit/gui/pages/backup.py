"""Backup page — create and restore Waydroid backups."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from waydroid_toolkit.modules.backup import (
    DEFAULT_BACKUP_DIR,
    create_backup,
    list_backups,
    restore_backup,
)

from .base import BasePage


class BackupPage(BasePage):
    def __init__(self) -> None:
        super().__init__("Backup")
        self._build()

    def _build(self) -> None:
        create_group = self.make_section("Create Backup")
        self._create_status = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])
        create_btn = self.make_button("Create Backup Now")
        create_btn.connect("clicked", self._on_create)
        create_group.add(Adw.ActionRow(title=f"Destination: {DEFAULT_BACKUP_DIR}"))

        restore_group = self.make_section("Available Backups")
        self._backups_list = Gtk.ListBox(
            css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.SINGLE,
        )
        restore_btn = self.make_button("Restore Selected", css_class="destructive-action")
        restore_btn.connect("clicked", self._on_restore)
        self._restore_status = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])

        refresh_btn = self.make_button("Refresh List")
        refresh_btn.connect("clicked", lambda _: self._load_backups())

        self.append_to_body(create_group)
        self.append_to_body(create_btn)
        self.append_to_body(self._create_status)
        self.append_to_body(restore_group)
        self.append_to_body(self._backups_list)
        self.append_to_body(restore_btn)
        self.append_to_body(self._restore_status)
        self.append_to_body(refresh_btn)
        self._load_backups()

    def _on_create(self, _btn: Gtk.Button) -> None:
        self._create_status.set_label("Creating backup…")

        def _work() -> None:
            try:
                archive = create_backup()
                GLib.idle_add(lambda: self._create_status.set_label(f"Saved: {archive.name}"))
                GLib.idle_add(self._load_backups)
            except Exception as exc:
                msg = str(exc)
                GLib.idle_add(lambda: self._create_status.set_label(f"Error: {msg}"))

        threading.Thread(target=_work, daemon=True).start()

    def _load_backups(self) -> None:
        def _work() -> None:
            archives = list_backups()

            def _update() -> None:
                child = self._backups_list.get_first_child()
                while child:
                    nxt = child.get_next_sibling()
                    self._backups_list.remove(child)
                    child = nxt
                for a in archives:
                    size_mb = a.stat().st_size / (1024 * 1024)
                    row = Adw.ActionRow(
                        title=a.name,
                        subtitle=f"{size_mb:.1f} MB",
                    )
                    row.set_name(str(a))
                    self._backups_list.append(row)

            GLib.idle_add(_update)

        threading.Thread(target=_work, daemon=True).start()

    def _on_restore(self, _btn: Gtk.Button) -> None:
        row = self._backups_list.get_selected_row()
        if row is None:
            self._restore_status.set_label("Select a backup first.")
            return
        from pathlib import Path
        archive = Path(row.get_name())
        self._restore_status.set_label(f"Restoring {archive.name}…")

        def _work() -> None:
            try:
                restore_backup(archive)
                GLib.idle_add(lambda: self._restore_status.set_label("Restore complete."))
            except Exception as exc:
                msg = str(exc)
                GLib.idle_add(lambda: self._restore_status.set_label(f"Error: {msg}"))

        threading.Thread(target=_work, daemon=True).start()
