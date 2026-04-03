"""Unit tests for waydroid_toolkit.modules.storage.nfs"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.storage.nfs import (
    NfsMount,
    add_nfs_mount,
    list_nfs_mounts,
    remove_nfs_mount,
)


# ── add_nfs_mount ─────────────────────────────────────────────────────────────

class TestAddNfsMount:
    def test_basic_nfs(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch(
                "waydroid_toolkit.modules.storage.nfs._container_name",
                return_value="waydroid",
            ):
                mount = add_nfs_mount("192.168.1.10:/exports/assets")

        assert mount.source == "192.168.1.10:/exports/assets"
        assert mount.container_path == "/data/shared"
        assert mount.mount_type == "nfs"
        assert mount.options == "soft,async"
        assert mount.device_name.startswith("nfs-")

        call_args = mock_run.call_args[0][0]
        assert "incus" in call_args
        assert "device" in call_args
        assert "add" in call_args
        assert "waydroid" in call_args
        assert "disk" in call_args

    def test_custom_path_and_name(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch(
                "waydroid_toolkit.modules.storage.nfs._container_name",
                return_value="waydroid",
            ):
                mount = add_nfs_mount(
                    "192.168.1.10:/games",
                    container_path="/data/games",
                    device_name="my-games",
                )

        assert mount.device_name == "my-games"
        assert mount.container_path == "/data/games"

    def test_efs_type(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch(
                "waydroid_toolkit.modules.storage.nfs._container_name",
                return_value="waydroid",
            ):
                mount = add_nfs_mount(
                    "fs-0abc1234:/",
                    mount_type="efs",
                    extra_options="tls",
                )

        assert mount.mount_type == "efs"
        assert mount.options == "tls"

    def test_invalid_mount_type_raises(self):
        with pytest.raises(ValueError, match="mount_type must be one of"):
            add_nfs_mount("host:/path", mount_type="smb")

    def test_device_name_truncated_to_63_chars(self):
        long_source = "192.168.1.10:/" + "a" * 100
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch(
                "waydroid_toolkit.modules.storage.nfs._container_name",
                return_value="waydroid",
            ):
                mount = add_nfs_mount(long_source)

        assert len(mount.device_name) <= 63


# ── remove_nfs_mount ──────────────────────────────────────────────────────────

class TestRemoveNfsMount:
    def test_calls_incus_remove(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch(
                "waydroid_toolkit.modules.storage.nfs._container_name",
                return_value="waydroid",
            ):
                remove_nfs_mount("nfs-my-share")

        call_args = mock_run.call_args[0][0]
        assert "incus" in call_args
        assert "remove" in call_args
        assert "nfs-my-share" in call_args


# ── list_nfs_mounts ───────────────────────────────────────────────────────────

class TestListNfsMounts:
    def test_returns_disk_devices(self):
        import json

        devices = {
            "nfs-share": {
                "type": "disk",
                "source": "192.168.1.10:/exports",
                "path": "/data/shared",
                "raw.mount.options": "soft,async",
            },
            "eth0": {
                "type": "nic",
                "network": "incusbr0",
            },
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(devices),
            )
            with patch(
                "waydroid_toolkit.modules.storage.nfs._container_name",
                return_value="waydroid",
            ):
                mounts = list_nfs_mounts()

        assert len(mounts) == 1
        assert mounts[0].device_name == "nfs-share"
        assert mounts[0].source == "192.168.1.10:/exports"
        assert mounts[0].container_path == "/data/shared"

    def test_returns_empty_on_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            with patch(
                "waydroid_toolkit.modules.storage.nfs._container_name",
                return_value="waydroid",
            ):
                mounts = list_nfs_mounts()

        assert mounts == []

    def test_returns_empty_on_invalid_json(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not-json")
            with patch(
                "waydroid_toolkit.modules.storage.nfs._container_name",
                return_value="waydroid",
            ):
                mounts = list_nfs_mounts()

        assert mounts == []
