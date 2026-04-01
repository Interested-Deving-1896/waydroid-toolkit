"""WayDroid Toolkit CLI entry point.

Usage:
    wdt [OPTIONS] COMMAND [ARGS]...

Commands:
    status        Show Waydroid runtime status
    install       Install Waydroid on this system
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
from .commands import backup, extensions, images, install, maintenance, packages, performance, status

console = Console()

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, "-v", "--version", prog_name="wdt")
def cli() -> None:
    """WayDroid Toolkit — unified management suite for Waydroid."""


cli.add_command(status.cmd, name="status")
cli.add_command(install.cmd, name="install")
cli.add_command(extensions.cmd, name="extensions")
cli.add_command(images.cmd, name="images")
cli.add_command(packages.cmd, name="packages")
cli.add_command(backup.cmd, name="backup")
cli.add_command(performance.cmd, name="performance")
cli.add_command(maintenance.cmd, name="maintenance")
