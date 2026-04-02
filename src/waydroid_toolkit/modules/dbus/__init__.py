"""D-Bus service mode for waydroid-toolkit.

Exposes core toolkit operations over the session bus so that GUI frontends,
scripts, and other processes can call them without spawning a new process.

Bus name  : io.github.waydroid_toolkit
Object    : /io/github/waydroid_toolkit
Interface : io.github.waydroid_toolkit.Manager

Usage
-----
    from waydroid_toolkit.modules.dbus import WdtService
    service = WdtService()
    service.run()          # blocks until SIGTERM / Stop() called
"""

from .service import WdtService

__all__ = ["WdtService"]
