"""Tests for the OTA update checker and downloader."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.images.ota import (
    OtaEntry,
    check_updates,
    download_image,
    download_updates,
    fetch_manifest,
)
from waydroid_toolkit.utils.net import verify_sha256

# ── Helpers ───────────────────────────────────────────────────────────────────

def _manifest_response(entries: list[dict]) -> MagicMock:
    """Return a mock urllib response yielding a JSON manifest."""
    body = json.dumps({"response": entries}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.headers = {}
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _make_entry(dt: int = 1000, filename: str = "system.img.zip") -> dict:
    return {"datetime": dt, "filename": filename, "url": "https://example.com/img.zip", "id": "abc123"}


def _make_zip(tmp_path: Path, name: str, content: bytes = b"img") -> tuple[Path, str]:
    """Create a zip containing *name* with *content*. Returns (zip_path, sha256)."""
    zip_path = tmp_path / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(name, content)
    sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    return zip_path, sha


# ── fetch_manifest ────────────────────────────────────────────────────────────

class TestFetchManifest:
    def test_returns_entries_sorted_newest_first(self) -> None:
        entries = [_make_entry(dt=100), _make_entry(dt=300), _make_entry(dt=200)]
        with patch("urllib.request.urlopen", return_value=_manifest_response(entries)):
            result = fetch_manifest("https://example.com/ota")
        assert [e.datetime for e in result] == [300, 200, 100]

    def test_returns_empty_list_on_empty_response(self) -> None:
        with patch("urllib.request.urlopen",
                   return_value=_manifest_response([])):
            result = fetch_manifest("https://example.com/ota")
        assert result == []

    def test_maps_id_field_to_sha256(self) -> None:
        with patch("urllib.request.urlopen",
                   return_value=_manifest_response([_make_entry()])):
            result = fetch_manifest("https://example.com/ota")
        assert result[0].sha256 == "abc123"

    def test_maps_all_fields(self) -> None:
        entry = {"datetime": 9999, "filename": "vendor.img.zip",
                 "url": "https://x.com/v.zip", "id": "deadbeef"}
        with patch("urllib.request.urlopen",
                   return_value=_manifest_response([entry])):
            result = fetch_manifest("https://example.com/ota")
        e = result[0]
        assert e.datetime == 9999
        assert e.filename == "vendor.img.zip"
        assert e.url == "https://x.com/v.zip"
        assert e.sha256 == "deadbeef"


# ── check_updates ─────────────────────────────────────────────────────────────

class TestCheckUpdates:
    def _cfg(self, system_dt: int = 0, vendor_dt: int = 0) -> MagicMock:
        cfg = MagicMock()
        cfg.system_ota = "https://ota.waydro.id/system"
        cfg.vendor_ota = "https://ota.waydro.id/vendor"
        cfg.system_datetime = system_dt
        cfg.vendor_datetime = vendor_dt
        return cfg

    def test_update_available_when_server_newer(self) -> None:
        cfg = self._cfg(system_dt=100, vendor_dt=100)
        with patch("waydroid_toolkit.modules.images.ota.fetch_manifest") as mock_fetch:
            mock_fetch.return_value = [OtaEntry(datetime=200, filename="s.zip",
                                                url="u", sha256="h")]
            sys_info, _ = check_updates(cfg)
        assert sys_info.update_available is True

    def test_no_update_when_server_same_datetime(self) -> None:
        cfg = self._cfg(system_dt=200, vendor_dt=200)
        with patch("waydroid_toolkit.modules.images.ota.fetch_manifest") as mock_fetch:
            mock_fetch.return_value = [OtaEntry(datetime=200, filename="s.zip",
                                                url="u", sha256="h")]
            sys_info, _ = check_updates(cfg)
        assert sys_info.update_available is False

    def test_no_update_when_channel_empty(self) -> None:
        cfg = self._cfg()
        with patch("waydroid_toolkit.modules.images.ota.fetch_manifest",
                   return_value=[]):
            sys_info, vendor_info = check_updates(cfg)
        assert sys_info.update_available is False
        assert sys_info.latest is None

    def test_returns_both_channels(self) -> None:
        cfg = self._cfg()
        with patch("waydroid_toolkit.modules.images.ota.fetch_manifest") as mock_fetch:
            mock_fetch.return_value = [OtaEntry(datetime=500, filename="x.zip",
                                                url="u", sha256="h")]
            sys_info, vendor_info = check_updates(cfg)
        assert sys_info.channel == "system"
        assert vendor_info.channel == "vendor"


# ── verify_sha256 (via net.py) ────────────────────────────────────────────────

class TestVerifySha256:
    def test_matches_known_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "data.bin"
        f.write_bytes(b"hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert verify_sha256(f, expected) is True

    def test_returns_false_on_mismatch(self, tmp_path: Path) -> None:
        f = tmp_path / "data.bin"
        f.write_bytes(b"hello")
        assert verify_sha256(f, "wronghash") is False


# ── download_image ────────────────────────────────────────────────────────────

class TestDownloadImage:
    def test_extracts_img_and_returns_path(self, tmp_path: Path) -> None:
        zip_path, sha = _make_zip(tmp_path, "system.img", b"fake-system")
        entry = OtaEntry(datetime=1, filename="system.img.zip",
                         url="https://x.com/s.zip", sha256=sha)

        dest = tmp_path / "dest"

        def _fake_download(url, dest_file, progress):
            import shutil
            shutil.copy(zip_path, dest_file)

        with patch("waydroid_toolkit.modules.images.ota._download_with_progress",
                   side_effect=_fake_download):
            result = download_image(entry, dest)

        assert result == dest / "system.img"

    def test_raises_on_sha256_mismatch(self, tmp_path: Path) -> None:
        zip_path, _ = _make_zip(tmp_path, "system.img")
        entry = OtaEntry(datetime=1, filename="system.img.zip",
                         url="https://x.com/s.zip", sha256="wronghash")

        dest = tmp_path / "dest"

        def _fake_download(url, dest_file, progress):
            import shutil
            shutil.copy(zip_path, dest_file)

        with patch("waydroid_toolkit.modules.images.ota._download_with_progress",
                   side_effect=_fake_download):
            with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
                download_image(entry, dest)

    def test_calls_progress(self, tmp_path: Path) -> None:
        zip_path, sha = _make_zip(tmp_path, "vendor.img")
        entry = OtaEntry(datetime=1, filename="vendor.img.zip",
                         url="https://x.com/v.zip", sha256=sha)
        dest = tmp_path / "dest"
        messages: list[str] = []

        def _fake_download(url, dest_file, progress):
            import shutil
            shutil.copy(zip_path, dest_file)

        with patch("waydroid_toolkit.modules.images.ota._download_with_progress",
                   side_effect=_fake_download):
            download_image(entry, dest, progress=messages.append)

        assert any("vendor.img.zip" in m for m in messages)


# ── download_updates ──────────────────────────────────────────────────────────

class TestDownloadUpdates:
    def _cfg(self, system_dt: int = 0, vendor_dt: int = 0) -> MagicMock:
        cfg = MagicMock()
        cfg.system_ota = "https://ota.waydro.id/system"
        cfg.vendor_ota = "https://ota.waydro.id/vendor"
        cfg.system_datetime = system_dt
        cfg.vendor_datetime = vendor_dt
        return cfg

    def test_returns_none_when_up_to_date(self, tmp_path: Path) -> None:
        cfg = self._cfg(system_dt=999, vendor_dt=999)
        with patch("waydroid_toolkit.modules.images.ota.fetch_manifest") as mock_fetch:
            mock_fetch.return_value = [OtaEntry(datetime=999, filename="x.zip",
                                                url="u", sha256="h")]
            sys_path, vendor_path = download_updates(tmp_path, cfg=cfg, update_cfg=False)
        assert sys_path is None
        assert vendor_path is None

    def test_downloads_when_update_available(self, tmp_path: Path) -> None:
        cfg = self._cfg(system_dt=0, vendor_dt=0)
        zip_path, sha = _make_zip(tmp_path, "system.img")
        entry = OtaEntry(datetime=500, filename="system.img.zip", url="u", sha256=sha)

        def _fake_download(url, dest_file, progress):
            import shutil
            shutil.copy(zip_path, dest_file)

        with patch("waydroid_toolkit.modules.images.ota.fetch_manifest",
                   return_value=[entry]), \
             patch("waydroid_toolkit.modules.images.ota._download_with_progress",
                   side_effect=_fake_download), \
             patch("waydroid_toolkit.modules.images.ota._save_datetime"):
            sys_path, vendor_path = download_updates(
                tmp_path / "dest", cfg=cfg, update_cfg=True
            )

        assert sys_path is not None
        assert sys_path.name == "system.img"

    def test_saves_datetime_after_download(self, tmp_path: Path) -> None:
        cfg = self._cfg(system_dt=0, vendor_dt=999)
        zip_path, sha = _make_zip(tmp_path, "system.img")
        entry = OtaEntry(datetime=500, filename="system.img.zip", url="u", sha256=sha)

        def _fake_download(url, dest_file, progress):
            import shutil
            shutil.copy(zip_path, dest_file)

        with patch("waydroid_toolkit.modules.images.ota.fetch_manifest") as mock_fetch, \
             patch("waydroid_toolkit.modules.images.ota._download_with_progress",
                   side_effect=_fake_download), \
             patch("waydroid_toolkit.modules.images.ota._save_datetime") as mock_save:
            # system has update (dt=0 < 500), vendor is up to date (dt=999 >= 999)
            mock_fetch.side_effect = [
                [entry],                                                    # system
                [OtaEntry(datetime=999, filename="v.zip", url="u", sha256="h")],  # vendor
            ]
            download_updates(tmp_path / "dest", cfg=cfg, update_cfg=True)

        mock_save.assert_called_once_with("system", 500)
