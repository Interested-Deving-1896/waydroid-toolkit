"""LXC container backend.

Wraps the lxc-* CLI tools (lxc-start, lxc-stop, lxc-attach, lxc-info)
that upstream waydroid/waydroid configures and uses internally.

This backend is the default and matches the behaviour of a standard
Waydroid installation.

Write-operation gating
----------------------
Snapshot, console, and other write operations that have no safe LXC
equivalent raise ``NotImplementedError`` with a message directing the
user to switch to the Incus backend.  Read-only operations (state,
execute) continue to work on LXC.
"""

from __future__ import annotations

import shutil
import subprocess

from .base import BackendInfo, BackendType, ContainerBackend, ContainerState

_INCUS_ONLY_MSG = (
    "This operation requires the Incus backend.\n"
    "Switch with: wdt backend set incus"
)


class LxcBackend(ContainerBackend):
    """Backend that delegates to lxc-* binaries."""

    # lxc-* tools use a path-based container layout; Waydroid sets this up
    # via waydroid init. We call the same binaries waydroid itself uses.
    _BINARIES = {
        "start": "lxc-start",
        "stop": "lxc-stop",
        "attach": "lxc-attach",
        "info": "lxc-info",
        "freeze": "lxc-freeze",
        "unfreeze": "lxc-unfreeze",
    }

    @property
    def backend_type(self) -> BackendType:
        return BackendType.LXC

    def is_available(self) -> bool:
        return shutil.which(self._BINARIES["start"]) is not None

    def get_info(self) -> BackendInfo:
        version = "unknown"
        if shutil.which(self._BINARIES["info"]):
            result = subprocess.run(
                [self._BINARIES["info"], "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
        return BackendInfo(
            backend_type=BackendType.LXC,
            binary=self._BINARIES["start"],
            version=version,
            container_name=self.CONTAINER_NAME,
        )

    def start(self) -> None:
        subprocess.run(
            ["sudo", self._BINARIES["start"], "-n", self.CONTAINER_NAME],
            check=True,
        )

    def stop(self, timeout: int = 10) -> None:
        subprocess.run(
            [
                "sudo", self._BINARIES["stop"],
                "-n", self.CONTAINER_NAME,
                "-t", str(timeout),
            ],
            check=True,
        )

    def freeze(self) -> None:
        subprocess.run(
            ["sudo", self._BINARIES["freeze"], "-n", self.CONTAINER_NAME],
            check=True,
        )

    def unfreeze(self) -> None:
        subprocess.run(
            ["sudo", self._BINARIES["unfreeze"], "-n", self.CONTAINER_NAME],
            check=True,
        )

    def get_state(self) -> ContainerState:
        if not self.is_available():
            return ContainerState.UNKNOWN
        try:
            result = subprocess.run(
                [self._BINARIES["info"], "-n", self.CONTAINER_NAME, "--state"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = result.stdout.lower()
            if "running" in output:
                return ContainerState.RUNNING
            if "frozen" in output:
                return ContainerState.FROZEN
            if "stopped" in output:
                return ContainerState.STOPPED
            return ContainerState.UNKNOWN
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ContainerState.UNKNOWN

    def execute(
        self,
        cmd: list[str],
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sudo", self._BINARIES["attach"], "-n", self.CONTAINER_NAME, "--"] + cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    # ── Snapshots (Incus-only) ────────────────────────────────────────────────

    def snapshot_create(self, name: str) -> None:  # noqa: ARG002
        raise NotImplementedError(_INCUS_ONLY_MSG)

    def snapshot_list(self) -> list[str]:
        raise NotImplementedError(_INCUS_ONLY_MSG)

    def snapshot_restore(self, name: str) -> None:  # noqa: ARG002
        raise NotImplementedError(_INCUS_ONLY_MSG)

    def snapshot_delete(self, name: str) -> None:  # noqa: ARG002
        raise NotImplementedError(_INCUS_ONLY_MSG)

    # ── Console (Incus-only) ──────────────────────────────────────────────────

    def console(self) -> None:
        raise NotImplementedError(_INCUS_ONLY_MSG)
