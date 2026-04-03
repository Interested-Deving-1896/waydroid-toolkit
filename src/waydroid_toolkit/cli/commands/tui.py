"""wdt tui — interactive terminal UI for waydroid-toolkit.

Menu-driven interface for common wdt operations.
Requires: dialog or whiptail.

Sub-commands
------------
  wdt tui    Launch the interactive menu
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import click
from rich.console import Console

console = Console()

_WDT = [sys.executable, "-m", "waydroid_toolkit"] if "__main__" not in sys.modules else ["wdt"]


def _wdt(*args: str) -> list[str]:
    """Build a wdt sub-command invocation."""
    return ["wdt", *args]


def _detect_dialog() -> str:
    for prog in ("dialog", "whiptail"):
        if shutil.which(prog):
            return prog
    return ""


def _dlg(dialog: str, *args: str) -> str:
    """Run dialog/whiptail, return selected value or raise on cancel."""
    result = subprocess.run(
        [dialog, "--backtitle", "wdt — Waydroid Toolkit", *args],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise KeyboardInterrupt
    return result.stderr.strip()


def _menu(dialog: str, title: str, text: str, *items: str) -> str:
    return _dlg(dialog, "--title", title, "--menu", text, "0", "0", "0", *items)


def _input(dialog: str, title: str, text: str, default: str = "") -> str:
    return _dlg(dialog, "--title", title, "--inputbox", text, "0", "60", default)


def _yesno(dialog: str, title: str, text: str) -> bool:
    result = subprocess.run(
        [dialog, "--backtitle", "wdt — Waydroid Toolkit",
         "--title", title, "--yesno", text, "0", "0"],
        capture_output=True,
    )
    return result.returncode == 0


def _msgbox(dialog: str, title: str, text: str) -> None:
    subprocess.run(
        [dialog, "--backtitle", "wdt — Waydroid Toolkit",
         "--title", title, "--msgbox", text, "0", "0"],
        capture_output=True,
    )


def _run_cmd(dialog: str, title: str, *args: str) -> None:
    result = subprocess.run(list(args), capture_output=True, text=True)
    output = result.stdout + result.stderr
    # Strip ANSI codes
    import re
    output = re.sub(r"\x1b\[[0-9;]*m", "", output)
    _msgbox(dialog, title, output.strip() or "Done.")


def _run_interactive(*args: str) -> None:
    """Drop out of dialog and run a command interactively in the terminal."""
    subprocess.call(list(args))
    input("\nPress Enter to continue...")


# ── menus ─────────────────────────────────────────────────────────────────────

def _menu_main(d: str) -> None:
    while True:
        try:
            choice = _menu(d, "wdt", "Select an action:",
                           "status",         "Show Waydroid status",
                           "container",      "Container lifecycle",
                           "backup",         "Backup and restore",
                           "images",         "Image profiles and OTA",
                           "fleet",          "Multi-instance orchestration",
                           "publish",        "Publish container as image",
                           "disk",           "Disk resize",
                           "config",         "Configuration",
                           "doctor",         "Check prerequisites",
                           "setup-rootless", "Rootless setup",
                           "quit",           "Exit")
        except KeyboardInterrupt:
            break

        if choice == "status":
            _run_cmd(d, "Status", *_wdt("status"))
        elif choice == "container":
            _menu_container(d)
        elif choice == "backup":
            _menu_backup(d)
        elif choice == "images":
            _menu_images(d)
        elif choice == "fleet":
            _menu_fleet(d)
        elif choice == "publish":
            _menu_publish(d)
        elif choice == "disk":
            _menu_disk(d)
        elif choice == "config":
            _menu_config(d)
        elif choice == "doctor":
            _run_cmd(d, "Doctor", *_wdt("doctor"))
        elif choice == "setup-rootless":
            _run_cmd(d, "Setup Rootless", *_wdt("setup-rootless"))
        elif choice == "quit":
            break


def _menu_container(d: str) -> None:
    while True:
        try:
            choice = _menu(d, "Container", "Select an action:",
                           "status",  "Show container status",
                           "start",   "Start container",
                           "stop",    "Stop container",
                           "shell",   "Open shell",
                           "upgrade", "Upgrade Android image (OTA)",
                           "back",    "Back")
        except KeyboardInterrupt:
            break

        if choice == "status":
            _run_cmd(d, "Container Status", *_wdt("status"))
        elif choice == "start":
            _run_cmd(d, "Start", *_wdt("container", "start"))
        elif choice == "stop":
            _run_cmd(d, "Stop", *_wdt("container", "stop"))
        elif choice == "shell":
            os.system("clear")
            _run_interactive(*_wdt("shell", "enter"))
        elif choice == "upgrade":
            _menu_upgrade(d)
        elif choice == "back":
            break


def _menu_upgrade(d: str) -> None:
    try:
        choice = _menu(d, "Upgrade", "Select action:",
                       "check", "Check for updates",
                       "apply", "Download and apply updates")
    except KeyboardInterrupt:
        return

    if choice == "check":
        _run_cmd(d, "Upgrade Check", *_wdt("upgrade", "check"))
    elif choice == "apply":
        if _yesno(d, "Apply Updates", "Download and apply the latest Waydroid images?"):
            _run_cmd(d, "Applying Updates", *_wdt("upgrade", "apply", "--yes"))


def _menu_backup(d: str) -> None:
    while True:
        try:
            choice = _menu(d, "Backup", "Select an action:",
                           "create",  "Create a backup",
                           "list",    "List backups",
                           "delete",  "Delete a backup",
                           "restore", "Restore from backup",
                           "back",    "Back")
        except KeyboardInterrupt:
            break

        if choice == "create":
            _run_cmd(d, "Creating Backup", *_wdt("backup", "create"))
        elif choice == "list":
            _run_cmd(d, "Backups", *_wdt("backup", "list"))
        elif choice == "delete":
            try:
                name = _input(d, "Delete Backup", "Backup archive name:")
            except KeyboardInterrupt:
                continue
            if name and _yesno(d, "Delete", f"Delete backup '{name}'?"):
                _run_cmd(d, "Deleting", *_wdt("backup", "delete", name, "--yes"))
        elif choice == "restore":
            try:
                src = _input(d, "Restore", "Backup archive path:")
            except KeyboardInterrupt:
                continue
            if src:
                _run_cmd(d, "Restoring", *_wdt("backup", "restore", src))
        elif choice == "back":
            break


def _menu_images(d: str) -> None:
    while True:
        try:
            choice = _menu(d, "Images", "Select an action:",
                           "list",   "List profiles",
                           "active", "Show active profile",
                           "switch", "Switch profile",
                           "check",  "Check for OTA updates",
                           "back",   "Back")
        except KeyboardInterrupt:
            break

        if choice == "list":
            _run_cmd(d, "Profiles", *_wdt("profiles", "list"))
        elif choice == "active":
            _run_cmd(d, "Active Profile", *_wdt("profiles", "active"))
        elif choice == "switch":
            try:
                name = _input(d, "Switch Profile", "Profile name:")
            except KeyboardInterrupt:
                continue
            if name:
                _run_cmd(d, f"Switching to {name}", *_wdt("profiles", "switch", name))
        elif choice == "check":
            _run_cmd(d, "OTA Check", *_wdt("upgrade", "check"))
        elif choice == "back":
            break


def _menu_fleet(d: str) -> None:
    while True:
        try:
            choice = _menu(d, "Fleet", "Select an action:",
                           "list",       "List all instances",
                           "status",     "Show fleet status",
                           "start-all",  "Start all stopped instances",
                           "stop-all",   "Stop all running instances",
                           "backup-all", "Backup all instances",
                           "back",       "Back")
        except KeyboardInterrupt:
            break

        if choice == "list":
            _run_cmd(d, "Fleet List", *_wdt("fleet", "list"))
        elif choice == "status":
            _run_cmd(d, "Fleet Status", *_wdt("fleet", "status"))
        elif choice == "start-all":
            _run_cmd(d, "Starting All", *_wdt("fleet", "start-all"))
        elif choice == "stop-all":
            if _yesno(d, "Stop All", "Stop all running Waydroid instances?"):
                _run_cmd(d, "Stopping All", *_wdt("fleet", "stop-all"))
        elif choice == "backup-all":
            _run_cmd(d, "Backing Up All", *_wdt("fleet", "backup-all"))
        elif choice == "back":
            break


def _menu_publish(d: str) -> None:
    try:
        choice = _menu(d, "Publish", "Select action:",
                       "create", "Publish container as image",
                       "list",   "List published images",
                       "delete", "Delete a published image")
    except KeyboardInterrupt:
        return

    if choice == "create":
        try:
            alias = _input(d, "Publish", "Image alias (e.g. waydroid/golden):",
                           "waydroid/published")
        except KeyboardInterrupt:
            return
        if alias:
            _run_cmd(d, "Publishing", *_wdt("publish", "create", "--alias", alias))
    elif choice == "list":
        _run_cmd(d, "Published Images", *_wdt("publish", "list"))
    elif choice == "delete":
        try:
            alias = _input(d, "Delete Image", "Image alias:")
        except KeyboardInterrupt:
            return
        if alias and _yesno(d, "Delete", f"Delete image '{alias}'?"):
            _run_cmd(d, "Deleting", *_wdt("publish", "delete", alias, "--yes"))


def _menu_disk(d: str) -> None:
    try:
        choice = _menu(d, "Disk", "Select action:",
                       "info",   "Show disk info",
                       "resize", "Resize root disk")
    except KeyboardInterrupt:
        return

    if choice == "info":
        _run_cmd(d, "Disk Info", *_wdt("disk", "info"))
    elif choice == "resize":
        try:
            size = _input(d, "Resize Disk", "New size (e.g. 20GB, +5GB):")
        except KeyboardInterrupt:
            return
        if size:
            _run_cmd(d, f"Resizing to {size}", *_wdt("disk", "resize", size))


def _menu_config(d: str) -> None:
    while True:
        try:
            choice = _menu(d, "Config", "Select action:",
                           "show", "Show current config",
                           "init", "Create default config",
                           "edit", "Edit config file",
                           "back", "Back")
        except KeyboardInterrupt:
            break

        if choice == "show":
            _run_cmd(d, "Config", *_wdt("config", "show"))
        elif choice == "init":
            _run_cmd(d, "Init Config", *_wdt("config", "init"))
        elif choice == "edit":
            os.system("clear")
            _run_interactive(*_wdt("config", "edit"))
        elif choice == "back":
            break


# ── entry point ───────────────────────────────────────────────────────────────

@click.command("tui")
def cmd() -> None:
    """Launch the interactive terminal UI (requires dialog or whiptail).

    \b
    Examples:
      wdt tui
    """
    dialog = _detect_dialog()
    if not dialog:
        console.print("[red]Neither dialog nor whiptail found.[/red]")
        console.print("Install with: [cyan]sudo apt install dialog[/cyan]")
        raise SystemExit(1)

    try:
        os.system("clear")
        _menu_main(dialog)
    except KeyboardInterrupt:
        pass
    finally:
        os.system("clear")
