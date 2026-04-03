# ruff: noqa: E501
"""wdt dashboard — lightweight web monitoring dashboard for Waydroid.

Serves a single-page HTML dashboard with live Waydroid container status.
Requires python3 (stdlib only — no extra dependencies).

Usage:
  wdt dashboard [--port PORT] [--bind ADDR]
"""

from __future__ import annotations

import http.server
import json
import subprocess
import threading

import click
from rich.console import Console

console = Console()

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>wdt Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
         background: #0d1117; color: #c9d1d9; padding: 20px; }
  h1 { color: #58a6ff; margin-bottom: 5px; font-size: 1.4em; }
  .subtitle { color: #8b949e; margin-bottom: 20px; font-size: 0.9em; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
           gap: 12px; margin-bottom: 20px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; }
  .card h3 { color: #58a6ff; font-size: 0.85em; margin-bottom: 8px; text-transform: uppercase; }
  .card .value { font-size: 1.6em; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; background: #161b22;
          border: 1px solid #30363d; border-radius: 6px; overflow: hidden; }
  th { background: #21262d; color: #8b949e; text-align: left; padding: 10px 14px;
       font-size: 0.8em; text-transform: uppercase; }
  td { padding: 10px 14px; border-top: 1px solid #21262d; font-size: 0.9em; }
  tr:hover { background: #1c2128; }
  .status-running { color: #3fb950; }
  .status-stopped { color: #8b949e; }
  .refresh { color: #8b949e; font-size: 0.8em; margin-top: 15px; }
  .actions { margin-top: 15px; }
  .actions button { background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
                    padding: 6px 14px; border-radius: 4px; cursor: pointer; margin-right: 6px;
                    font-size: 0.85em; }
  .actions button:hover { background: #30363d; }
</style>
</head>
<body>
<h1>wdt Dashboard</h1>
<p class="subtitle">Waydroid Container Monitor</p>

<div class="cards" id="system-cards"></div>

<table>
  <thead>
    <tr><th>Name</th><th>Status</th><th>CPU</th><th>Memory</th><th>Disk</th><th>IP</th></tr>
  </thead>
  <tbody id="ct-table"></tbody>
</table>

<div class="actions">
  <button onclick="refresh()">Refresh</button>
</div>
<p class="refresh" id="last-refresh"></p>

<script>
async function refresh() {
  try {
    const res = await fetch('/api/containers');
    const data = await res.json();

    const cards = document.getElementById('system-cards');
    cards.innerHTML = `
      <div class="card"><h3>Running</h3><div class="value">${data.system.running} / ${data.system.total}</div></div>
      <div class="card"><h3>Host Memory</h3><div class="value" style="font-size:1em">${data.system.host_memory}</div></div>
      <div class="card"><h3>Host Disk</h3><div class="value" style="font-size:1em">${data.system.host_disk}</div></div>
      <div class="card"><h3>Version</h3><div class="value" style="font-size:1em">v${data.system.version}</div></div>
    `;

    const tbody = document.getElementById('ct-table');
    if (data.containers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#8b949e">No containers found</td></tr>';
    } else {
      tbody.innerHTML = data.containers.map(ct => `
        <tr>
          <td><strong>${ct.name}</strong></td>
          <td class="status-${ct.status.toLowerCase()}">${ct.status}</td>
          <td>${ct.cpu || '-'}</td>
          <td>${ct.memory || '-'}</td>
          <td>${ct.disk || '-'}</td>
          <td>${ct.ip}</td>
        </tr>
      `).join('');
    }

    document.getElementById('last-refresh').textContent =
      'Last refresh: ' + new Date().toLocaleTimeString();
  } catch (e) {
    console.error('Refresh failed:', e);
  }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


def _containers_json() -> dict:
    """Collect container data from incus for the API response."""
    result = subprocess.run(
        ["incus", "list", "--format", "json"],
        capture_output=True,
        text=True,
    )
    containers = []
    if result.returncode == 0:
        try:
            instances = json.loads(result.stdout)
        except json.JSONDecodeError:
            instances = []
        for inst in instances:
            if inst.get("type") != "container":
                continue
            name = inst.get("name", "")
            status = inst.get("status", "unknown")

            cpu = _incus_config(name, "limits.cpu")
            mem = _incus_config(name, "limits.memory")
            disk = _incus_device(name, "root", "size")

            ip = "-"
            if status == "Running":
                for iface in inst.get("state", {}).get("network", {}).values():
                    for addr in iface.get("addresses", []):
                        if addr.get("family") == "inet" and not addr["address"].startswith("127."):
                            ip = addr["address"]
                            break
                    if ip != "-":
                        break

            containers.append(
                {
                    "name": name,
                    "status": status,
                    "cpu": cpu,
                    "memory": mem,
                    "disk": disk,
                    "ip": ip,
                }
            )

    total = len(containers)
    running = sum(1 for c in containers if c["status"] == "Running")

    host_memory = _host_memory()
    host_disk = _host_disk()
    version = _wdt_version()

    return {
        "containers": containers,
        "system": {
            "total": total,
            "running": running,
            "host_memory": host_memory,
            "host_disk": host_disk,
            "version": version,
        },
    }


def _incus_config(name: str, key: str) -> str:
    r = subprocess.run(
        ["incus", "config", "get", name, key],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip() or "?"


def _incus_device(name: str, device: str, key: str) -> str:
    r = subprocess.run(
        ["incus", "config", "device", "get", name, device, key],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip() or "?"


def _host_memory() -> str:
    try:
        r = subprocess.run(["free", "-h"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.startswith("Mem:"):
                parts = line.split()
                return f"{parts[2]} / {parts[1]}"
    except Exception:
        pass
    return "?"


def _host_disk() -> str:
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        lines = r.stdout.splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            return f"{parts[2]} / {parts[1]} ({parts[4]})"
    except Exception:
        pass
    return "?"


def _wdt_version() -> str:
    try:
        from importlib.metadata import version

        return version("waydroid-toolkit")
    except Exception:
        return "?"


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/containers":
            data = json.dumps(_containers_json()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        elif self.path in ("/", "/index.html"):
            body = _HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "9")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, *_args: object) -> None:  # silence access log
        pass


@click.command("dashboard")
@click.option("--port", default=8421, show_default=True, help="Listen port.")
@click.option("--bind", default="127.0.0.1", show_default=True, help="Bind address.")
def cmd(port: int, bind: str) -> None:
    """Serve a web monitoring dashboard for Waydroid containers."""
    server = http.server.HTTPServer((bind, port), _Handler)
    console.print("[bold cyan]wdt Web Dashboard[/bold cyan]")
    console.print(f"Listening on [link]http://{bind}:{port}[/link]")
    console.print("Press [bold]Ctrl+C[/bold] to stop\n")

    # Run in a daemon thread so KeyboardInterrupt on the main thread shuts it down.
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        t.join()
    except KeyboardInterrupt:
        server.shutdown()
        console.print("\n[yellow]Dashboard stopped.[/yellow]")
