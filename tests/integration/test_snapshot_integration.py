"""Integration tests for snapshot support.

These tests require either ZFS or btrfs to be available on the host.
They are skipped automatically when neither backend is present.

WARNING: ``test_create_and_delete`` creates and immediately deletes a real
snapshot. It does NOT test restore (which would overwrite live data).
"""

from __future__ import annotations

import pytest

from waydroid_toolkit.modules.snapshot import detect_backend, get_backend
from waydroid_toolkit.modules.snapshot.backends import SnapshotInfo

# Skip the entire module if no snapshot backend is available.
# The autouse _require_live_waydroid fixture already handles the Waydroid
# prerequisite; this adds the backend check on top.
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def _require_snapshot_backend():
    backend = detect_backend()
    if backend is None:
        pytest.skip("No ZFS or btrfs snapshot backend available")


class TestSnapshotBackendIntegration:
    def test_detect_backend_returns_backend(self) -> None:
        backend = detect_backend()
        assert backend is not None

    def test_get_backend_does_not_raise(self) -> None:
        backend = get_backend()
        assert backend is not None

    def test_backend_name_is_known(self) -> None:
        backend = get_backend()
        assert backend.NAME in ("zfs", "btrfs")

    def test_list_returns_list(self) -> None:
        backend = get_backend()
        snaps = backend.list()
        assert isinstance(snaps, list)

    def test_list_items_are_snapshot_info(self) -> None:
        backend = get_backend()
        for snap in backend.list():
            assert isinstance(snap, SnapshotInfo)
            assert snap.name.startswith("waydroid-")
            assert snap.backend == backend.NAME

    def test_create_and_delete(self) -> None:
        """Create a snapshot with a test label and immediately delete it."""
        backend = get_backend()
        info = backend.create("integration-test")
        assert isinstance(info, SnapshotInfo)
        assert "integration-test" in info.name

        # Verify it appears in the list
        names = [s.name for s in backend.list()]
        assert info.name in names

        # Clean up
        backend.delete(info.name)
        names_after = [s.name for s in backend.list()]
        assert info.name not in names_after

    def test_delete_nonexistent_raises(self) -> None:
        backend = get_backend()
        with pytest.raises((RuntimeError, FileNotFoundError)):
            backend.delete("waydroid-nonexistent-snap-99999999_999999")
