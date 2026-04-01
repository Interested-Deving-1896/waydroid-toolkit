"""Tests for network download helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from waydroid_toolkit.utils.net import download, verify_sha256


def test_download_writes_file(tmp_path: Path) -> None:
    content = b"fake binary content"
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {"Content-Length": str(len(content))}
    mock_resp.read.side_effect = [content, b""]

    dest = tmp_path / "file.bin"
    with patch("waydroid_toolkit.utils.net.urlopen", return_value=mock_resp):
        result = download("https://example.com/file.bin", dest)

    assert result == dest
    assert dest.read_bytes() == content


def test_download_calls_progress(tmp_path: Path) -> None:
    content = b"data"
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {"Content-Length": "4"}
    mock_resp.read.side_effect = [content, b""]

    calls: list[tuple[int, int]] = []
    dest = tmp_path / "out.bin"
    with patch("waydroid_toolkit.utils.net.urlopen", return_value=mock_resp):
        download("https://example.com/out.bin", dest, progress=lambda d, t: calls.append((d, t)))

    assert len(calls) == 1
    assert calls[0] == (4, 4)


def test_verify_sha256_correct(tmp_path: Path) -> None:
    import hashlib
    data = b"hello world"
    expected = hashlib.sha256(data).hexdigest()
    f = tmp_path / "file.txt"
    f.write_bytes(data)
    assert verify_sha256(f, expected) is True


def test_verify_sha256_wrong(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_bytes(b"hello world")
    assert verify_sha256(f, "0" * 64) is False


def _mock_response(content: bytes, content_length: int | None = None) -> MagicMock:
    """Build a context-manager mock for urlopen."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {"Content-Length": str(content_length if content_length is not None else len(content))}
    mock_resp.read.side_effect = [content, b""]
    return mock_resp


# ── download — additional cases ───────────────────────────────────────────────

def test_download_raises_connection_error_on_url_error(tmp_path: Path) -> None:
    with patch("waydroid_toolkit.utils.net.urlopen", side_effect=URLError("timeout")):
        with pytest.raises(ConnectionError, match="Failed to download"):
            download("https://example.com/file.bin", tmp_path / "out.bin")


def test_download_creates_parent_directories(tmp_path: Path) -> None:
    dest = tmp_path / "a" / "b" / "c" / "file.bin"
    with patch("waydroid_toolkit.utils.net.urlopen", return_value=_mock_response(b"data")):
        download("https://example.com/file.bin", dest)
    assert dest.exists()


def test_download_handles_missing_content_length(tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {}  # no Content-Length
    mock_resp.read.side_effect = [b"data", b""]
    dest = tmp_path / "out.bin"
    with patch("waydroid_toolkit.utils.net.urlopen", return_value=mock_resp):
        result = download("https://example.com/file.bin", dest)
    assert result == dest
    assert dest.read_bytes() == b"data"


def test_download_progress_receives_total_zero_when_no_content_length(tmp_path: Path) -> None:
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {}
    mock_resp.read.side_effect = [b"data", b""]
    calls: list[tuple[int, int]] = []
    dest = tmp_path / "out.bin"
    with patch("waydroid_toolkit.utils.net.urlopen", return_value=mock_resp):
        download("https://example.com/file.bin", dest, progress=lambda d, t: calls.append((d, t)))
    assert calls[0][1] == 0  # total is 0 when Content-Length absent


def test_download_sends_user_agent_header(tmp_path: Path) -> None:
    dest = tmp_path / "file.bin"
    with patch("waydroid_toolkit.utils.net.urlopen", return_value=_mock_response(b"x")):
        with patch("waydroid_toolkit.utils.net.Request") as mock_req:
            mock_req.return_value = MagicMock()
            download("https://example.com/file.bin", dest)
    _, kwargs = mock_req.call_args
    headers = kwargs.get("headers", {})
    assert "User-Agent" in headers
    assert "waydroid-toolkit" in headers["User-Agent"]


def test_download_multiple_chunks_progress(tmp_path: Path) -> None:
    chunk1, chunk2 = b"a" * 64, b"b" * 64
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.headers = {"Content-Length": "128"}
    mock_resp.read.side_effect = [chunk1, chunk2, b""]
    calls: list[tuple[int, int]] = []
    dest = tmp_path / "out.bin"
    with patch("waydroid_toolkit.utils.net.urlopen", return_value=mock_resp):
        download("https://example.com/file.bin", dest,
                 progress=lambda d, t: calls.append((d, t)), chunk_size=64)
    assert len(calls) == 2
    assert calls[-1][0] == 128


# ── verify_sha256 — additional cases ─────────────────────────────────────────

def test_verify_sha256_case_insensitive(tmp_path: Path) -> None:
    data = b"hello"
    expected = hashlib.sha256(data).hexdigest().upper()
    f = tmp_path / "f.bin"
    f.write_bytes(data)
    assert verify_sha256(f, expected) is True


def test_verify_sha256_large_file(tmp_path: Path) -> None:
    data = b"x" * 200_000
    expected = hashlib.sha256(data).hexdigest()
    f = tmp_path / "large.bin"
    f.write_bytes(data)
    assert verify_sha256(f, expected) is True
