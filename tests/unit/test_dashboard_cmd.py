"""Tests for wdt dashboard."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from waydroid_toolkit.cli.commands.dashboard import (
    _containers_json,
    _host_disk,
    _host_memory,
    _wdt_version,
    _Handler,
)


def _make_run(returncode: int = 0, stdout: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


class TestContainersJson:
    def test_empty_when_incus_fails(self) -> None:
        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   return_value=_make_run(1)):
            data = _containers_json()
        assert data["containers"] == []
        assert data["system"]["total"] == 0
        assert data["system"]["running"] == 0

    def test_empty_when_invalid_json(self) -> None:
        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   return_value=_make_run(0, "not-json")):
            data = _containers_json()
        assert data["containers"] == []

    def test_filters_non_containers(self) -> None:
        instances = json.dumps([
            {"name": "vm1", "type": "virtual-machine", "status": "Running"},
            {"name": "ct1", "type": "container", "status": "Running",
             "state": {"network": {}}},
        ])
        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   return_value=_make_run(0, instances)) as mock_run:
            # stub config/device calls
            mock_run.side_effect = None
            mock_run.return_value = _make_run(0, instances)

            def _run_side(args, **_kw):
                if args[:2] == ["incus", "list"]:
                    return _make_run(0, instances)
                return _make_run(0, "")

            mock_run.side_effect = _run_side
            data = _containers_json()

        assert len(data["containers"]) == 1
        assert data["containers"][0]["name"] == "ct1"

    def test_system_keys_present(self) -> None:
        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   return_value=_make_run(1)):
            data = _containers_json()
        assert {"total", "running", "host_memory", "host_disk", "version"} <= data["system"].keys()

    def test_running_count(self) -> None:
        instances = json.dumps([
            {"name": "ct1", "type": "container", "status": "Running",
             "state": {"network": {}}},
            {"name": "ct2", "type": "container", "status": "Stopped",
             "state": {"network": {}}},
        ])

        def _run_side(args, **_kw):
            if args[:2] == ["incus", "list"]:
                return _make_run(0, instances)
            return _make_run(0, "")

        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   side_effect=_run_side):
            data = _containers_json()

        assert data["system"]["total"] == 2
        assert data["system"]["running"] == 1


class TestHostHelpers:
    def test_host_memory_parses_free_output(self) -> None:
        free_out = "              total        used        free\nMem:           15Gi       8.0Gi       7.0Gi\n"
        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   return_value=_make_run(0, free_out)):
            result = _host_memory()
        assert "/" in result

    def test_host_memory_fallback_on_error(self) -> None:
        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   side_effect=Exception("no free")):
            result = _host_memory()
        assert result == "?"

    def test_host_disk_parses_df_output(self) -> None:
        df_out = "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   20G   30G  40% /\n"
        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   return_value=_make_run(0, df_out)):
            result = _host_disk()
        assert "/" in result

    def test_host_disk_fallback_on_error(self) -> None:
        with patch("waydroid_toolkit.cli.commands.dashboard.subprocess.run",
                   side_effect=Exception("no df")):
            result = _host_disk()
        assert result == "?"

    def test_wdt_version_fallback(self) -> None:
        with patch("importlib.metadata.version", side_effect=Exception("not found")):
            result = _wdt_version()
        assert result == "?"


class TestHttpHandler:
    """Unit-test the HTTP handler routing logic."""

    def _make_handler(self, path: str) -> _Handler:
        handler = _Handler.__new__(_Handler)
        handler.path = path
        handler._headers_sent = []
        handler._response_code = None
        handler._body = b""

        def send_response(code):
            handler._response_code = code

        def send_header(k, v):
            handler._headers_sent.append((k, v))

        def end_headers():
            pass

        class _FakeWfile:
            def write(self, data):
                handler._body += data

        handler.send_response = send_response
        handler.send_header = send_header
        handler.end_headers = end_headers
        handler.wfile = _FakeWfile()
        return handler

    def test_root_returns_html(self) -> None:
        handler = self._make_handler("/")
        with patch("waydroid_toolkit.cli.commands.dashboard._containers_json",
                   return_value={"containers": [], "system": {}}):
            handler.do_GET()
        assert handler._response_code == 200
        assert b"wdt Dashboard" in handler._body

    def test_api_returns_json(self) -> None:
        payload = {"containers": [], "system": {"total": 0, "running": 0,
                                                 "host_memory": "?", "host_disk": "?",
                                                 "version": "?"}}
        handler = self._make_handler("/api/containers")
        with patch("waydroid_toolkit.cli.commands.dashboard._containers_json",
                   return_value=payload):
            handler.do_GET()
        assert handler._response_code == 200
        data = json.loads(handler._body)
        assert "containers" in data

    def test_unknown_path_returns_404(self) -> None:
        handler = self._make_handler("/nonexistent")
        handler.do_GET()
        assert handler._response_code == 404
