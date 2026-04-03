"""Tests for wdt gpu (GPU passthrough)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.gpu import cmd as gpu_cmd

_CT = "waydroid"
_PATCH = "waydroid_toolkit.cli.commands.gpu"


def _patch_container():
    return patch(f"{_PATCH}._container_name", return_value=_CT)


class TestGpuAttach:
    def test_attach_physical_default(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(gpu_cmd, ["attach"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "gpu" in args
        assert "gputype=physical" in args

    def test_attach_with_pci_address(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(gpu_cmd, ["attach", "--pci", "0000:01:00.0"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "pci=0000:01:00.0" in args

    def test_attach_mdev_type(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(gpu_cmd, ["attach", "--type", "mdev"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "gputype=mdev" in args

    def test_attach_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                result = runner.invoke(gpu_cmd, ["attach"])
        assert result.exit_code != 0

    def test_attach_custom_dev_name(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                runner.invoke(gpu_cmd, ["attach", "--dev-name", "mygpu"])
        args = mock_run.call_args[0][0]
        assert "mygpu" in args


class TestGpuDetach:
    def test_detach_removes_device(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(gpu_cmd, ["detach", "gpu0"])
        assert result.exit_code == 0
        args = mock_run.call_args[0][0]
        assert "remove" in args
        assert "gpu0" in args

    def test_detach_failure_exits_nonzero(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                result = runner.invoke(gpu_cmd, ["detach", "gpu0"])
        assert result.exit_code != 0


class TestGpuList:
    def test_list_shows_gpu_devices(self) -> None:
        runner = CliRunner()

        def fake_run(cmd, **kw):
            m = MagicMock(returncode=0)
            if "list" in cmd:
                m.stdout = "gpu0  gpu\n"
            elif "gputype" in cmd:
                m.stdout = "physical\n"
            else:
                m.stdout = "0000:01:00.0\n"
            return m

        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run", side_effect=fake_run):
                result = runner.invoke(gpu_cmd, ["list"])
        assert result.exit_code == 0
        assert "gpu0" in result.output

    def test_list_no_devices_shows_message(self) -> None:
        runner = CliRunner()
        with _patch_container():
            with patch(f"{_PATCH}.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="eth0  nic\n")
                result = runner.invoke(gpu_cmd, ["list"])
        assert result.exit_code == 0
        assert "No GPU" in result.output


class TestGpuListHost:
    def test_list_host_shows_incus_resources(self) -> None:
        runner = CliRunner()
        resources_out = "  GPUs:\n    GPU 0:\n      Vendor: NVIDIA\n  Storage:\n"

        def fake_run(cmd, **kw):
            m = MagicMock(returncode=0)
            if "--resources" in cmd:
                m.stdout = resources_out
            else:
                m.stdout = ""
                m.returncode = 1
            return m

        with patch(f"{_PATCH}.subprocess.run", side_effect=fake_run):
            result = runner.invoke(gpu_cmd, ["list-host"])
        assert result.exit_code == 0
        assert "NVIDIA" in result.output
