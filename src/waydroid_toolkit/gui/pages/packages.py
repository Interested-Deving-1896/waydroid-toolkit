"""Packages page — install APKs and manage F-Droid repos."""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from waydroid_toolkit.modules.packages import (
    get_installed_packages,
    install_apk_url,
)

from .base import BasePage


class PackagesPage(BasePage):
    def __init__(self) -> None:
        super().__init__("Packages")
        self._build()

    def _build(self) -> None:
        # APK install from URL
        install_group = self.make_section("Install APK")
        self._url_entry = Gtk.Entry(placeholder_text="https://… or /path/to/app.apk",
                                    hexpand=True)
        install_row = Adw.ActionRow(title="APK source")
        install_row.add_suffix(self._url_entry)
        install_btn = Gtk.Button(
            label="Install", css_classes=["suggested-action"], valign=Gtk.Align.CENTER,
        )
        install_btn.connect("clicked", self._on_install)
        install_row.add_suffix(install_btn)
        install_group.add(install_row)

        self._install_status = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])

        # Installed packages
        pkgs_group = self.make_section("Installed Packages")
        self._pkgs_list = Gtk.ListBox(
            css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE,
        )
        pkgs_group.add(self._pkgs_list)

        refresh_btn = self.make_button("Refresh Package List")
        refresh_btn.connect("clicked", lambda _: self._load_packages())

        self.append_to_body(install_group)
        self.append_to_body(self._install_status)
        self.append_to_body(pkgs_group)
        self.append_to_body(refresh_btn)
        self._load_packages()

    def _on_install(self, _btn: Gtk.Button) -> None:
        source = self._url_entry.get_text().strip()
        if not source:
            return
        self._install_status.set_label("Installing…")

        def _work() -> None:
            try:
                if source.startswith("http"):
                    install_apk_url(source)
                else:
                    from waydroid_toolkit.modules.packages import install_apk_file
                    install_apk_file(Path(source))
                GLib.idle_add(lambda: self._install_status.set_label("Installed successfully."))
                GLib.idle_add(self._load_packages)
            except Exception as exc:
                msg = str(exc)
                GLib.idle_add(lambda: self._install_status.set_label(f"Error: {msg}"))
                GLib.idle_add(lambda: self._show_error(msg))

        threading.Thread(target=_work, daemon=True).start()

    def _load_packages(self) -> None:
        def _work() -> None:
            try:
                pkgs = get_installed_packages()
            except Exception:
                pkgs = []

            def _update() -> None:
                child = self._pkgs_list.get_first_child()
                while child:
                    nxt = child.get_next_sibling()
                    self._pkgs_list.remove(child)
                    child = nxt
                for pkg in sorted(pkgs):
                    row = Adw.ActionRow(title=pkg)
                    self._pkgs_list.append(row)

            GLib.idle_add(_update)

        threading.Thread(target=_work, daemon=True).start()
