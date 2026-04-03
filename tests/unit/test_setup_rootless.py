"""Tests for wdt setup-rootless."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from waydroid_toolkit.cli.commands.setup_rootless import cmd


def _make_run(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _base_patches(
    *,
    uid: int = 1000,
    user: str = "alice",
    socket_exists: bool = True,
    incus_ok: bool = True,
    incus_user_svc: bool = True,
    incus_user_active: bool = True,
    binder_loaded: bool = True,
    subuid_content: str = "alice:100000:65536",
    subgid_content: str = "alice:100000:65536",
    profile_ok: bool = True,
    waydroid_svc_enabled: bool = True,
) -> list:
    def _run_side_effect(args, **_kwargs):
        cmd_str = " ".join(str(a) for a in args)
        if "incus" in cmd_str and "--version" in cmd_str:
            return _make_run(0 if incus_ok else 1, "6.0.0")
        if "list-unit-files" in cmd_str and "incus-user" in cmd_str:
            return _make_run(0 if incus_user_svc else 1,
                             "incus-user.service enabled" if incus_user_svc else "")
        if "is-active" in cmd_str and "incus-user" in cmd_str:
            return _make_run(0 if incus_user_active else 1)
        if "lsmod" in cmd_str:
            return _make_run(0, "binder_linux 12345 0" if binder_loaded else "")
        if "grep" in cmd_str and "binder" in cmd_str:
            # Simulate binder not built-in when binder_loaded is False
            return _make_run(1 if not binder_loaded else 0)
        if "profile" in cmd_str and "show" in cmd_str:
            return _make_run(0 if profile_ok else 1)
        if "is-enabled" in cmd_str and "waydroid-container" in cmd_str:
            return _make_run(0 if waydroid_svc_enabled else 1)
        if "list-unit-files" in cmd_str and "waydroid-container" in cmd_str:
            return _make_run(0, "waydroid-container.service enabled")
        return _make_run(0)

    def _read_text_side_effect(self):
        if "subuid" in str(self):
            return subuid_content
        if "subgid" in str(self):
            return subgid_content
        return ""

    return [
        patch("os.getuid", return_value=uid),
        patch.dict("os.environ", {"USER": user, "XDG_RUNTIME_DIR": f"/run/user/{uid}"}),
        patch("waydroid_toolkit.cli.commands.setup_rootless._run", side_effect=_run_side_effect),
        patch("subprocess.run", side_effect=_run_side_effect),
        patch("pathlib.Path.exists", return_value=socket_exists),
        patch("pathlib.Path.read_text", _read_text_side_effect),
    ]


class TestSetupRootless:
    def _invoke(self, args: list[str] | None = None, **kwargs) -> object:
        runner = CliRunner()
        patches = _base_patches(**kwargs)
        for p in patches:
            p.start()
        try:
            result = runner.invoke(cmd, args or [])
        finally:
            for p in patches:
                p.stop()
        return result

    def test_all_ok_exits_zero(self) -> None:
        result = self._invoke()
        assert result.exit_code == 0
        assert "All checks passed" in result.output

    def test_root_user_exits_nonzero(self) -> None:
        result = self._invoke(uid=0)
        assert result.exit_code != 0

    def test_missing_incus_reports_issue(self) -> None:
        result = self._invoke(incus_ok=False)
        assert result.exit_code != 0

    def test_missing_binder_reports_issue(self) -> None:
        result = self._invoke(binder_loaded=False)
        assert result.exit_code != 0

    def test_missing_subuid_entry_reports_issue(self) -> None:
        result = self._invoke(subuid_content="otheruser:100000:65536")
        assert result.exit_code != 0

    def test_missing_profile_reports_issue(self) -> None:
        result = self._invoke(profile_ok=False)
        assert result.exit_code != 0

    def test_fix_flag_accepted(self) -> None:
        result = self._invoke(args=["--fix"])
        assert result.exit_code == 0

    def test_yes_flag_implies_fix(self) -> None:
        result = self._invoke(args=["--yes"])
        assert result.exit_code == 0

    def test_issues_count_shown_on_failure(self) -> None:
        result = self._invoke(incus_ok=False)
        assert "issue" in result.output.lower()

    def test_rerun_hint_shown_without_fix(self) -> None:
        result = self._invoke(profile_ok=False)
        assert "--fix" in result.output
