"""Tests for the backup module."""

from pathlib import Path

from waydroid_toolkit.modules.backup.backup import list_backups


def test_list_backups_empty(tmp_path: Path) -> None:
    assert list_backups(tmp_path) == []


def test_list_backups_sorted_newest_first(tmp_path: Path) -> None:
    names = [
        "waydroid_backup_20240101_120000.tar.gz",
        "waydroid_backup_20240301_090000.tar.gz",
        "waydroid_backup_20240201_150000.tar.gz",
    ]
    for name in names:
        (tmp_path / name).touch()

    result = list_backups(tmp_path)
    assert [p.name for p in result] == sorted(names, reverse=True)


def test_list_backups_ignores_non_matching(tmp_path: Path) -> None:
    (tmp_path / "waydroid_backup_20240101_120000.tar.gz").touch()
    (tmp_path / "other_file.tar.gz").touch()
    (tmp_path / "notes.txt").touch()

    result = list_backups(tmp_path)
    assert len(result) == 1
    assert result[0].name == "waydroid_backup_20240101_120000.tar.gz"


def test_list_backups_missing_dir(tmp_path: Path) -> None:
    assert list_backups(tmp_path / "nonexistent") == []
