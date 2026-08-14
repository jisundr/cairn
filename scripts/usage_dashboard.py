#!/usr/bin/env python3
"""Realtime local usage dashboard for the current project.

Reads Claude Code's own session transcripts directly — no separate
capture pipeline. Every session under the current project already has
a JSONL transcript at ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
with per-turn token usage; this just aggregates it. The one thing that
transcript doesn't record is which cairn version was installed at the
time, so that comes from .cairn/version-log.jsonl (written by
hooks/scripts/log-version.sh on SessionStart) instead, joined in by
session id.

stdlib only, no dependencies. Serves:
  GET /            the dashboard page (polls /api/usage)
  GET /api/usage   current aggregation, as JSON
"""

import http.server
import json
import socket
import sys
import time
from pathlib import Path

DEFAULT_PORT = 4756
USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def encode_project_dir(cwd: str) -> str:
    return cwd.replace("/", "-")


def load_version_log(cwd: str) -> dict:
    """session_id -> cairn version, from .cairn/version-log.jsonl."""
    path = Path(cwd) / ".cairn" / "version-log.jsonl"
    versions = {}
    if not path.exists():
        return versions
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = entry.get("session_id")
        if session_id:
            versions[session_id] = entry.get("version", "unknown")
    return versions


def _empty_usage() -> dict:
    return {field: 0 for field in USAGE_FIELDS} | {"calls": 0}


def _parse_session(path: Path, version: str) -> dict | None:
    totals = _empty_usage()
    first_ts = None
    models = set()
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "assistant":
            continue
        message = entry.get("message") or {}
        usage = message.get("usage")
        if not usage:
            continue
        if first_ts is None:
            first_ts = entry.get("timestamp")
        model = message.get("model")
        if model:
            models.add(model)
        for field in USAGE_FIELDS:
            totals[field] += usage.get(field, 0) or 0
        totals["calls"] += 1
    if totals["calls"] == 0:
        return None
    return {
        "session_id": path.stem,
        "timestamp": first_ts,
        "models": sorted(models),
        "version": version,
        **totals,
    }


def aggregate_usage(cwd: str, projects_root: Path) -> dict:
    transcripts_dir = projects_root / encode_project_dir(cwd)
    versions = load_version_log(cwd)

    sessions = []
    if transcripts_dir.exists():
        for jsonl_file in sorted(transcripts_dir.glob("*.jsonl")):
            session = _parse_session(jsonl_file, versions.get(jsonl_file.stem, "unknown"))
            if session:
                sessions.append(session)
    sessions.sort(key=lambda s: s["timestamp"] or "", reverse=True)

    totals = _empty_usage()
    for session in sessions:
        for field in (*USAGE_FIELDS, "calls"):
            totals[field] += session[field]

    return {
        "project": cwd,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totals": totals,
        "sessions": sessions,
    }


PAGE_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>cairn usage</title>
<style>
  body { font: 14px/1.4 -apple-system, sans-serif; margin: 2rem; color: #1a1a1a; background: #fafafa; }
  h1 { font-size: 1.1rem; margin-bottom: .25rem; }
  #project { color: #666; font-size: .85rem; margin-bottom: 1.5rem; }
  .totals { display: flex; gap: 2rem; margin-bottom: 2rem; }
  .stat { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: .75rem 1rem; }
  .stat .label { font-size: .75rem; color: #888; text-transform: uppercase; letter-spacing: .03em; }
  .stat .value { font-size: 1.3rem; font-variant-numeric: tabular-nums; }
  table { border-collapse: collapse; width: 100%; background: #fff; }
  th, td { text-align: left; padding: .4rem .6rem; border-bottom: 1px solid #eee; font-variant-numeric: tabular-nums; }
  th { font-size: .75rem; color: #888; text-transform: uppercase; letter-spacing: .03em; }
  td.num { text-align: right; }
  #updated { color: #aaa; font-size: .75rem; margin-top: 1rem; }
</style>
</head>
<body>
  <h1>cairn usage</h1>
  <div id="project"></div>
  <div class="totals" id="totals"></div>
  <table>
    <thead>
      <tr><th>Session</th><th>Started</th><th class="num">Calls</th><th class="num">In</th><th class="num">Out</th><th class="num">Cache R</th><th class="num">Cache W</th><th>Version</th></tr>
    </thead>
    <tbody id="sessions"></tbody>
  </table>
  <div id="updated"></div>
<script>
function fmt(n) { return n.toLocaleString(); }

async function refresh() {
  const res = await fetch('/api/usage');
  const data = await res.json();

  document.getElementById('project').textContent = data.project;

  const t = data.totals;
  document.getElementById('totals').innerHTML = `
    <div class="stat"><div class="label">Sessions</div><div class="value">${fmt(data.sessions.length)}</div></div>
    <div class="stat"><div class="label">Calls</div><div class="value">${fmt(t.calls)}</div></div>
    <div class="stat"><div class="label">Input</div><div class="value">${fmt(t.input_tokens)}</div></div>
    <div class="stat"><div class="label">Output</div><div class="value">${fmt(t.output_tokens)}</div></div>
    <div class="stat"><div class="label">Cache read</div><div class="value">${fmt(t.cache_read_input_tokens)}</div></div>
    <div class="stat"><div class="label">Cache write</div><div class="value">${fmt(t.cache_creation_input_tokens)}</div></div>
  `;

  document.getElementById('sessions').innerHTML = data.sessions.map(s => `
    <tr>
      <td title="${s.session_id}">${s.session_id.slice(0, 8)}</td>
      <td>${s.timestamp ? new Date(s.timestamp).toLocaleString() : '?'}</td>
      <td class="num">${fmt(s.calls)}</td>
      <td class="num">${fmt(s.input_tokens)}</td>
      <td class="num">${fmt(s.output_tokens)}</td>
      <td class="num">${fmt(s.cache_read_input_tokens)}</td>
      <td class="num">${fmt(s.cache_creation_input_tokens)}</td>
      <td>${s.version}</td>
    </tr>
  `).join('');

  document.getElementById('updated').textContent = 'updated ' + new Date(data.generated).toLocaleTimeString();
}

refresh();
setInterval(refresh, 4000);
</script>
</body>
</html>
"""


def make_handler(cwd: str, projects_root: Path):
    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, code, content_type, body):
            body_bytes = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

        def do_GET(self):
            if self.path == "/":
                self._send(200, "text/html; charset=utf-8", PAGE_HTML)
            elif self.path == "/api/usage":
                data = aggregate_usage(cwd, projects_root)
                self._send(200, "application/json", json.dumps(data))
            else:
                self._send(404, "text/plain", "not found")

        def log_message(self, format, *args):
            pass

    return Handler


def find_free_port(start_port: int) -> int:
    port = start_port
    for _ in range(20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    raise RuntimeError("no free port found")


def main():
    cwd = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    port = find_free_port(DEFAULT_PORT)
    projects_root = Path.home() / ".claude" / "projects"

    handler = make_handler(cwd, projects_root)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"cairn usage dashboard at http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
