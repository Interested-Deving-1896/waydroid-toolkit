"""Images page — list and switch Waydroid image profiles."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from waydroid_toolkit.modules.images import get_active_profile, scan_profiles, switch_profile

from .base import BasePage


class ImagesPage(BasePage):
    def __init__(self) -> None:
        super().__init__("Images")
        self._build()

    def _build(self) -> None:
        self._group = self.make_section("Image Profiles")
        self._status_label = Gtk.Label(label="Scanning for profiles…", xalign=0,
                                       css_classes=["dim-label"])

        refresh_btn = self.make_button("Refresh")
        refresh_btn.connect("clicked", lambda _: self._load_profiles())

        self.append_to_body(self._status_label)
        self.append_to_body(self._group)
        self.append_to_body(refresh_btn)
        self._load_profiles()

    def _load_profiles(self) -> None:
        self._status_label.set_label("Scanning…")

        def _work() -> None:
            profiles = scan_profiles()
            active = get_active_profile()

            def _update() -> None:
                # Clear existing rows
                child = self._group.get_first_child()
                while child:
                    nxt = child.get_next_sibling()
                    self._group.remove(child)
                    child = nxt

                if not profiles:
                    self._status_label.set_label(
                        "No profiles found. Place system.img + vendor.img pairs"
                        " under ~/waydroid-images/."
                    )
                    return

                self._status_label.set_label(f"{len(profiles)} profile(s) found.")
                for p in profiles:
                    is_active = active and str(p.path) in active
                    active_tag = " (active)" if is_active else ""
                    subtitle = str(p.path) + active_tag
                    row = Adw.ActionRow(title=p.name, subtitle=subtitle)
                    if not is_active:
                        btn = Gtk.Button(label="Switch", css_classes=["suggested-action"],
                                         valign=Gtk.Align.CENTER)
                        btn.connect("clicked", self._on_switch, p)
                        row.add_suffix(btn)
                    self._group.add(row)

            GLib.idle_add(_update)

        threading.Thread(target=_work, daemon=True).start()

    def _on_switch(self, _btn: Gtk.Button, profile: object) -> None:
        self._status_label.set_label(f"Switching to '{profile.name}'…")  # type: ignore[attr-defined]

        def _work() -> None:
            try:
                switch_profile(profile)  # type: ignore[arg-type]
                GLib.idle_add(self._load_profiles)
            except Exception as exc:
                msg = str(exc)
                GLib.idle_add(lambda: self._status_label.set_label(f"Error: {msg}"))

        threading.Thread(target=_work, daemon=True).start()
