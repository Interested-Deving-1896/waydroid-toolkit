"""Tests for wdt template."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from waydroid_toolkit.cli.commands.template import _parse_template, cmd as template_cmd


# ── parser unit tests ─────────────────────────────────────────────────────────

class TestParseTemplate:
    def test_parses_description(self, tmp_path: Path) -> None:
        f = tmp_path / "t.yaml"
        f.write_text('description: "A test template"\n')
        d = _parse_template(f)
        assert d["description"] == "A test template"

    def test_parses_nested_resources(self, tmp_path: Path) -> None:
        f = tmp_path / "t.yaml"
        f.write_text("resources:\n  cpu: 4\n  memory: 8GiB\n")
        d = _parse_template(f)
        assert isinstance(d["resources"], dict)
        assert d["resources"]["cpu"] == "4"  # type: ignore[index]
        assert d["resources"]["memory"] == "8GiB"  # type: ignore[index]

    def test_ignores_comments(self, tmp_path: Path) -> None:
        f = tmp_path / "t.yaml"
        f.write_text("# comment\ndescription: hello\n")
        d = _parse_template(f)
        assert d["description"] == "hello"


# ── CLI tests ─────────────────────────────────────────────────────────────────

def _make_template_dir(tmp_path: Path) -> Path:
    tdir = tmp_path / "templates"
    tdir.mkdir()
    (tdir / "dev.yaml").write_text(
        'description: "Dev template"\nresources:\n  cpu: 4\n  memory: 4GiB\n'
    )
    (tdir / "minimal.yaml").write_text(
        'description: "Minimal template"\nresources:\n  cpu: 2\n  memory: 2GiB\n'
    )
    return tdir


class TestTemplateList:
    def test_lists_templates(self, tmp_path: Path) -> None:
        tdir = _make_template_dir(tmp_path)
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.template._templates_dir", return_value=tdir):
            result = runner.invoke(template_cmd, ["list"])
        assert result.exit_code == 0
        assert "dev" in result.output
        assert "minimal" in result.output

    def test_empty_dir_shows_message(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.template._templates_dir", return_value=empty):
            result = runner.invoke(template_cmd, ["list"])
        assert result.exit_code == 0
        assert "No templates" in result.output


class TestTemplateShow:
    def test_shows_template_details(self, tmp_path: Path) -> None:
        tdir = _make_template_dir(tmp_path)
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.template._templates_dir", return_value=tdir):
            result = runner.invoke(template_cmd, ["show", "dev"])
        assert result.exit_code == 0
        assert "Dev template" in result.output
        assert "4GiB" in result.output

    def test_missing_template_exits_nonzero(self, tmp_path: Path) -> None:
        tdir = _make_template_dir(tmp_path)
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.template._templates_dir", return_value=tdir):
            result = runner.invoke(template_cmd, ["show", "nonexistent"])
        assert result.exit_code != 0


class TestTemplateApply:
    def test_dry_run_makes_no_subprocess_calls(self, tmp_path: Path) -> None:
        tdir = _make_template_dir(tmp_path)
        mock_b = MagicMock()
        mock_b.get_info.return_value = MagicMock(container_name="waydroid")
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.template._templates_dir", return_value=tdir):
            with patch("waydroid_toolkit.cli.commands.template.get_backend", return_value=mock_b):
                with patch("waydroid_toolkit.cli.commands.template.subprocess.run") as mock_run:
                    result = runner.invoke(template_cmd, ["apply", "dev", "--dry-run"])
        assert result.exit_code == 0
        mock_run.assert_not_called()
        assert "dry-run" in result.output

    def test_apply_calls_incus_config_set(self, tmp_path: Path) -> None:
        tdir = _make_template_dir(tmp_path)
        mock_b = MagicMock()
        mock_b.get_info.return_value = MagicMock(container_name="waydroid")
        runner = CliRunner()
        with patch("waydroid_toolkit.cli.commands.template._templates_dir", return_value=tdir):
            with patch("waydroid_toolkit.cli.commands.template.get_backend", return_value=mock_b):
                with patch("waydroid_toolkit.cli.commands.template.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    result = runner.invoke(template_cmd, ["apply", "dev"])
        assert result.exit_code == 0
        calls = [c[0][0] for c in mock_run.call_args_list]
        assert any("limits.cpu" in c for c in calls)
        assert any("limits.memory" in c for c in calls)
