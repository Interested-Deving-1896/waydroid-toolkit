"""WayDroid Toolkit CLI entry point.

Usage:
    wdt [OPTIONS] COMMAND [ARGS]...

Commands:
    status        Show Waydroid runtime status
    install       Install Waydroid on this system
    build         Build an Android image via penguins-eggs
    gui           Launch the Qt/QML graphical interface
    backend       Select and inspect the container backend (LXC or Incus)
    extensions    Manage extensions (GApps, Magisk, ARM translation, microG)
    images        Manage image profiles
    packages      Install/remove Android apps and manage F-Droid repos
    backup        Backup and restore Waydroid data
    performance   Apply/remove host performance tuning
    maintenance   Display settings, screenshots, logcat, file transfer, debloat
"""

import click
from rich.console import Console

from waydroid_toolkit import __version__

from .commands import (
    assemble,
    backend,
    backup,
    build,
    cloud_sync,
    container,
    dbus,
    doctor,
    extensions,
    images,
    install,
    maintenance,
    monitor,
    packages,
    performance,
    snapshot,
    status,
    template,
    update,
)

console = Console()

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _gui_cmd() -> click.Command:
    @click.command("gui")
    def _cmd() -> None:
        """Launch the Qt/QML graphical interface."""
        import sys
        try:
            from waydroid_toolkit.gui.app import run
        except ImportError as exc:
            Console().print(
                f"[red]Qt GUI dependencies not installed:[/red] {exc}\n"
                "Install with: pip install 'waydroid-toolkit[gui]'"
            )
            raise SystemExit(1) from exc
        sys.exit(run())
    return _cmd


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, "-v", "--version", prog_name="wdt")
def cli() -> None:
    """WayDroid Toolkit — unified management suite for Waydroid."""


cli.add_command(status.cmd, name="status")
cli.add_command(doctor.cmd, name="doctor")
cli.add_command(assemble.cmd, name="assemble")
cli.add_command(monitor.cmd, name="monitor")
cli.add_command(install.cmd, name="install")
cli.add_command(build.cmd, name="build")
cli.add_command(_gui_cmd(), name="gui")
cli.add_command(backend.cmd, name="backend")
cli.add_command(extensions.cmd, name="extensions")
cli.add_command(images.cmd, name="images")
cli.add_command(packages.cmd, name="packages")
cli.add_command(backup.cmd, name="backup")
cli.add_command(performance.cmd, name="performance")
cli.add_command(maintenance.cmd, name="maintenance")
cli.add_command(snapshot.cmd, name="snapshot")
cli.add_command(container.cmd, name="container")
cli.add_command(cloud_sync.cmd, name="cloud-sync")
cli.add_command(template.cmd, name="template")
cli.add_command(update.cmd, name="update")
cli.add_command(dbus.cmd, name="dbus")
