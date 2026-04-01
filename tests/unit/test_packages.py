"""Tests for the package manager module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from waydroid_toolkit.modules.packages.manager import (
    add_repo,
    get_installed_packages,
    install_apk_file,
    install_apk_url,
    list_repos,
    remove_package,
    remove_repo,
    search_repos,
)

# ── install_apk_file ──────────────────────────────────────────────────────────

class TestInstallApkFile:
    def test_raises_if_file_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            install_apk_file(tmp_path / "nonexistent.apk")

    def test_calls_install_apk(self, tmp_path: Path) -> None:
        apk = tmp_path / "app.apk"
        apk.write_bytes(b"PK")
        with patch("waydroid_toolkit.modules.packages.manager.install_apk") as mock_install:
            mock_install.return_value = MagicMock(returncode=0)
            install_apk_file(apk)
        mock_install.assert_called_once_with(apk)

    def test_raises_on_nonzero_returncode(self, tmp_path: Path) -> None:
        apk = tmp_path / "bad.apk"
        apk.write_bytes(b"PK")
        with patch("waydroid_toolkit.modules.packages.manager.install_apk") as mock_install:
            mock_install.return_value = MagicMock(returncode=1, stderr="INSTALL_FAILED")
            with pytest.raises(RuntimeError, match="INSTALL_FAILED"):
                install_apk_file(apk)

    def test_calls_progress(self, tmp_path: Path) -> None:
        apk = tmp_path / "app.apk"
        apk.write_bytes(b"PK")
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.packages.manager.install_apk") as mock_install:
            mock_install.return_value = MagicMock(returncode=0)
            install_apk_file(apk, progress=messages.append)
        assert any("app.apk" in m for m in messages)


# ── install_apk_url ───────────────────────────────────────────────────────────

class TestInstallApkUrl:
    def test_downloads_then_installs(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.packages.manager.download") as mock_dl:
            with patch("waydroid_toolkit.modules.packages.manager.install_apk_file") as mock_inst:
                mock_dl.side_effect = lambda url, dest: dest.write_bytes(b"PK")
                install_apk_url("https://example.com/app.apk")
        mock_dl.assert_called_once()
        mock_inst.assert_called_once()


# ── remove_package ────────────────────────────────────────────────────────────

class TestRemovePackage:
    def test_calls_uninstall(self) -> None:
        with patch("waydroid_toolkit.modules.packages.manager.uninstall_package") as mock_un:
            mock_un.return_value = MagicMock(returncode=0)
            remove_package("com.example.app")
        mock_un.assert_called_once_with("com.example.app")

    def test_raises_on_failure(self) -> None:
        with patch("waydroid_toolkit.modules.packages.manager.uninstall_package") as mock_un:
            mock_un.return_value = MagicMock(returncode=1, stderr="DELETE_FAILED")
            with pytest.raises(RuntimeError, match="DELETE_FAILED"):
                remove_package("com.example.app")


# ── get_installed_packages ────────────────────────────────────────────────────

class TestGetInstalledPackages:
    def test_delegates_to_list_packages(self) -> None:
        with patch("waydroid_toolkit.modules.packages.manager.list_packages", return_value=["com.a", "com.b"]):
            result = get_installed_packages()
        assert result == ["com.a", "com.b"]


# ── F-Droid repo management ───────────────────────────────────────────────────

class TestRepoManagement:
    def test_add_repo_creates_meta(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            with patch("waydroid_toolkit.modules.packages.manager._refresh_repo"):
                add_repo("myrepo", "https://f-droid.org/repo")
        meta = json.loads((tmp_path / "myrepo" / "meta.json").read_text())
        assert meta["name"] == "myrepo"
        assert meta["url"] == "https://f-droid.org/repo"

    def test_add_repo_calls_refresh(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            with patch("waydroid_toolkit.modules.packages.manager._refresh_repo") as mock_refresh:
                add_repo("myrepo", "https://f-droid.org/repo")
        mock_refresh.assert_called_once_with("myrepo", "https://f-droid.org/repo", None)

    def test_remove_repo_deletes_directory(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "myrepo"
        repo_dir.mkdir()
        (repo_dir / "meta.json").write_text("{}")
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            remove_repo("myrepo")
        assert not repo_dir.exists()

    def test_remove_repo_noop_if_missing(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            remove_repo("nonexistent")  # should not raise

    def test_list_repos_returns_all(self, tmp_path: Path) -> None:
        for name, url in [("fdroid", "https://f-droid.org/repo"), ("izzy", "https://apt.izzysoft.de/fdroid/repo")]:
            d = tmp_path / name
            d.mkdir()
            (d / "meta.json").write_text(json.dumps({"name": name, "url": url}))
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            repos = list_repos()
        names = [r["name"] for r in repos]
        assert "fdroid" in names
        assert "izzy" in names

    def test_list_repos_empty_when_no_dir(self, tmp_path: Path) -> None:
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path / "nonexistent"):
            assert list_repos() == []


# ── search_repos ──────────────────────────────────────────────────────────────

class TestSearchRepos:
    def _write_index(self, repo_dir: Path, apps: list[dict]) -> None:
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "meta.json").write_text(json.dumps({"name": repo_dir.name, "url": "https://example.com"}))
        (repo_dir / "index-v1.json").write_text(json.dumps({"apps": apps}))

    def test_finds_by_package_name(self, tmp_path: Path) -> None:
        self._write_index(tmp_path / "fdroid", [
            {"packageName": "org.mozilla.firefox", "name": "Firefox"},
            {"packageName": "com.example.other", "name": "Other"},
        ])
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            results = search_repos("firefox")
        assert len(results) == 1
        assert results[0]["id"] == "org.mozilla.firefox"

    def test_finds_by_display_name(self, tmp_path: Path) -> None:
        self._write_index(tmp_path / "fdroid", [
            {"packageName": "org.mozilla.firefox", "name": "Firefox"},
        ])
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            results = search_repos("Firefox")
        assert results[0]["name"] == "Firefox"

    def test_returns_empty_for_no_match(self, tmp_path: Path) -> None:
        self._write_index(tmp_path / "fdroid", [
            {"packageName": "com.example.app", "name": "Example"},
        ])
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            results = search_repos("zzznomatch")
        assert results == []

    def test_skips_missing_index(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "broken"
        repo_dir.mkdir()
        (repo_dir / "meta.json").write_text("{}")
        # No index-v1.json
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            results = search_repos("anything")
        assert results == []

    def test_skips_corrupt_index(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "corrupt"
        repo_dir.mkdir()
        (repo_dir / "meta.json").write_text("{}")
        (repo_dir / "index-v1.json").write_text("not-json{{{")
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            results = search_repos("anything")
        assert results == []

    def test_search_across_multiple_repos(self, tmp_path: Path) -> None:
        self._write_index(tmp_path / "repo1", [{"packageName": "com.app.one", "name": "AppOne"}])
        self._write_index(tmp_path / "repo2", [{"packageName": "com.app.two", "name": "AppTwo"}])
        with patch("waydroid_toolkit.modules.packages.manager._REPOS_DIR", tmp_path):
            results = search_repos("app")
        assert len(results) == 2
