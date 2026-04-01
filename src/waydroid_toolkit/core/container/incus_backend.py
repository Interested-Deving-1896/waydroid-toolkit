"""Incus container backend.

Wraps the `incus` CLI (https://github.com/lxc/incus).

Incus is built on top of liblxc — the same library that LXC tools use —
so it can run the Waydroid Android container with identical kernel-level
behaviour. Android-specific configuration (binder device nodes, seccomp
profile, AppArmor) is passed through via Incus's `raw.lxc` config key,
which injects directives directly into the underlying LXC config.

Setup requirements
------------------
Before switching to this backend the Waydroid container must be imported
into Incus. WayDroid Toolkit provides `wdt backend incus setup` to do this
automatically. The setup command:

  1. Reads the existing LXC container config from /var/lib/lxc/waydroid/
  2. Creates an Incus container named "waydroid" with equivalent config
  3. Passes all lxc.mount.entry and lxc.seccomp.profile directives through
     raw.lxc so the Android environment is identical

This toolkit does not modify upstream waydroid/waydroid. The waydroid daemon
continues to manage its own LXC config files; the Incus backend reads those
files and mirrors them into Incus on setup.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .base import BackendInfo, BackendType, ContainerBackend, ContainerState

_LXC_CONFIG_PATH = Path("/var/lib/lxc/waydroid/config")
_LXC_NODES_PATH = Path("/var/lib/lxc/waydroid/config_nodes")
_LXC_SESSION_PATH = Path("/var/lib/lxc/waydroid/config_session")
_LXC_SECCOMP_PATH = Path("/var/lib/lxc/waydroid/waydroid.seccomp")


class IncusBackend(ContainerBackend):
    """Backend that delegates to the `incus` CLI."""

    @property
    def backend_type(self) -> BackendType:
        return BackendType.INCUS

    def is_available(self) -> bool:
        return shutil.which("incus") is not None

    def get_info(self) -> BackendInfo:
        version = "unknown"
        if self.is_available():
            result = subprocess.run(
                ["incus", "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Output: "Client version: 6.x\nServer version: 6.x"
                for line in result.stdout.splitlines():
                    if "client" in line.lower():
                        version = line.split(":", 1)[-1].strip()
                        break
        return BackendInfo(
            backend_type=BackendType.INCUS,
            binary="incus",
            version=version,
            container_name=self.CONTAINER_NAME,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        subprocess.run(
            ["incus", "start", self.CONTAINER_NAME],
            check=True,
        )

    def stop(self, timeout: int = 10) -> None:
        subprocess.run(
            ["incus", "stop", self.CONTAINER_NAME, "--timeout", str(timeout)],
            check=True,
        )

    def freeze(self) -> None:
        subprocess.run(
            ["incus", "pause", self.CONTAINER_NAME],
            check=True,
        )

    def unfreeze(self) -> None:
        # Incus resumes a paused container with `start`
        subprocess.run(
            ["incus", "start", self.CONTAINER_NAME],
            check=True,
        )

    # ── Introspection ─────────────────────────────────────────────────────────

    def get_state(self) -> ContainerState:
        if not self.is_available():
            return ContainerState.UNKNOWN
        try:
            result = subprocess.run(
                ["incus", "info", self.CONTAINER_NAME, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return ContainerState.UNKNOWN
            data = json.loads(result.stdout)
            status = data.get("status", "").lower()
            mapping = {
                "running": ContainerState.RUNNING,
                "stopped": ContainerState.STOPPED,
                "frozen": ContainerState.FROZEN,
            }
            return mapping.get(status, ContainerState.UNKNOWN)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            return ContainerState.UNKNOWN

    # ── Execution ─────────────────────────────────────────────────────────────

    def execute(
        self,
        cmd: list[str],
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["incus", "exec", self.CONTAINER_NAME, "--"] + cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    # ── Incus-specific: setup from existing LXC config ────────────────────────

    def container_exists(self) -> bool:
        """Return True if the waydroid container exists in Incus."""
        result = subprocess.run(
            ["incus", "info", self.CONTAINER_NAME],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0

    def setup_from_lxc(self) -> None:
        """Import the Waydroid LXC container config into Incus.

        Reads the LXC config files written by upstream waydroid/waydroid
        and creates an equivalent Incus container, passing Android-specific
        directives through raw.lxc.

        Raises RuntimeError if the LXC config files are not present
        (i.e. waydroid has not been initialised yet).
        """
        if not _LXC_CONFIG_PATH.exists():
            raise RuntimeError(
                "LXC config not found at /var/lib/lxc/waydroid/config. "
                "Run 'wdt install' or 'waydroid init' first."
            )

        raw_lxc_lines = self._collect_raw_lxc_directives()

        if self.container_exists():
            # Remove and recreate to apply fresh config
            subprocess.run(
                ["incus", "delete", self.CONTAINER_NAME, "--force"],
                check=True,
            )

        # Create an empty container using the local rootfs
        # Incus needs a base image; we use the existing rootfs path from
        # the waydroid LXC config rather than pulling a remote image.
        rootfs = self._get_rootfs_path()
        subprocess.run(
            [
                "incus", "init", "--empty", self.CONTAINER_NAME,
                "--config", f"raw.lxc={raw_lxc_lines}",
            ],
            check=True,
        )

        # Point Incus at the same rootfs waydroid uses
        subprocess.run(
            [
                "incus", "config", "device", "add", self.CONTAINER_NAME,
                "root", "disk",
                "path=/",
                f"source={rootfs}",
            ],
            check=True,
        )

        # Copy seccomp profile if present
        if _LXC_SECCOMP_PATH.exists():
            subprocess.run(
                [
                    "incus", "config", "set", self.CONTAINER_NAME,
                    "raw.lxc",
                    f"lxc.seccomp.profile={_LXC_SECCOMP_PATH}",
                ],
                check=True,
            )

    def _collect_raw_lxc_directives(self) -> str:
        """Read mount entries and other directives from the LXC config files
        and return them as a newline-joined string for raw.lxc injection."""
        lines: list[str] = []
        for path in (_LXC_CONFIG_PATH, _LXC_NODES_PATH, _LXC_SESSION_PATH):
            if not path.exists():
                continue
            for line in path.read_text().splitlines():
                stripped = line.strip()
                # Pass through mount entries, seccomp, apparmor, cgroup rules
                if any(
                    stripped.startswith(prefix)
                    for prefix in (
                        "lxc.mount.entry",
                        "lxc.seccomp",
                        "lxc.apparmor",
                        "lxc.cgroup",
                        "lxc.cap",
                        "lxc.aa_",
                    )
                ):
                    lines.append(stripped)
        return "\n".join(lines)

    def _get_rootfs_path(self) -> str:
        """Extract lxc.rootfs.path from the LXC config."""
        for line in _LXC_CONFIG_PATH.read_text().splitlines():
            if line.strip().startswith("lxc.rootfs.path"):
                return line.split("=", 1)[-1].strip()
        return "/var/lib/waydroid/rootfs"
