"""Tests for the performance tuner module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from waydroid_toolkit.modules.performance.tuner import (
    PerformanceProfile,
    apply_profile,
    install_systemd_service,
    restore_defaults,
)

# ── PerformanceProfile defaults ───────────────────────────────────────────────

class TestPerformanceProfile:
    def test_default_governor_is_performance(self) -> None:
        assert PerformanceProfile().cpu_governor == "performance"

    def test_default_zram_size(self) -> None:
        assert PerformanceProfile().zram_size_mb == 4096

    def test_default_algorithm_is_lz4(self) -> None:
        assert PerformanceProfile().zram_algorithm == "lz4"

    def test_turbo_enabled_by_default(self) -> None:
        assert PerformanceProfile().enable_turbo is True

    def test_gamemode_enabled_by_default(self) -> None:
        assert PerformanceProfile().use_gamemode is True


# ── apply_profile ─────────────────────────────────────────────────────────────

class TestApplyProfile:
    def _mock_run(self, returncode: int = 0, stdout: str = "/dev/zram0") -> MagicMock:
        return MagicMock(returncode=returncode, stdout=stdout)

    def test_calls_zramctl(self) -> None:
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner.subprocess.run") as mock_run:
                mock_run.return_value = self._mock_run()
                apply_profile(PerformanceProfile(use_gamemode=False))
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("zramctl" in c for c in cmds)

    def test_calls_cpu_governor(self, tmp_path: Path) -> None:
        policy = tmp_path / "policy0"
        policy.mkdir()
        (policy / "scaling_governor").write_text("schedutil")
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner.subprocess.run") as mock_run:
                mock_run.return_value = self._mock_run()
                with patch(
                    "waydroid_toolkit.modules.performance.tuner.Path",
                    side_effect=lambda p: Path(str(p).replace(
                        "/sys/devices/system/cpu/cpufreq", str(tmp_path)
                    )),
                ):
                    apply_profile(PerformanceProfile(use_gamemode=False))
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("tee" in c for c in cmds)

    def test_gamemode_started_when_available(self) -> None:
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner.subprocess.run") as mock_run:
                mock_run.return_value = self._mock_run()
                with patch("waydroid_toolkit.modules.performance.tuner.shutil.which", return_value="/usr/bin/gamemoded"):
                    apply_profile(PerformanceProfile(use_gamemode=True))
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("gamemoded" in c for c in cmds)

    def test_gamemode_skipped_when_not_installed(self) -> None:
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner.subprocess.run") as mock_run:
                mock_run.return_value = self._mock_run()
                with patch("waydroid_toolkit.modules.performance.tuner.shutil.which", return_value=None):
                    apply_profile(PerformanceProfile(use_gamemode=True))
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert not any("gamemoded" in c for c in cmds)

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner.subprocess.run") as mock_run:
                mock_run.return_value = self._mock_run()
                with patch("waydroid_toolkit.modules.performance.tuner.shutil.which", return_value=None):
                    apply_profile(PerformanceProfile(use_gamemode=False), progress=messages.append)
        assert len(messages) >= 2


# ── restore_defaults ──────────────────────────────────────────────────────────

class TestRestoreDefaults:
    def test_sets_schedutil_governor(self) -> None:
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner._set_cpu_governor") as mock_gov:
                restore_defaults()
        mock_gov.assert_called_once_with("schedutil")

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                restore_defaults(progress=messages.append)
        assert len(messages) >= 1


# ── install_systemd_service ───────────────────────────────────────────────────

class TestInstallSystemdService:
    def test_writes_service_file_and_enables(self) -> None:
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                install_systemd_service()
        cmds = [" ".join(c[0][0]) for c in mock_run.call_args_list]
        assert any("daemon-reload" in c for c in cmds)
        assert any("enable" in c for c in cmds)

    def test_progress_called(self) -> None:
        messages: list[str] = []
        with patch("waydroid_toolkit.modules.performance.tuner.require_root"):
            with patch("waydroid_toolkit.modules.performance.tuner.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                install_systemd_service(progress=messages.append)
        assert len(messages) >= 1
