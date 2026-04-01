"""Backend page — select and inspect the active container backend."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from waydroid_toolkit.core.container import (
    BackendType,
    IncusBackend,
    LxcBackend,
)
from waydroid_toolkit.core.container import (
    get_active as get_active_backend,
)
from waydroid_toolkit.core.container import (
    set_active as set_active_backend,
)

from .base import BasePage


class BackendPage(BasePage):
    def __init__(self) -> None:
        super().__init__("Container Backend")
        self._build()

    def _build(self) -> None:
        # ── Active backend info ───────────────────────────────────────────────
        info_group = self.make_section("Active Backend")
        self._row_type = Adw.ActionRow(title="Backend", subtitle="—")
        self._row_binary = Adw.ActionRow(title="Binary", subtitle="—")
        self._row_version = Adw.ActionRow(title="Version", subtitle="—")
        self._row_container = Adw.ActionRow(title="Container name", subtitle="—")
        for row in (
            self._row_type, self._row_binary, self._row_version, self._row_container,
        ):
            info_group.add(row)

        refresh_btn = self.make_button("Refresh")
        refresh_btn.connect("clicked", lambda _: self._load_info())

        # ── Backend selector ──────────────────────────────────────────────────
        select_group = self.make_section("Switch Backend")
        self._status_label = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])

        for backend_cls, label, subtitle in (
            (
                LxcBackend,
                "LXC",
                "Default Waydroid backend. Uses lxc-start / lxc-stop / lxc-attach.",
            ),
            (
                IncusBackend,
                "Incus",
                "Modern LXC-based manager. Run 'wdt backend incus-setup' after switching.",
            ),
        ):
            backend = backend_cls()
            row = Adw.ActionRow(title=label, subtitle=subtitle)
            btn = Gtk.Button(
                label="Use",
                css_classes=["suggested-action"],
                valign=Gtk.Align.CENTER,
                sensitive=backend.is_available(),
            )
            if not backend.is_available():
                row.set_subtitle(subtitle + "  [not installed]")
            btn.connect("clicked", self._on_switch, backend.backend_type)
            row.add_suffix(btn)
            select_group.add(row)

        # ── Incus setup helper ────────────────────────────────────────────────
        setup_group = self.make_section("Incus Setup")
        setup_row = Adw.ActionRow(
            title="Import Waydroid config into Incus",
            subtitle=(
                "Reads the LXC config written by waydroid init and creates an "
                "equivalent Incus container with raw.lxc passthrough."
            ),
        )
        setup_btn = Gtk.Button(
            label="Run Setup",
            css_classes=["suggested-action"],
            valign=Gtk.Align.CENTER,
            sensitive=IncusBackend().is_available(),
        )
        setup_btn.connect("clicked", self._on_incus_setup)
        setup_row.add_suffix(setup_btn)
        setup_group.add(setup_row)
        self._setup_status = Gtk.Label(label="", xalign=0, css_classes=["dim-label"])

        self.append_to_body(info_group)
        self.append_to_body(refresh_btn)
        self.append_to_body(select_group)
        self.append_to_body(self._status_label)
        self.append_to_body(setup_group)
        self.append_to_body(self._setup_status)

        self._load_info()

    def _load_info(self) -> None:
        def _work() -> None:
            try:
                backend = get_active_backend()
                info = backend.get_info()

                def _update() -> None:
                    self._row_type.set_subtitle(info.backend_type.value)
                    self._row_binary.set_subtitle(info.binary)
                    self._row_version.set_subtitle(info.version)
                    self._row_container.set_subtitle(info.container_name)

                GLib.idle_add(_update)
            except RuntimeError as exc:
                msg = str(exc)
                GLib.idle_add(
                    lambda: self._row_type.set_subtitle(f"Error: {msg}")
                )

        threading.Thread(target=_work, daemon=True).start()

    def _on_switch(self, _btn: Gtk.Button, backend_type: BackendType) -> None:
        self._status_label.set_label(f"Switching to {backend_type.value}…")

        def _work() -> None:
            try:
                set_active_backend(backend_type)
                GLib.idle_add(
                    lambda: self._status_label.set_label(
                        f"Active backend set to {backend_type.value}."
                    )
                )
                GLib.idle_add(self._load_info)
            except Exception as exc:
                msg = str(exc)
                GLib.idle_add(lambda: self._status_label.set_label(f"Error: {msg}"))

        threading.Thread(target=_work, daemon=True).start()

    def _on_incus_setup(self, _btn: Gtk.Button) -> None:
        self._setup_status.set_label("Running Incus setup…")

        def _work() -> None:
            try:
                IncusBackend().setup_from_lxc()
                GLib.idle_add(
                    lambda: self._setup_status.set_label(
                        "Done. Waydroid container imported into Incus."
                    )
                )
            except Exception as exc:
                msg = str(exc)
                GLib.idle_add(lambda: self._setup_status.set_label(f"Error: {msg}"))

        threading.Thread(target=_work, daemon=True).start()
