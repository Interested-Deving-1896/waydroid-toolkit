"""Images page — list and switch Waydroid image profiles."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from waydroid_toolkit.gui.presenters import get_image_profile_rows
from waydroid_toolkit.modules.images import switch_profile

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
            profile_rows = get_image_profile_rows()

            def _update() -> None:
                # Clear existing rows
                child = self._group.get_first_child()
                while child:
                    nxt = child.get_next_sibling()
                    self._group.remove(child)
                    child = nxt

                if not profile_rows:
                    self._status_label.set_label(
                        "No profiles found. Place system.img + vendor.img pairs"
                        " under ~/waydroid-images/."
                    )
                    return

                self._status_label.set_label(f"{len(profile_rows)} profile(s) found.")
                for pr in profile_rows:
                    active_tag = " (active)" if pr.is_active else ""
                    subtitle = str(pr.path) + active_tag
                    row = Adw.ActionRow(title=pr.name, subtitle=subtitle)
                    if not pr.is_active:
                        from waydroid_toolkit.modules.images.manager import ImageProfile
                        profile = ImageProfile(name=pr.name, path=pr.path)
                        btn = Gtk.Button(label="Switch", css_classes=["suggested-action"],
                                         valign=Gtk.Align.CENTER)
                        btn.connect("clicked", self._on_switch, profile)
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
                GLib.idle_add(lambda: self._show_error(msg))

        threading.Thread(target=_work, daemon=True).start()
