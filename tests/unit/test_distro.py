"""Tests for distro detection."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from waydroid_toolkit.utils.distro import Distro, detect_distro


def _mock_os_release(content: str):
    return patch("builtins.open", mock_open(read_data=content))


@pytest.mark.parametrize("content,expected", [
    ('ID=ubuntu\nID_LIKE=debian\n', Distro.UBUNTU),
    ('ID=debian\n', Distro.DEBIAN),
    ('ID=fedora\n', Distro.FEDORA),
    ('ID=arch\n', Distro.ARCH),
    ('ID=opensuse-tumbleweed\nID_LIKE="suse opensuse"\n', Distro.OPENSUSE),
    ('ID=linuxmint\nID_LIKE=ubuntu\n', Distro.UBUNTU),
    # New distros
    ('ID=nixos\n', Distro.NIXOS),
    ('ID=void\n', Distro.VOID),
    ('ID=alpine\n', Distro.ALPINE),
    ('ID=gentoo\n', Distro.GENTOO),
    # ID_LIKE fallbacks
    ('ID=garuda\nID_LIKE=arch\n', Distro.ARCH),
    ('ID=endeavouros\nID_LIKE="arch"\n', Distro.ARCH),
    ('ID=pop\nID_LIKE="ubuntu debian"\n', Distro.UBUNTU),
    ('ID=unknown-distro\n', Distro.UNKNOWN),
])
def test_detect_distro(content: str, expected: Distro, tmp_path: Path) -> None:
    os_release = tmp_path / "os-release"
    os_release.write_text(content)
    with patch("waydroid_toolkit.utils.distro.Path") as mock_path:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = content
        # Call the real function with patched Path
        from waydroid_toolkit.utils import distro as distro_mod
        original_path = distro_mod.Path
        distro_mod.Path = lambda p: os_release if "os-release" in str(p) else original_path(p)
        result = detect_distro()
        distro_mod.Path = original_path
    assert result == expected


def test_detect_distro_missing_file(tmp_path: Path) -> None:
    from waydroid_toolkit.utils import distro as distro_mod
    original_path = distro_mod.Path
    fake = tmp_path / "nonexistent"
    distro_mod.Path = lambda p: fake if "os-release" in str(p) else original_path(p)
    result = detect_distro()
    distro_mod.Path = original_path
    assert result == Distro.UNKNOWN
