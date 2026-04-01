"""Maintenance page — display settings, screenshot, logcat, file transfer, debloat."""

from __future__ import annotations

import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from waydroid_toolkit.modules.maintenance import (
    get_device_info, reset_display, set_density, set_resolution, take_screenshot,
)
from .base import BasePage


class MaintenancePage(BasePage):
    def __init__(self) -> None:
        super().__init__("Maintenance")
        self._build()

    def _build(self) -> None:
        # ── Device info ───────────────────────────────────────────────────────
        info_group = self.make_section("Device Info")
        self._info_rows: dict[str, Adw.ActionRow] = {}
        for key in ("android_version", "sdk_version", "product_model", "cpu_abi", "display", "density"):
            row = Adw.ActionRow(title=key.replace("_", " ").title(), subtitle="—")
            info_group.add(row)
            self._info_rows[key] = row

        info_refresh_btn = self.make_button("Refresh Info")
        info_refresh_btn.connect("clicked", lambda _: self._load_device_info())

        # ── Display settings ──────────────────────────────────────────────────
        display_group = self.make_section("Display Settings")

        res_row = Adw.ActionRow(title="Resolution", subtitle="Width × Height")
        self._width_entry = Gtk.Entry(placeholder_text="1280", max_width_chars=6,
                                      valign=Gtk.Align.CENTER)
        self._height_entry = Gtk.Entry(placeholder_text="720", max_width_chars=6,
                                       valign=Gtk.Align.CENTER)
        res_row.add_suffix(self._width_entry)
        res_row.add_suffix(Gtk.Label(label="×", valign=Gtk.Align.CENTER))
        res_row.add_suffix(self._height_entry)
        display_group.add(res_row)

        dpi_row = Adw.ActionRow(title="Density (DPI)")
        self._dpi_entry = Gtk.Entry(placeholder_text="240", max_width_chars=6,
                                    valign=Gtk.Align.CENTER)
        dpi_row.add_suffix(self._dpi_entry)
        display_group.add(dpi_row)

        display_btn_box = Gtk.Box(spacing=8)
        apply_display_btn = self.make_button("Apply Display Settings")
        apply_display_btn.connect("clicked", self._on_apply_display)
        reset_display_btn = self.make_button("Reset to Defaults", css_class="destructive-action")
        reset_display_btn.connect("clicked", lambda _: reset_display())
        display_btn_box.append(apply_display_btn)
        display_btn_box.append(reset_display_btn)

        # ── Screenshot ────────────────────────────────────────────────────────
        screenshot_group = self.make_section("Screenshot")
        self._screenshot_status = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])
        screenshot_btn = self.make_button("Take Screenshot")
        screenshot_btn.connect("clicked", self._on_screenshot)

        self._status = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])

        self.append_to_body(info_group)
        self.append_to_body(info_refresh_btn)
        self.append_to_body(display_group)
        self.append_to_body(display_btn_box)
        self.append_to_body(screenshot_group)
        self.append_to_body(screenshot_btn)
        self.append_to_body(self._screenshot_status)
        self.append_to_body(self._status)

        self._load_device_info()

    def _load_device_info(self) -> None:
        def _work() -> None:
            try:
                info = get_device_info()
            except Exception:
                info = {}

            def _update() -> None:
                for key, row in self._info_rows.items():
                    row.set_subtitle(info.get(key, "unavailable"))

            GLib.idle_add(_update)

        threading.Thread(target=_work, daemon=True).start()

    def _on_apply_display(self, _btn: Gtk.Button) -> None:
        try:
            w = int(self._width_entry.get_text() or "0")
            h = int(self._height_entry.get_text() or "0")
            dpi = int(self._dpi_entry.get_text() or "0")
            if w and h:
                set_resolution(w, h)
            if dpi:
                set_density(dpi)
            self._status.set_label("Display settings applied. Restart Waydroid to take effect.")
        except ValueError:
            self._status.set_label("Invalid values — enter integers only.")

    def _on_screenshot(self, _btn: Gtk.Button) -> None:
        self._screenshot_status.set_label("Capturing…")

        def _work() -> None:
            try:
                path = take_screenshot()
                GLib.idle_add(lambda: self._screenshot_status.set_label(f"Saved: {path}"))
            except Exception as e:
                GLib.idle_add(lambda: self._screenshot_status.set_label(f"Error: {e}"))

        threading.Thread(target=_work, daemon=True).start()
