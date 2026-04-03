"""Tests for wdt assemble."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from waydroid_toolkit.cli.commands.assemble import _parse_minimal_yaml, cmd as assemble_cmd


# ── YAML parser ───────────────────────────────────────────────────────────────

class TestParseMinimalYaml:
    def test_parses_backend(self) -> None:
        text = dedent("""\
            waydroid:
              backend: incus
        """)
        result = _parse_minimal_yaml(text)
        assert result["waydroid"]["backend"] == "incus"

    def test_parses_image_type(self) -> None:
        text = dedent("""\
            waydroid:
              image_type: GAPPS
        """)
        result = _parse_minimal_yaml(text)
        assert result["waydroid"]["image_type"] == "GAPPS"

    def test_parses_extensions_list(self) -> None:
        text = dedent("""\
            waydroid:
              extensions:
                - gapps
                - widevine
        """)
        result = _parse_minimal_yaml(text)
        assert result["waydroid"]["extensions"] == ["gapps", "widevine"]

    def test_parses_integer_values(self) -> None:
        text = dedent("""\
            waydroid:
              performance:
                zram_size: 4096
        """)
        result = _parse_minimal_yaml(text)
        assert result["waydroid"]["performance"]["zram_size"] == 4096

    def test_ignores_comments(self) -> None:
        text = dedent("""\
            # top comment
            waydroid:
              # inline comment
              backend: lxc
        """)
        result = _parse_minimal_yaml(text)
        assert result["waydroid"]["backend"] == "lxc"

    def test_empty_file_returns_empty_dict(self) -> None:
        assert _parse_minimal_yaml("") == {}

    def test_no_waydroid_section(self) -> None:
        result = _parse_minimal_yaml("other:\n  key: val\n")
        assert "waydroid" not in result


# ── CLI ───────────────────────────────────────────────────────────────────────

class TestAssembleCmd:
    def _write_config(self, tmp_path: Path, content: str) -> Path:
        f = tmp_path / "waydroid.yaml"
        f.write_text(content)
        return f

    def test_dry_run_prints_summary_no_changes(self, tmp_path: Path) -> None:
        cfg = self._write_config(tmp_path, dedent("""\
            waydroid:
              backend: incus
              image_type: VANILLA
        """))
        runner = CliRunner()
        result = runner.invoke(assemble_cmd, ["--file", str(cfg), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "incus" in result.output

    def test_unknown_backend_exits_nonzero(self, tmp_path: Path) -> None:
        cfg = self._write_config(tmp_path, "waydroid:\n  backend: docker\n")
        runner = CliRunner()
        result = runner.invoke(assemble_cmd, ["--file", str(cfg), "--dry-run"])
        assert result.exit_code != 0
        assert "backend" in result.output.lower()

    def test_unknown_image_type_exits_nonzero(self, tmp_path: Path) -> None:
        cfg = self._write_config(tmp_path, "waydroid:\n  image_type: CUSTOM\n")
        runner = CliRunner()
        result = runner.invoke(assemble_cmd, ["--file", str(cfg), "--dry-run"])
        assert result.exit_code != 0

    def test_no_waydroid_section_is_noop(self, tmp_path: Path) -> None:
        cfg = self._write_config(tmp_path, "other:\n  key: val\n")
        runner = CliRunner()
        result = runner.invoke(assemble_cmd, ["--file", str(cfg), "--dry-run"])
        assert result.exit_code == 0
        assert "nothing to do" in result.output.lower()

    def test_apply_sets_backend(self, tmp_path: Path) -> None:
        cfg = self._write_config(tmp_path, "waydroid:\n  backend: incus\n")
        runner = CliRunner()
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True

        with patch("waydroid_toolkit.cli.commands.assemble.IncusBackend", return_value=mock_backend):
            with patch("waydroid_toolkit.cli.commands.assemble.set_active_backend") as mock_set:
                result = runner.invoke(assemble_cmd, ["--file", str(cfg), "--yes"])

        assert result.exit_code == 0
        mock_set.assert_called_once()

    def test_apply_skips_unavailable_backend(self, tmp_path: Path) -> None:
        cfg = self._write_config(tmp_path, "waydroid:\n  backend: incus\n")
        runner = CliRunner()
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = False

        with patch("waydroid_toolkit.cli.commands.assemble.IncusBackend", return_value=mock_backend):
            with patch("waydroid_toolkit.cli.commands.assemble.set_active_backend") as mock_set:
                result = runner.invoke(assemble_cmd, ["--file", str(cfg), "--yes"])

        assert result.exit_code == 0
        mock_set.assert_not_called()
        assert "not available" in result.output.lower()

    def test_example_file_parses_cleanly(self) -> None:
        """The committed example file must parse without errors."""
        example = Path(__file__).parent.parent.parent / "data" / "example-assemble.yaml"
        if not example.exists():
            pytest.skip("example-assemble.yaml not found")
        runner = CliRunner()
        result = runner.invoke(assemble_cmd, ["--file", str(example), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
