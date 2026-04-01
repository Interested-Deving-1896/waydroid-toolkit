"""Performance page — host-side tuning for Waydroid gaming."""

from __future__ import annotations

import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from waydroid_toolkit.modules.performance import PerformanceProfile, apply_profile, restore_defaults
from .base import BasePage


class PerformancePage(BasePage):
    def __init__(self) -> None:
        super().__init__("Performance")
        self._build()

    def _build(self) -> None:
        settings_group = self.make_section("Profile Settings")

        # ZRAM size
        zram_row = Adw.ActionRow(title="ZRAM size (MB)", subtitle="Swap compressed in RAM")
        self._zram_spin = Gtk.SpinButton.new_with_range(512, 32768, 512)
        self._zram_spin.set_value(4096)
        self._zram_spin.set_valign(Gtk.Align.CENTER)
        zram_row.add_suffix(self._zram_spin)
        settings_group.add(zram_row)

        # ZRAM algorithm
        algo_row = Adw.ActionRow(title="ZRAM algorithm")
        self._algo_combo = Gtk.DropDown.new_from_strings(["lz4", "zstd", "lzo"])
        self._algo_combo.set_valign(Gtk.Align.CENTER)
        algo_row.add_suffix(self._algo_combo)
        settings_group.add(algo_row)

        # CPU governor
        gov_row = Adw.ActionRow(title="CPU governor")
        self._gov_combo = Gtk.DropDown.new_from_strings(["performance", "schedutil", "powersave"])
        self._gov_combo.set_valign(Gtk.Align.CENTER)
        gov_row.add_suffix(self._gov_combo)
        settings_group.add(gov_row)

        # Turbo boost
        turbo_row = Adw.SwitchRow(title="CPU Turbo Boost", subtitle="Enable Intel/AMD boost")
        turbo_row.set_active(True)
        settings_group.add(turbo_row)
        self._turbo_row = turbo_row

        # GameMode
        gamemode_row = Adw.SwitchRow(title="GameMode", subtitle="Requires gamemode package")
        gamemode_row.set_active(True)
        settings_group.add(gamemode_row)
        self._gamemode_row = gamemode_row

        self._status = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])

        apply_btn = self.make_button("Apply Profile")
        apply_btn.connect("clicked", self._on_apply)
        restore_btn = self.make_button("Restore Defaults", css_class="destructive-action")
        restore_btn.connect("clicked", self._on_restore)

        btn_box = Gtk.Box(spacing=8)
        btn_box.append(apply_btn)
        btn_box.append(restore_btn)

        self.append_to_body(settings_group)
        self.append_to_body(btn_box)
        self.append_to_body(self._status)

    def _on_apply(self, _btn: Gtk.Button) -> None:
        governors = ["performance", "schedutil", "powersave"]
        algorithms = ["lz4", "zstd", "lzo"]
        profile = PerformanceProfile(
            zram_size_mb=int(self._zram_spin.get_value()),
            zram_algorithm=algorithms[self._algo_combo.get_selected()],
            cpu_governor=governors[self._gov_combo.get_selected()],
            enable_turbo=self._turbo_row.get_active(),
            use_gamemode=self._gamemode_row.get_active(),
        )
        self._status.set_label("Applying profile…")

        def _work() -> None:
            try:
                apply_profile(profile)
                GLib.idle_add(lambda: self._status.set_label("Profile applied."))
            except Exception as e:
                GLib.idle_add(lambda: self._status.set_label(f"Error: {e}"))

        threading.Thread(target=_work, daemon=True).start()

    def _on_restore(self, _btn: Gtk.Button) -> None:
        self._status.set_label("Restoring defaults…")

        def _work() -> None:
            try:
                restore_defaults()
                GLib.idle_add(lambda: self._status.set_label("Defaults restored."))
            except Exception as e:
                GLib.idle_add(lambda: self._status.set_label(f"Error: {e}"))

        threading.Thread(target=_work, daemon=True).start()
