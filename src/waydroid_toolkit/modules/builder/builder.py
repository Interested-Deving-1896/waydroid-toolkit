"""Android image builder — delegates to the penguins-eggs CLI.

penguins-eggs is a Node.js/TypeScript tool that builds Android images
(system.img, boot.img, ISOs, OTA zips). This module locates or installs
the `eggs` CLI and invokes `eggs android build`, then reads the
waydroid-image-manifest.json it produces.

Auto-install behaviour
----------------------
If `eggs` is not on PATH, the module runs:
    npm install -g penguins-eggs
using whatever `npm` is available. If npm itself is absent, a clear
error is raised with install instructions.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from waydroid_toolkit.utils.android_shared import AndroidShared

_EGGS_PACKAGE = "penguins-eggs"
_MANIFEST_FILENAME = "waydroid-image-manifest.json"


# ── eggs CLI detection + auto-install ────────────────────────────────────────

def find_eggs() -> str | None:
    """Return the path to the `eggs` binary, or None if not found."""
    return shutil.which("eggs")


def install_eggs(progress: Callable[[str], None] | None = None) -> str:
    """Install penguins-eggs globally via npm.

    Returns the path to the installed `eggs` binary.
    Raises RuntimeError if npm is not available or installation fails.
    """
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError(
            "npm is required to auto-install penguins-eggs but was not found. "
            "Install Node.js >= 22 from https://nodejs.org then re-run wdt build."
        )

    if progress:
        progress(f"Installing {_EGGS_PACKAGE} via npm (this may take a minute)...")

    result = subprocess.run(
        [npm, "install", "-g", _EGGS_PACKAGE],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"npm install -g {_EGGS_PACKAGE} failed:\n{result.stderr.strip()}"
        )

    eggs = find_eggs()
    if eggs is None:
        raise RuntimeError(
            f"{_EGGS_PACKAGE} was installed but `eggs` binary not found on PATH. "
            "You may need to add the npm global bin directory to your PATH."
        )

    if progress:
        progress(f"penguins-eggs installed at {eggs}.")
    return eggs


def ensure_eggs(progress: Callable[[str], None] | None = None) -> str:
    """Return path to `eggs`, auto-installing if necessary."""
    eggs = find_eggs()
    if eggs is not None:
        return eggs
    if progress:
        progress("penguins-eggs not found — installing automatically...")
    return install_eggs(progress)


# ── Manifest reading ──────────────────────────────────────────────────────────

def read_manifest(manifest_path: Path) -> dict:
    """Read and validate a waydroid-image-manifest.json.

    Raises FileNotFoundError, ValueError, or json.JSONDecodeError on failure.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    data = json.loads(manifest_path.read_text())

    version = data.get(AndroidShared.MANIFEST_VERSION, "")
    if not AndroidShared.is_manifest_version_supported(version):
        raise ValueError(
            f"Unsupported manifest version '{version}' in {manifest_path}. "
            f"Expected '{AndroidShared.MANIFEST_SCHEMA_VER}'."
        )

    variant = data.get(AndroidShared.MANIFEST_VARIANT, "")
    if not AndroidShared.is_known_variant(variant):
        raise ValueError(
            f"Unknown Android variant '{variant}' in manifest."
        )

    return data


# ── Build orchestration ───────────────────────────────────────────────────────

def build_android_image(
    output_dir: Path,
    variant: str = AndroidShared.VARIANT_WAYDROID,
    arch: str = AndroidShared.ABI_X8664,
    avb_sign: bool = False,
    extra_args: list[str] | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Build an Android image using penguins-eggs and return the manifest.

    Runs: eggs android build --variant <variant> --arch <arch> --output <dir>
    Then reads and returns the waydroid-image-manifest.json written by eggs.

    Parameters
    ----------
    output_dir:  Directory where eggs writes the image files and manifest.
    variant:     Android variant (default: "waydroid").
    arch:        Target ABI (default: "x86_64").
    avb_sign:    Whether to request AVB signing from eggs.
    extra_args:  Additional arguments forwarded verbatim to `eggs android build`.
    progress:    Optional callback for progress messages.

    Returns the parsed manifest dict.
    """
    if not AndroidShared.is_known_variant(variant):
        raise ValueError(f"Unknown variant '{variant}'. "
                         f"Valid values: waydroid, blissos, aosp, grapheneos, "
                         f"lineageos, cuttlefish, bassos, custom.")

    output_dir.mkdir(parents=True, exist_ok=True)
    eggs = ensure_eggs(progress)

    cmd = [
        eggs, "android", "build",
        "--variant", variant,
        "--arch", arch,
        "--output", str(output_dir),
    ]
    if avb_sign:
        cmd.append("--avb-sign")
    if extra_args:
        cmd.extend(extra_args)

    if progress:
        progress(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"eggs android build failed with exit code {result.returncode}."
        )

    manifest_path = output_dir / _MANIFEST_FILENAME
    if progress:
        progress("Reading image manifest...")
    return read_manifest(manifest_path)
