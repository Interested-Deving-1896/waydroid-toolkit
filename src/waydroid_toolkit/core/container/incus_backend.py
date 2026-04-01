"""Incus container backend.

Wraps the `incus` CLI (https://github.com/lxc/incus).

Incus is built on top of liblxc — the same library that LXC tools use —
so it can run the Waydroid Android container with identical kernel-level
behaviour.

Gap coverage vs. the LXC backend
----------------------------------
All six gap categories identified from upstream waydroid/waydroid
tools/helpers/lxc.py are handled here:

  1. Device nodes       — added as native `incus config device add` calls
                          (unix-char) with required=false for optional nodes,
                          enabling Incus introspection and hotplugging.
  2. tmpfs + bind mounts — added as `disk` devices (vendor, sys nodes, wslg,
                          dev/, tmp/, var/, run/).
  3. Session mounts     — configure_session() applies per-session Wayland
                          socket, PulseAudio socket, and userdata bind mounts
                          dynamically at session start.
  4. Android env vars   — execute() passes the full ANDROID_ENV dict via
                          `incus exec --env` so Android PATH and runtime
                          roots are correct inside the container.
  5. Exec privileges    — execute() accepts uid, gid, and disable_apparmor
                          parameters, mapping to `incus exec --user` and
                          `--disable-apparmor`.
  6. raw.lxc merge      — setup_from_lxc() collects ALL raw.lxc directives
                          (mount entries, seccomp, AppArmor, cgroup, caps)
                          into a single merged string and applies them in one
                          `incus config set` call so nothing overwrites
                          anything else.

This toolkit does not modify upstream waydroid/waydroid. The waydroid daemon
continues to manage its own LXC config files; the Incus backend reads those
files and mirrors them into Incus on setup.
"""

from __future__ import annotations

import glob
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .base import BackendInfo, BackendType, ContainerBackend, ContainerState

# ── Paths written by upstream waydroid/waydroid ───────────────────────────────
_LXC_CONFIG_PATH = Path("/var/lib/lxc/waydroid/config")
_LXC_NODES_PATH = Path("/var/lib/lxc/waydroid/config_nodes")
_LXC_SESSION_PATH = Path("/var/lib/lxc/waydroid/config_session")
_LXC_SECCOMP_PATH = Path("/var/lib/lxc/waydroid/waydroid.seccomp")

# ── Android environment ───────────────────────────────────────────────────────
# Mirrors ANDROID_ENV in upstream tools/helpers/lxc.py.
# Passed to every `incus exec` call via --env so Android binaries find
# their runtime roots correctly (equivalent to lxc-attach --clear-env
# --set-var KEY=VALUE ...).
ANDROID_ENV: dict[str, str] = {
    "PATH": (
        "/product/bin:/apex/com.android.runtime/bin:/apex/com.android.art/bin"
        ":/system_ext/bin:/system/bin:/system/xbin:/odm/bin:/vendor/bin:/vendor/xbin"
    ),
    "ANDROID_ROOT": "/system",
    "ANDROID_DATA": "/data",
    "ANDROID_STORAGE": "/storage",
    "ANDROID_ART_ROOT": "/apex/com.android.art",
    "ANDROID_I18N_ROOT": "/apex/com.android.i18n",
    "ANDROID_TZDATA_ROOT": "/apex/com.android.tzdata",
    "ANDROID_RUNTIME_ROOT": "/apex/com.android.runtime",
    "BOOTCLASSPATH": (
        "/apex/com.android.art/javalib/core-oj.jar"
        ":/apex/com.android.art/javalib/core-libart.jar"
        ":/apex/com.android.art/javalib/core-icu4j.jar"
        ":/apex/com.android.art/javalib/okhttp.jar"
        ":/apex/com.android.art/javalib/bouncycastle.jar"
        ":/apex/com.android.art/javalib/apache-xml.jar"
        ":/system/framework/framework.jar"
        ":/system/framework/ext.jar"
        ":/system/framework/telephony-common.jar"
        ":/system/framework/voip-common.jar"
        ":/system/framework/ims-common.jar"
        ":/system/framework/framework-atb-backward-compatibility.jar"
        ":/apex/com.android.conscrypt/javalib/conscrypt.jar"
        ":/apex/com.android.media/javalib/updatable-media.jar"
        ":/apex/com.android.mediaprovider/javalib/framework-mediaprovider.jar"
        ":/apex/com.android.os.statsd/javalib/framework-statsd.jar"
        ":/apex/com.android.permission/javalib/framework-permission.jar"
        ":/apex/com.android.sdkext/javalib/framework-sdkextensions.jar"
        ":/apex/com.android.wifi/javalib/framework-wifi.jar"
        ":/apex/com.android.tethering/javalib/framework-tethering.jar"
    ),
}

# ── Device descriptors ────────────────────────────────────────────────────────

@dataclass
class _CharDevice:
    name: str       # unique Incus device name
    source: str     # host path
    path: str       # container path
    required: bool = False


@dataclass
class _DiskMount:
    name: str
    source: str     # host path or "tmpfs"
    path: str       # container mount point
    required: bool = False
    readonly: bool = False


def _static_char_devices() -> list[_CharDevice]:
    """Fixed character devices Waydroid always needs."""
    return [
        # Binder IPC
        _CharDevice("binder",    "/dev/binder",    "/dev/binder"),
        _CharDevice("vndbinder", "/dev/vndbinder",  "/dev/vndbinder"),
        _CharDevice("hwbinder",  "/dev/hwbinder",   "/dev/hwbinder"),
        # Core Android nodes
        _CharDevice("ashmem",    "/dev/ashmem",     "/dev/ashmem"),
        _CharDevice("fuse",      "/dev/fuse",       "/dev/fuse"),
        _CharDevice("ion",       "/dev/ion",        "/dev/ion"),
        _CharDevice("tty",       "/dev/tty",        "/dev/tty"),
        # ADB
        _CharDevice("uhid",      "/dev/uhid",       "/dev/uhid"),
        # VPN
        _CharDevice("tun",       "/dev/net/tun",    "/dev/tun"),
        # HWC sync
        _CharDevice("sw_sync",   "/dev/sw_sync",    "/dev/sw_sync"),
        # GPU — Qualcomm / ARM / PowerVR / PMSG
        _CharDevice("kgsl3d0",   "/dev/kgsl-3d0",   "/dev/kgsl-3d0"),
        _CharDevice("mali0",     "/dev/mali0",      "/dev/mali0"),
        _CharDevice("pvr_sync",  "/dev/pvr_sync",   "/dev/pvr_sync"),
        _CharDevice("pmsg0",     "/dev/pmsg0",      "/dev/pmsg0"),
        # WSLg / DirectX
        _CharDevice("dxg",       "/dev/dxg",        "/dev/dxg"),
        # Mediatek media
        _CharDevice("vcodec",    "/dev/Vcodec",     "/dev/Vcodec"),
        _CharDevice("mtk_smi",   "/dev/MTK_SMI",    "/dev/MTK_SMI"),
        _CharDevice("mdp_sync",  "/dev/mdp_sync",   "/dev/mdp_sync"),
        _CharDevice("mtk_cmdq",  "/dev/mtk_cmdq",   "/dev/mtk_cmdq"),
    ]


def _glob_char_devices() -> list[_CharDevice]:
    """Character devices discovered by glob at setup time (DRI, fb, video, dma_heap)."""
    devices: list[_CharDevice] = []
    for pattern, prefix in (
        ("/dev/dri/renderD*", "dri_render_"),
        ("/dev/fb*",          "fb_"),
        ("/dev/graphics/fb*", "gfx_fb_"),
        ("/dev/video*",       "video_"),
        ("/dev/dma_heap/*",   "dma_heap_"),
    ):
        for host_path in glob.glob(pattern):
            node_name = prefix + Path(host_path).name
            devices.append(_CharDevice(node_name, host_path, host_path))
    return devices


def _static_disk_mounts() -> list[_DiskMount]:
    """Fixed filesystem mounts Waydroid always needs."""
    return [
        # tmpfs overlays Android expects as writable RAM disks
        _DiskMount("dev_tmpfs",    "tmpfs",  "/dev"),
        _DiskMount("tmp_tmpfs",    "tmpfs",  "/tmp"),
        _DiskMount("var_tmpfs",    "tmpfs",  "/var"),
        _DiskMount("run_tmpfs",    "tmpfs",  "/run"),
        _DiskMount("mnt_extra",    "tmpfs",  "/mnt_extra"),
        # Host vendor partition — Android HALs live here
        _DiskMount("vendor_extra", "/vendor", "/vendor_extra"),
        # sysfs nodes
        _DiskMount(
            "lowmemkiller",
            "/sys/module/lowmemorykiller",
            "/sys/module/lowmemorykiller",
        ),
        _DiskMount(
            "kernel_debug",
            "/sys/kernel/debug",
            "/sys/kernel/debug",
        ),
        _DiskMount(
            "vibrator_leds",
            "/sys/class/leds/vibrator",
            "/sys/class/leds/vibrator",
        ),
        _DiskMount(
            "vibrator_timed",
            "/sys/devices/virtual/timed_output/vibrator",
            "/sys/devices/virtual/timed_output/vibrator",
        ),
        # WSLg
        _DiskMount("wslg", "/mnt/wslg", "/mnt_extra/wslg"),
    ]


# ── Session config ────────────────────────────────────────────────────────────

@dataclass
class SessionConfig:
    """Per-session mount parameters.

    Mirrors the inputs to generate_session_lxc_config() in upstream lxc.py.
    """
    wayland_host_socket: str       # e.g. /run/user/1000/wayland-0
    wayland_container_socket: str  # e.g. /run/waydroid-session/wayland-0
    pulse_host_socket: str         # e.g. /run/user/1000/pulse/native
    pulse_container_socket: str    # e.g. /run/waydroid-session/pulse/native
    waydroid_data: str             # e.g. ~/.local/share/waydroid/data
    xdg_runtime_dir: str           # container XDG_RUNTIME_DIR path


# ── IncusBackend ──────────────────────────────────────────────────────────────

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
        subprocess.run(["incus", "start", self.CONTAINER_NAME], check=True)

    def stop(self, timeout: int = 10) -> None:
        subprocess.run(
            ["incus", "stop", self.CONTAINER_NAME, "--timeout", str(timeout)],
            check=True,
        )

    def freeze(self) -> None:
        subprocess.run(["incus", "pause", self.CONTAINER_NAME], check=True)

    def unfreeze(self) -> None:
        # Incus resumes a paused container with start
        subprocess.run(["incus", "start", self.CONTAINER_NAME], check=True)

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
            return {
                "running": ContainerState.RUNNING,
                "stopped": ContainerState.STOPPED,
                "frozen":  ContainerState.FROZEN,
            }.get(status, ContainerState.UNKNOWN)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            return ContainerState.UNKNOWN

    # ── Execution ─────────────────────────────────────────────────────────────

    def execute(
        self,
        cmd: list[str],
        timeout: int = 30,
        uid: int | None = None,
        gid: int | None = None,
        disable_apparmor: bool = False,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run cmd inside the container with the correct Android environment.

        Parameters
        ----------
        cmd:              Command and arguments to run.
        timeout:          Subprocess timeout in seconds.
        uid:              Run as this UID (mirrors lxc-attach --uid).
        gid:              Run as this GID; defaults to uid if omitted.
        disable_apparmor: Bypass AppArmor profile (mirrors
                          lxc-attach --elevated-privileges=LSM).
        extra_env:        Additional env vars merged on top of ANDROID_ENV.
        """
        env = {**ANDROID_ENV, **(extra_env or {})}

        incus_cmd: list[str] = ["incus", "exec", self.CONTAINER_NAME]

        for key, value in env.items():
            incus_cmd += ["--env", f"{key}={value}"]

        if uid is not None:
            effective_gid = gid if gid is not None else uid
            incus_cmd += ["--user", f"{uid}:{effective_gid}"]

        if disable_apparmor:
            incus_cmd.append("--disable-apparmor")

        incus_cmd += ["--"] + cmd

        return subprocess.run(
            incus_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    # ── Session configuration ─────────────────────────────────────────────────

    def configure_session(self, session: SessionConfig) -> None:
        """Apply per-session mounts to the container.

        Mirrors generate_session_lxc_config() in upstream lxc.py.
        Must be called at session start; call remove_session_devices()
        at session stop.
        """
        for name, device_args in self._session_device_specs(session).items():
            # Remove stale device from a previous session if present
            subprocess.run(
                ["incus", "config", "device", "remove",
                 self.CONTAINER_NAME, name],
                capture_output=True,
            )
            subprocess.run(
                ["incus", "config", "device", "add",
                 self.CONTAINER_NAME, name] + device_args,
                check=True,
            )

    def remove_session_devices(self, session: SessionConfig) -> None:
        """Remove per-session devices added by configure_session()."""
        for name in self._session_device_specs(session):
            subprocess.run(
                ["incus", "config", "device", "remove",
                 self.CONTAINER_NAME, name],
                capture_output=True,
            )

    def _session_device_specs(
        self, session: SessionConfig,
    ) -> dict[str, list[str]]:
        return {
            "session_xdg_tmpfs": [
                "disk",
                "source=tmpfs",
                f"path={session.xdg_runtime_dir}",
            ],
            "session_wayland": [
                "disk",
                f"source={session.wayland_host_socket}",
                f"path={session.wayland_container_socket}",
            ],
            "session_pulse": [
                "disk",
                f"source={session.pulse_host_socket}",
                f"path={session.pulse_container_socket}",
            ],
            "session_data": [
                "disk",
                f"source={session.waydroid_data}",
                "path=/data",
            ],
        }

    # ── Setup from existing LXC config ───────────────────────────────────────

    def container_exists(self) -> bool:
        result = subprocess.run(
            ["incus", "info", self.CONTAINER_NAME],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0

    def setup_from_lxc(self) -> None:
        """Import the Waydroid LXC container config into Incus.

        Steps:
          1. Collect ALL raw.lxc directives into one merged string (fixes
             the overwrite bug where separate config set calls clobber each
             other).
          2. Create an empty Incus container with the merged raw.lxc value.
          3. Add the rootfs as a disk device.
          4. Add each character device node as a native unix-char device.
          5. Add tmpfs and bind-mount disk devices.

        Raises RuntimeError if waydroid has not been initialised yet.
        """
        if not _LXC_CONFIG_PATH.exists():
            raise RuntimeError(
                "LXC config not found at /var/lib/lxc/waydroid/config. "
                "Run 'wdt install' or 'waydroid init' first."
            )

        if self.container_exists():
            subprocess.run(
                ["incus", "delete", self.CONTAINER_NAME, "--force"],
                check=True,
            )

        # Step 1 + 2: merged raw.lxc → single config set
        raw_lxc = self._collect_raw_lxc_directives()
        subprocess.run(
            [
                "incus", "init", "--empty", self.CONTAINER_NAME,
                "--config", f"raw.lxc={raw_lxc}",
            ],
            check=True,
        )

        # Step 3: rootfs
        rootfs = self._get_rootfs_path()
        subprocess.run(
            [
                "incus", "config", "device", "add", self.CONTAINER_NAME,
                "root", "disk", "path=/", f"source={rootfs}",
            ],
            check=True,
        )

        # Step 4: character device nodes
        for dev in _static_char_devices() + _glob_char_devices():
            if not Path(dev.source).exists():
                continue
            subprocess.run(
                [
                    "incus", "config", "device", "add", self.CONTAINER_NAME,
                    dev.name, "unix-char",
                    f"source={dev.source}",
                    f"path={dev.path}",
                    "required=false",
                ],
                check=True,
            )

        # Step 5: tmpfs and bind-mount disk devices
        for mount in _static_disk_mounts():
            if mount.source != "tmpfs" and not Path(mount.source).exists():
                continue
            args = [
                "incus", "config", "device", "add", self.CONTAINER_NAME,
                mount.name, "disk",
                f"source={mount.source}",
                f"path={mount.path}",
            ]
            if mount.readonly:
                args.append("readonly=true")
            subprocess.run(args, check=True)

    def _collect_raw_lxc_directives(self) -> str:
        """Collect all passthrough LXC directives from waydroid config files.

        Merges config, config_nodes, and config_session into one string.
        Appends the seccomp profile path if the file exists and is not
        already referenced. This single string is passed to raw.lxc in one
        call, preventing the overwrite bug.
        """
        _PASS_PREFIXES = (
            "lxc.mount.entry",
            "lxc.seccomp",
            "lxc.apparmor",
            "lxc.aa_",
            "lxc.cgroup",
            "lxc.cap",
        )
        lines: list[str] = []
        for path in (_LXC_CONFIG_PATH, _LXC_NODES_PATH, _LXC_SESSION_PATH):
            if not path.exists():
                continue
            for line in path.read_text().splitlines():
                stripped = line.strip()
                if any(stripped.startswith(p) for p in _PASS_PREFIXES):
                    lines.append(stripped)

        # Append seccomp path if present and not already in config
        if _LXC_SECCOMP_PATH.exists() and not any(
            "lxc.seccomp" in ln for ln in lines
        ):
            lines.append(f"lxc.seccomp.profile={_LXC_SECCOMP_PATH}")

        return "\n".join(lines)

    def _get_rootfs_path(self) -> str:
        for line in _LXC_CONFIG_PATH.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("lxc.rootfs.path"):
                return stripped.split("=", 1)[-1].strip()
        return "/var/lib/waydroid/rootfs"
