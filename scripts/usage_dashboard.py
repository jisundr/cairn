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
  GET /             the dashboard page (polls /api/usage and /api/tracker)
  GET /api/usage    current usage aggregation, as JSON
  GET /api/tracker  docs/.tasks/TRACKER.md rows, as JSON (empty list if absent)
"""

import http.server
import json
import mimetypes
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_PORT = 4756
PLAN_WINDOW_LOOKBACK_SECONDS = 3600  # no HISTORY.md entry precedes PLAN's own line, so approximate its start
HISTORY_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) — ([A-Z][A-Z0-9 \-]*) — (.*)$")
USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)

# USD per 1M tokens. Approximate — verify against current published rates
# before trusting cost totals for anything but a rough sense of spend.
# A model not listed here shows as unpriced rather than silently costing $0.
MODEL_PRICING = {
    "claude-opus-5": {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30},
    "claude-fable-5": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00, "cache_write": 1.00, "cache_read": 0.08},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00, "cache_write": 1.00, "cache_read": 0.08},
}


def calc_cost(model: str, usage: dict) -> float | None:
    """Cost in USD for one call's usage, or None if the model has no pricing entry."""
    rate = MODEL_PRICING.get(model)
    if rate is None:
        return None
    return (
        usage.get("input_tokens", 0) / 1_000_000 * rate["input"]
        + usage.get("output_tokens", 0) / 1_000_000 * rate["output"]
        + usage.get("cache_creation_input_tokens", 0) / 1_000_000 * rate["cache_write"]
        + usage.get("cache_read_input_tokens", 0) / 1_000_000 * rate["cache_read"]
    )


def parse_tracker_md(path: Path) -> list:
    """Rows from a docs/.tasks/TRACKER.md GFM table, skipping the unfilled template row.

    Reads the column set from the table's own header row (not a fixed tuple), so a
    TRACKER.md predating the Milestone column still parses — those rows just get
    milestone="—" via the default below.
    """
    if not path.exists():
        return []
    columns = None
    rows = []
    in_table = False
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0].lower() == "slug":
            columns = tuple(c.lower().replace(" ", "_") for c in cells)
            in_table = True
            continue
        if not in_table or set(cells[0]) <= {"-"}:
            continue
        row = {"milestone": "—", **dict(zip(columns, cells))}
        if row["slug"] == "—" and row["scope"].startswith("["):
            continue
        rows.append(row)
    return rows


def parse_history_md(path: Path) -> list:
    """Timestamped phase lines from a task's HISTORY.md: "<ISO-8601> — <PHASE> — <note>".

    Lines predating this convention (no timestamp prefix) are skipped, not errored —
    a HISTORY.md with zero matching lines just means usage reporting isn't available
    for that task yet.
    """
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().splitlines():
        match = HISTORY_LINE_RE.match(line.strip())
        if match:
            entries.append({"timestamp": match.group(1), "phase": match.group(2), "note": match.group(3)})
    return entries


def parse_state_md(path: Path) -> dict:
    """Generic STATE.md key:value parser. {} if the file doesn't exist.

    Keys are lowercased with spaces replaced by underscores (e.g. "Handoff to"
    -> "handoff_to"). Lines that aren't "Key: value" (the H1 title, blank
    lines, prose without a colon) are skipped.
    """
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip().lower().replace(" ", "_")] = value.strip()
    return result


def _tmux_has_session(branch: str) -> bool | None:
    """True/False if tmux answered, None if the tmux binary itself is unavailable."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", branch], capture_output=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.returncode == 0


def _tmux_pane_tail(branch: str, lines: int = 20) -> list | None:
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", branch, "-p"], capture_output=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.decode("utf-8", errors="replace")
    return text.splitlines()[-lines:]


def discover_swarms(cwd: str) -> list:
    """Mode: Unattended tasks under docs/.tasks/*/STATE.md, with tmux liveness."""
    swarms = []
    for task_dir in sorted(Path(cwd).glob("docs/.tasks/*/")):
        state = parse_state_md(task_dir / "STATE.md")
        if state.get("mode") != "Unattended":
            continue
        history = parse_history_md(task_dir / "HISTORY.md")
        branch = state.get("branch", "")
        tmux_alive = _tmux_has_session(branch) if branch else None
        phase = state.get("phase", "")
        pane_tail = _tmux_pane_tail(branch) if (phase == "HANDOFF NEEDED" and tmux_alive) else None
        swarms.append({
            "slug": task_dir.name,
            "phase": phase,
            "status": state.get("status", ""),
            "handoff_to": state.get("handoff_to", ""),
            "worktree": state.get("worktree", ""),
            "branch": branch,
            "key_info": state.get("key_info", ""),
            "last_history": history[-1] if history else None,
            "recent_history": list(reversed(history[-5:])),
            "history_count": len(history),
            "tmux_alive": tmux_alive,
            "pane_tail": pane_tail,
        })
    return swarms


def serve_static(dist_dir: Path, request_path: str):
    """Resolve a static asset under dist_dir, falling back to index.html for
    the SPA root/any client-side route. None if dist_dir/index.html itself
    doesn't exist (submodule not initialized)."""
    index = dist_dir / "index.html"
    if not index.exists():
        return None
    rel = request_path.lstrip("/")
    candidate = (dist_dir / rel) if rel else index
    try:
        resolved = candidate.resolve()
        resolved.relative_to(dist_dir.resolve())
    except (ValueError, OSError):
        candidate = index
    else:
        if not resolved.is_file():
            candidate = index
    content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
    return content_type, candidate.read_bytes()


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _format_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def phase_windows(entries: list) -> list:
    """[(phase, window_start, window_end), ...] — each entry's timestamp closes its own
    phase's window; the previous entry's timestamp opens it. PLAN (the first entry) has
    no preceding line, so its window is approximated as the PLAN_WINDOW_LOOKBACK_SECONDS
    before it closed — the same "approximate, documented" tradeoff as MODEL_PRICING.
    """
    if not entries:
        return []
    windows = []
    for i, entry in enumerate(entries):
        if i == 0:
            start = _format_iso(_parse_iso(entry["timestamp"]) - timedelta(seconds=PLAN_WINDOW_LOOKBACK_SECONDS))
        else:
            start = entries[i - 1]["timestamp"]
        windows.append((entry["phase"], start, entry["timestamp"]))
    return windows


def usage_by_windows(cwd: str, projects_root: Path, windows: list) -> dict:
    """Turn-level (not session-level) usage bucketed by phase window.

    Session-level totals aren't fine-grained enough here: a single session's transcript
    can span every phase of a task (e.g. an Attended run stays in one conversation from
    PLAN through PUBLISH), so bucketing has to happen per assistant turn, by that turn's
    own timestamp, not per session.
    """
    buckets = {label: _empty_usage() | {"cost": 0.0, "unpriced_calls": 0} for label, _, _ in windows}
    transcripts_dir = projects_root / encode_project_dir(cwd)
    if not transcripts_dir.exists():
        return buckets
    parsed_windows = [(label, _parse_iso(start), _parse_iso(end)) for label, start, end in windows]
    for jsonl_file in transcripts_dir.glob("*.jsonl"):
        try:
            lines = jsonl_file.read_text().splitlines()
        except OSError:
            continue
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
            ts = entry.get("timestamp")
            if not usage or not ts:
                continue
            turn_ts = _parse_iso(ts)
            for label, start, end in parsed_windows:
                if start <= turn_ts <= end:
                    bucket = buckets[label]
                    for field in USAGE_FIELDS:
                        bucket[field] += usage.get(field, 0) or 0
                    bucket["calls"] += 1
                    call_cost = calc_cost(message.get("model"), usage) if message.get("model") else None
                    if call_cost is None:
                        bucket["unpriced_calls"] += 1
                    else:
                        bucket["cost"] += call_cost
                    break
    return buckets


def build_task_report(cwd: str, projects_root: Path, slug: str) -> str:
    """Markdown usage table for a task, for inclusion in its PR/MR body (Publish Mode)."""
    task_dirs = sorted(Path(cwd).glob(f"docs/.tasks/*-{slug}"))
    if not task_dirs:
        return f"Usage: unavailable (no task folder found for slug '{slug}')"
    entries = parse_history_md(task_dirs[-1] / "HISTORY.md")
    if not entries:
        return "Usage: unavailable (predates timestamp tracking)"

    windows = phase_windows(entries)
    stats = usage_by_windows(cwd, projects_root, windows)

    total = _empty_usage() | {"cost": 0.0, "unpriced_calls": 0}
    rows = []
    for label, _, _ in windows:
        row = stats[label]
        tokens = sum(row[f] for f in USAGE_FIELDS)
        rows.append(f"| {label} | {tokens:,} | ${row['cost']:.2f} |")
        for field in (*USAGE_FIELDS, "calls"):
            total[field] += row[field]
        total["cost"] += row["cost"]
        total["unpriced_calls"] += row["unpriced_calls"]

    total_tokens = sum(total[f] for f in USAGE_FIELDS)
    lines = [
        "| Phase | Tokens | Cost |",
        "|---|---|---|",
        *rows,
        f"| **Total** | **{total_tokens:,}** | **${total['cost']:.2f}** |",
        "",
        "_Approximate: time-window estimate correlated from session transcripts by "
        "timestamp, not an exact per-task measurement. PLAN's window is backdated "
        f"{PLAN_WINDOW_LOOKBACK_SECONDS // 60} minutes since no earlier boundary exists._",
    ]
    if total["unpriced_calls"]:
        lines.insert(-1, f"_{total['unpriced_calls']} call(s) used a model with no pricing entry — excluded from cost._")
    return "\n".join(lines)


def build_window_report(cwd: str, projects_root: Path, start_iso: str, end_iso: str) -> str:
    """Markdown usage table for a single time window — Lightweight mode's variant of
    build_task_report, for paths with no HISTORY.md/task folder to read phases from."""
    transcripts_dir = projects_root / encode_project_dir(cwd)
    windows = [("Work", start_iso, end_iso)]
    stats = usage_by_windows(cwd, projects_root, windows)
    row = stats["Work"]
    if not transcripts_dir.exists() or row["calls"] == 0:
        return "Usage: unavailable (no transcripts found for this project/window)"
    tokens = sum(row[f] for f in USAGE_FIELDS)

    lines = [
        "| Phase | Tokens | Cost |",
        "|---|---|---|",
        f"| Work | {tokens:,} | ${row['cost']:.2f} |",
        f"| **Total** | **{tokens:,}** | **${row['cost']:.2f}** |",
    ]
    if row["unpriced_calls"]:
        lines.append(f"_{row['unpriced_calls']} call(s) used a model with no pricing entry — excluded from cost._")
    return "\n".join(lines)


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


def _merge_call_counts(target: dict, name: str) -> None:
    target[name] = target.get(name, 0) + 1


def _merge_model_stats(target: dict, model: str, usage: dict, cost) -> None:
    row = target.setdefault(model, _empty_usage() | {"cost": 0.0})
    for field in USAGE_FIELDS:
        row[field] += usage.get(field, 0) or 0
    row["calls"] += 1
    if cost is not None:
        row["cost"] += cost


def _parse_session(path: Path, version: str) -> dict | None:
    totals = _empty_usage()
    cost = 0.0
    unpriced_calls = 0
    first_ts = None
    models = set()
    model_stats = {}
    subagent_calls = {}
    skill_calls = {}
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

        call_cost = calc_cost(model, usage) if model else None
        if call_cost is None:
            unpriced_calls += 1
        else:
            cost += call_cost
        if model:
            _merge_model_stats(model_stats, model, usage, call_cost)

        for block in message.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            block_input = block.get("input") or {}
            if block.get("name") == "Agent" and block_input.get("subagent_type"):
                _merge_call_counts(subagent_calls, block_input["subagent_type"])
            elif block.get("name") == "Skill" and block_input.get("skill"):
                _merge_call_counts(skill_calls, block_input["skill"])
    if totals["calls"] == 0:
        return None
    return {
        "session_id": path.stem,
        "timestamp": first_ts,
        "models": sorted(models),
        "version": version,
        "cost": cost,
        "unpriced_calls": unpriced_calls,
        **totals,
        "_model_stats": model_stats,
        "_subagent_calls": subagent_calls,
        "_skill_calls": skill_calls,
    }


def _ranked(counts: dict, key_name: str) -> list:
    return sorted(
        ({key_name: name, "calls": calls} for name, calls in counts.items()),
        key=lambda row: row["calls"],
        reverse=True,
    )


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

    totals = _empty_usage() | {"cost": 0.0, "unpriced_calls": 0}
    by_model = {}
    by_version = {}
    by_subagent = {}
    by_skill = {}
    for session in sessions:
        for field in (*USAGE_FIELDS, "calls"):
            totals[field] += session[field]
        totals["cost"] += session["cost"]
        totals["unpriced_calls"] += session["unpriced_calls"]

        version_row = by_version.setdefault(session["version"], _empty_usage() | {"cost": 0.0})
        for field in (*USAGE_FIELDS, "calls"):
            version_row[field] += session[field]
        version_row["cost"] += session["cost"]

        for model, stats in session.pop("_model_stats").items():
            row = by_model.setdefault(model, _empty_usage() | {"cost": 0.0})
            for field in (*USAGE_FIELDS, "calls"):
                row[field] += stats[field]
            row["cost"] += stats["cost"]

        for name, calls in session.pop("_subagent_calls").items():
            by_subagent[name] = by_subagent.get(name, 0) + calls
        for name, calls in session.pop("_skill_calls").items():
            by_skill[name] = by_skill.get(name, 0) + calls

    return {
        "project": cwd,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "totals": totals,
        "sessions": sessions,
        "by_model": sorted(
            ({"model": m, **s} for m, s in by_model.items()), key=lambda r: r["cost"], reverse=True
        ),
        "by_version": sorted(
            ({"version": v, **s} for v, s in by_version.items()), key=lambda r: r["cost"], reverse=True
        ),
        "by_subagent": _ranked(by_subagent, "name"),
        "by_skill": _ranked(by_skill, "name"),
    }



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
            if self.path.startswith("/api/"):
                if self.path == "/api/usage":
                    data = aggregate_usage(cwd, projects_root)
                    self._send(200, "application/json", json.dumps(data))
                elif self.path == "/api/tracker":
                    rows = parse_tracker_md(Path(cwd) / "docs" / ".tasks" / "TRACKER.md")
                    self._send(200, "application/json", json.dumps(rows))
                elif self.path == "/api/swarms":
                    swarms = discover_swarms(cwd)
                    self._send(200, "application/json", json.dumps(swarms))
                else:
                    self._send(404, "text/plain", "not found")
                return
            result = serve_static(Path(cwd) / "dashboard" / "dist", self.path)
            if result is None:
                self._send(
                    500, "text/plain",
                    "dashboard/dist/ not found. Run: git submodule update --init dashboard",
                )
                return
            content_type, body = result
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

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
    projects_root = Path.home() / ".claude" / "projects"

    if len(sys.argv) > 1 and sys.argv[1] == "--task-report":
        if len(sys.argv) < 3:
            print("usage: usage_dashboard.py --task-report <slug> [cwd]", file=sys.stderr)
            sys.exit(1)
        slug = sys.argv[2]
        cwd = sys.argv[3] if len(sys.argv) > 3 else str(Path.cwd())
        print(build_task_report(cwd, projects_root, slug))
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--window-report":
        if len(sys.argv) < 4:
            print("usage: usage_dashboard.py --window-report <start-iso> <end-iso> [cwd]", file=sys.stderr)
            sys.exit(1)
        start_iso, end_iso = sys.argv[2], sys.argv[3]
        cwd = sys.argv[4] if len(sys.argv) > 4 else str(Path.cwd())
        print(build_window_report(cwd, projects_root, start_iso, end_iso))
        return

    cwd = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    port = find_free_port(DEFAULT_PORT)

    handler = make_handler(cwd, projects_root)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"cairn usage dashboard at http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
