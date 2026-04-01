"""Tests for network download helpers."""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

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
