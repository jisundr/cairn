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


def discover_swarms(cwd: str) -> list:
    """Mode: Unattended tasks under docs/.tasks/*/STATE.md, with tmux liveness."""
    swarms = []
    for task_dir in sorted(Path(cwd).glob("docs/.tasks/*/")):
        state = parse_state_md(task_dir / "STATE.md")
        if state.get("mode") != "Unattended":
            continue
        history = parse_history_md(task_dir / "HISTORY.md")
        branch = state.get("branch", "")
        swarms.append({
            "slug": task_dir.name,
            "phase": state.get("phase", ""),
            "status": state.get("status", ""),
            "handoff_to": state.get("handoff_to", ""),
            "worktree": state.get("worktree", ""),
            "branch": branch,
            "key_info": state.get("key_info", ""),
            "last_history": history[-1] if history else None,
            "recent_history": list(reversed(history[-5:])),
            "history_count": len(history),
            "tmux_alive": _tmux_has_session(branch) if branch else None,
        })
    return swarms


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


PAGE_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Cairn Dashboard</title>
<style>
  :root {
    --bg: #f6f4ee; --card: #ffffff; --border: #e6e2d8; --text: #1c1c1a; --dim: #6b6b62;
    --faint: #9a978c; --accent: #3d8b5f; --accent-2: #d9a441; --danger: #b5482f;
    --idea: #8a8a80; --groomed: #4472c4; --progress: #d9a441; --review: #8757b0;
    --blocked: #b5482f; --done: #3d8b5f;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #15171a; --card: #1e2124; --border: #2c2f33; --text: #e9e7e0; --dim: #9c9a92;
      --faint: #6d6b63; --accent: #4fae7c; --accent-2: #e0b256; --danger: #d16249;
    }
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body { font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; color: var(--text); background: var(--bg); display: flex; flex-direction: column; }
  header { display: flex; align-items: center; gap: 1.5rem; padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
  h1 { font-size: 1.05rem; margin: 0; font-weight: 700; }
  h1 span { color: var(--accent); }
  .tabs { display: flex; gap: .25rem; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: .2rem; }
  .tab { padding: .4rem .9rem; border-radius: 6px; cursor: pointer; color: var(--dim); font-size: .85rem; }
  .tab.active { background: var(--card); color: var(--text); box-shadow: 0 1px 2px rgba(0,0,0,.06); }
  #project { color: var(--faint); font-size: .8rem; margin-left: auto; }
  .toolbar { display: flex; gap: 1.5rem; align-items: center; padding: .85rem 1.5rem; flex-wrap: wrap; }
  .range { display: flex; gap: .25rem; background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: .2rem; }
  .range button { border: none; background: none; padding: .35rem .7rem; border-radius: 6px; cursor: pointer; color: var(--dim); font-size: .8rem; }
  .range button.active { background: var(--bg); color: var(--text); }
  main { padding: 0 1.5rem 2rem; flex: 1 1 auto; min-height: 0; overflow-y: auto; }
  .view { display: none; }
  .view.active { display: flex; flex-direction: column; height: 100%; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: .9rem 1.1rem; }
  .stat .label { font-size: .7rem; color: var(--faint); text-transform: uppercase; letter-spacing: .04em; margin-bottom: .3rem; }
  .stat .value { font-size: 1.4rem; font-variant-numeric: tabular-nums; font-weight: 600; }
  .stat .value.accent { color: var(--accent); }
  .stat .sub { font-size: .72rem; color: var(--faint); margin-top: .2rem; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1.1rem 1.2rem; margin-bottom: 1rem; }
  .card .head { font-size: .7rem; color: var(--faint); text-transform: uppercase; letter-spacing: .04em; margin-bottom: .9rem; }
  .chart-card svg { width: 100%; height: 180px; overflow: visible; }
  .chart-card .bar { fill: var(--accent); }
  .chart-card .bar:hover { fill: var(--accent-2); }
  .chart-card .axis { font-size: 10px; fill: var(--faint); }
  .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
  .rank-row { display: grid; grid-template-columns: minmax(0,1fr) auto; gap: .5rem; align-items: center; padding: .35rem 0; font-size: .82rem; }
  .rank-row .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rank-row .bar-track { grid-column: 1 / -1; height: 5px; background: var(--bg); border-radius: 3px; overflow: hidden; margin-bottom: .5rem; }
  .rank-row .bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent-2)); }
  .rank-row .num { font-variant-numeric: tabular-nums; color: var(--dim); white-space: nowrap; }
  .empty { color: var(--faint); font-size: .85rem; padding: .5rem 0; }
  table { border-collapse: collapse; width: 100%; }
  th, td { text-align: left; padding: .5rem .6rem; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; }
  th { font-size: .68rem; color: var(--faint); text-transform: uppercase; letter-spacing: .04em; font-weight: 600; }
  td.num { text-align: right; }
  .pill { display: inline-block; padding: .15rem .55rem; border-radius: 99px; font-size: .72rem; font-weight: 600; color: #fff; }
  #updated { color: var(--faint); font-size: .72rem; padding: 1rem 1.5rem 2rem; }
  .unpriced-note { color: var(--danger); font-size: .72rem; margin-top: -.3rem; margin-bottom: 1rem; }

  .subtabs { display: flex; gap: .25rem; background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: .2rem; width: fit-content; margin-bottom: 1rem; }
  .subtab { padding: .35rem .85rem; border-radius: 6px; cursor: pointer; color: var(--dim); font-size: .8rem; }
  .subtab.active { background: var(--bg); color: var(--text); }

  .board { display: flex; gap: .9rem; overflow-x: auto; overflow-y: auto; padding-bottom: .5rem; align-items: flex-start; flex: 1 1 auto; min-height: 0; }
  .col { flex: 0 0 260px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: .8rem; border-top: 3px solid var(--idea); }
  .col-groomed { border-top-color: var(--groomed); }
  .col-progress { border-top-color: var(--progress); }
  .col-review { border-top-color: var(--review); }
  .col-blocked { border-top-color: var(--blocked); }
  .col-done { border-top-color: var(--done); }
  .col h2 { font-size: .68rem; text-transform: uppercase; letter-spacing: .04em; color: var(--faint); margin: .2rem .2rem .7rem; display: flex; justify-content: space-between; font-weight: 600; }
  .task-card { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: .6rem .7rem; margin-bottom: .6rem; }
  .card-milestone { font-size: .66rem; color: var(--faint); text-transform: uppercase; letter-spacing: .04em; margin-bottom: .3rem; }
  .task-card .slug { font-weight: 600; font-size: .82rem; }
  .task-card .scope { color: var(--dim); font-size: .78rem; margin-top: .2rem; line-height: 1.35; }
  .task-card .foot { display: flex; gap: .35rem; flex-wrap: wrap; margin-top: .5rem; }
  .tag { background: var(--card); border: 1px solid var(--border); border-radius: 5px; padding: .1rem .45rem; color: var(--faint); font-size: .68rem; }

  .road-wrap { overflow-x: auto; overflow-y: auto; padding-bottom: .5rem; flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }
  .rmap { display: flex; align-items: flex-start; min-width: min-content; flex: 1 1 auto; }
  .rstation { flex: 0 0 260px; }
  .rnoderow { position: relative; height: 44px; display: flex; align-items: center; justify-content: center; }
  .rnoderow::before { content: ""; position: absolute; top: 50%; left: 0; right: 0; height: 2px; transform: translateY(-50%); background: var(--border); }
  .rstation.filled .rnoderow::before { background: var(--accent); }
  .rstation:first-child .rnoderow::before { left: 50%; }
  .rstation:last-child .rnoderow::before { right: 50%; }
  .rnode { position: relative; z-index: 1; width: 40px; height: 40px; display: grid; place-items: center; color: var(--dim); background: var(--bg); border-radius: 50%; }
  .rbody { padding: .9rem 1rem 0; }
  .rname { font-weight: 600; font-size: .82rem; }
  .rname span.rcount { font-weight: 400; }
  .rcount { color: var(--faint); font-size: .72rem; margin-left: .3rem; }
  .icard { border-left: 3px solid var(--accent); background: var(--bg); border-radius: 6px; padding: .4rem .55rem; margin-top: .5rem; font-size: .78rem; }
  .icard.is-done { color: var(--faint); text-decoration: line-through; text-decoration-color: var(--border); border-left-color: var(--done); }
  .blocked-badge { align-self: flex-start; background: var(--blocked); color: #fff; border-radius: 99px; padding: .15rem .6rem; font-size: .72rem; font-weight: 600; margin-bottom: .8rem; flex: 0 0 auto; }

  .hidden { display: none !important; }
</style>
</head>
<body>
  <header>
    <h1>Cairn <span>Dashboard</span></h1>
    <div class="tabs">
      <div class="tab active" data-view="usage">Usage</div>
      <div class="tab" data-view="tracker">Tracker</div>
    </div>
    <div id="project"></div>
  </header>
  <div class="toolbar">
    <div class="range" id="range">
      <button data-range="today">Today</button>
      <button data-range="7" class="active">7 days</button>
      <button data-range="30">30 days</button>
      <button data-range="month">Month</button>
      <button data-range="all">All</button>
    </div>
  </div>
  <main>
    <section class="view active" id="view-usage">
      <div class="stat-grid" id="stat-grid"></div>
      <div id="unpriced-note"></div>
      <div class="card chart-card">
        <div class="head">Cost over time</div>
        <svg id="chart"></svg>
      </div>
      <div class="card-grid">
        <div class="card"><div class="head">By model (all time)</div><div id="by-model"></div></div>
        <div class="card"><div class="head">By cairn version (all time)</div><div id="by-version"></div></div>
        <div class="card"><div class="head">Top subagents (all time)</div><div id="by-subagent"></div></div>
        <div class="card"><div class="head">Top skills (all time)</div><div id="by-skill"></div></div>
      </div>
      <div class="card">
        <div class="head">Sessions</div>
        <table>
          <thead>
            <tr><th>Session</th><th>Started</th><th class="num">Calls</th><th class="num">Cost</th><th class="num">In</th><th class="num">Out</th><th class="num">Cache R</th><th class="num">Cache W</th><th>Version</th></tr>
          </thead>
          <tbody id="sessions"></tbody>
        </table>
      </div>
    </section>
    <section class="view" id="view-tracker">
      <div class="subtabs" id="tracker-subtabs">
        <div class="subtab active" data-sub="board">Board</div>
        <div class="subtab" data-sub="road">Roadmap</div>
      </div>
      <div class="board" id="board"></div>
      <div class="road-wrap hidden" id="road-wrap">
        <div class="blocked-badge hidden" id="blocked-badge"></div>
        <div class="rmap" id="road"></div>
      </div>
      <div class="empty" id="tracker-empty" style="display:none">No tasks tracked yet — run <code>project-manager</code> to decompose a PRD into docs/.tasks/TRACKER.md.</div>
    </section>
  </main>
  <div id="updated"></div>
<script>
function fmt(n) { return Math.round(n).toLocaleString(); }
function usd(n) { return '$' + n.toFixed(2); }
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// Tab state lives in location.hash (#usage, #tracker, #tracker/road) so a refresh or a
// shared link lands back on the same view instead of always resetting to Usage.
function setTab(view, sub, pushHash) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === view));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + view).classList.add('active');
  document.querySelector('.toolbar').classList.toggle('hidden', view !== 'usage');

  if (view === 'tracker') {
    const activeSub = sub === 'road' ? 'road' : 'board';
    document.querySelectorAll('#tracker-subtabs .subtab').forEach(t => t.classList.toggle('active', t.dataset.sub === activeSub));
    const hasRows = document.getElementById('tracker-empty').style.display !== 'block';
    document.getElementById('board').classList.toggle('hidden', !hasRows || activeSub !== 'board');
    document.getElementById('road-wrap').classList.toggle('hidden', !hasRows || activeSub !== 'road');
  }

  if (pushHash) location.hash = view === 'tracker' && sub === 'road' ? 'tracker/road' : view;
}

function tabFromHash() {
  const [view, sub] = location.hash.replace('#', '').split('/');
  return view === 'tracker' ? ['tracker', sub] : ['usage', undefined];
}

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const sub = document.querySelector('#tracker-subtabs .subtab.active')?.dataset.sub;
    setTab(tab.dataset.view, sub, true);
  });
});

window.addEventListener('hashchange', () => setTab(...tabFromHash(), false));

let currentRange = '7';
document.querySelectorAll('#range button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#range button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentRange = btn.dataset.range;
    render();
  });
});

let usageData = null;

function sessionsInRange(sessions) {
  if (currentRange === 'all') return sessions;
  const now = new Date();
  let cutoff;
  if (currentRange === 'today') {
    cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  } else if (currentRange === 'month') {
    cutoff = new Date(now.getFullYear(), now.getMonth(), 1);
  } else {
    cutoff = new Date(now.getTime() - Number(currentRange) * 86400000);
  }
  return sessions.filter(s => s.timestamp && new Date(s.timestamp) >= cutoff);
}

function rankRows(rows, nameKey, valueKey, valueFmt) {
  if (!rows.length) return '<div class="empty">No data yet.</div>';
  const max = Math.max(...rows.map(r => r[valueKey]), 1);
  return rows.slice(0, 8).map(r => `
    <div class="rank-row">
      <div class="name">${esc(r[nameKey])}</div>
      <div class="num">${valueFmt(r[valueKey])}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${(r[valueKey] / max * 100).toFixed(1)}%"></div></div>
    </div>
  `).join('');
}

function renderChart(sessions) {
  const byDay = {};
  for (const s of sessions) {
    if (!s.timestamp) continue;
    const day = s.timestamp.slice(0, 10);
    byDay[day] = (byDay[day] || 0) + s.cost;
  }
  const days = Object.keys(byDay).sort();
  const svg = document.getElementById('chart');
  if (!days.length) { svg.innerHTML = ''; return; }
  const max = Math.max(...days.map(d => byDay[d]), 0.01);
  const w = svg.clientWidth || 800, h = 160, barGap = 4;
  const barW = Math.max(2, w / days.length - barGap);
  let bars = '';
  days.forEach((d, i) => {
    const barH = (byDay[d] / max) * (h - 20);
    const x = i * (barW + barGap);
    bars += `<rect class="bar" x="${x}" y="${h - barH}" width="${barW}" height="${barH}"><title>${d}: ${usd(byDay[d])}</title></rect>`;
  });
  const labelEvery = Math.max(1, Math.ceil(days.length / 8));
  let labels = '';
  days.forEach((d, i) => {
    if (i % labelEvery !== 0) return;
    labels += `<text class="axis" x="${i * (barW + barGap)}" y="${h + 14}">${d.slice(5)}</text>`;
  });
  svg.setAttribute('viewBox', `0 0 ${w} ${h + 20}`);
  svg.innerHTML = bars + labels;
}

function render() {
  if (!usageData) return;
  const sessions = sessionsInRange(usageData.sessions);

  document.getElementById('project').textContent = usageData.project;

  const t = sessions.reduce((acc, s) => {
    acc.calls += s.calls; acc.cost += s.cost; acc.unpriced_calls += s.unpriced_calls;
    acc.input_tokens += s.input_tokens; acc.output_tokens += s.output_tokens;
    acc.cache_read_input_tokens += s.cache_read_input_tokens; acc.cache_creation_input_tokens += s.cache_creation_input_tokens;
    return acc;
  }, { calls: 0, cost: 0, unpriced_calls: 0, input_tokens: 0, output_tokens: 0, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 });
  const totalTokens = t.input_tokens + t.output_tokens + t.cache_read_input_tokens + t.cache_creation_input_tokens;
  const cacheHit = (t.cache_read_input_tokens + t.input_tokens) > 0
    ? (t.cache_read_input_tokens / (t.cache_read_input_tokens + t.input_tokens) * 100) : 0;

  document.getElementById('stat-grid').innerHTML = `
    <div class="stat"><div class="label">Cost</div><div class="value accent">${usd(t.cost)}</div></div>
    <div class="stat"><div class="label">Tokens</div><div class="value">${fmt(totalTokens)}</div></div>
    <div class="stat"><div class="label">Calls</div><div class="value">${fmt(t.calls)}</div></div>
    <div class="stat"><div class="label">Sessions</div><div class="value">${fmt(sessions.length)}</div></div>
    <div class="stat"><div class="label">Cache hit</div><div class="value">${cacheHit.toFixed(1)}%</div></div>
  `;
  document.getElementById('unpriced-note').innerHTML = t.unpriced_calls
    ? `<div class="unpriced-note">${fmt(t.unpriced_calls)} call(s) used a model with no pricing entry — excluded from cost total.</div>` : '';

  renderChart(sessions);

  document.getElementById('by-model').innerHTML = rankRows(usageData.by_model, 'model', 'cost', usd);
  document.getElementById('by-version').innerHTML = rankRows(usageData.by_version, 'version', 'cost', usd);
  document.getElementById('by-subagent').innerHTML = rankRows(usageData.by_subagent, 'name', 'calls', fmt);
  document.getElementById('by-skill').innerHTML = rankRows(usageData.by_skill, 'name', 'calls', fmt);

  document.getElementById('sessions').innerHTML = sessions.map(s => `
    <tr>
      <td title="${esc(s.session_id)}">${esc(s.session_id.slice(0, 8))}</td>
      <td>${s.timestamp ? new Date(s.timestamp).toLocaleString() : '?'}</td>
      <td class="num">${fmt(s.calls)}</td>
      <td class="num">${usd(s.cost)}</td>
      <td class="num">${fmt(s.input_tokens)}</td>
      <td class="num">${fmt(s.output_tokens)}</td>
      <td class="num">${fmt(s.cache_read_input_tokens)}</td>
      <td class="num">${fmt(s.cache_creation_input_tokens)}</td>
      <td>${esc(s.version)}</td>
    </tr>
  `).join('');

  document.getElementById('updated').textContent = 'updated ' + new Date(usageData.generated).toLocaleTimeString();
}

document.querySelectorAll('#tracker-subtabs .subtab').forEach(tab => {
  tab.addEventListener('click', () => setTab('tracker', tab.dataset.sub, true));
});

const BOARD_COLUMNS = [
  { key: 'idea', label: 'Idea', cls: '' },
  { key: 'groomed', label: 'Groomed', cls: 'col-groomed' },
  { key: 'progress', label: 'In Progress', cls: 'col-progress' },
  { key: 'review', label: 'In Review', cls: 'col-review' },
  { key: 'blocked', label: 'Blocked', cls: 'col-blocked' },
  { key: 'done', label: 'Done', cls: 'col-done' },
];
function stageKey(status) {
  const s = status.toLowerCase();
  if (s.startsWith('in progress')) return 'progress';
  if (s === 'in review') return 'review';
  if (s === 'blocked') return 'blocked';
  if (s === 'done') return 'done';
  if (s === 'groomed') return 'groomed';
  return 'idea';
}
const isDoneRow = r => stageKey(r.status) === 'done';
const isActiveRow = r => ['progress', 'review'].includes(stageKey(r.status));

function taskCardHtml(r) {
  const ticket = r.ticket && r.ticket !== '—' ? `<span class="tag">${esc(r.ticket)}</span>` : '';
  const phase = r.status.includes(':') ? `<span class="tag">${esc(r.status.split(':').slice(1).join(':').trim())}</span>` : '';
  const milestone = r.milestone && r.milestone !== '—' ? `<div class="card-milestone">${esc(r.milestone)}</div>` : '';
  return `<div class="task-card">
    ${milestone}
    <div class="slug">${esc(r.slug)}</div>
    <div class="scope">${esc(r.scope)}</div>
    <div class="foot">${ticket}${phase}</div>
  </div>`;
}

function renderBoard(rows) {
  document.getElementById('board').innerHTML = BOARD_COLUMNS.map(col => {
    const items = rows.filter(r => stageKey(r.status) === col.key);
    return `<div class="col ${col.cls}">
      <h2>${col.label}<span>${items.length}</span></h2>
      ${items.length ? items.map(taskCardHtml).join('') : '<div class="empty">—</div>'}
    </div>`;
  }).join('');
}

// progress ring: track + accent arc; center shows a check when done, else the station number
function ring(pct, state, n) {
  const r = 15, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
  const arc = state === 'done' ? 'var(--done)' : 'var(--accent)';
  const center = state === 'done'
    ? '<path d="M-5 0.5 L-1.5 4 L5.5 -4.5" fill="none" stroke="var(--done)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
    : `<text x="0" y="4" text-anchor="middle" font-size="12" font-weight="600" fill="currentColor">${n}</text>`;
  return `<svg viewBox="-22 -22 44 44" width="40" height="40" aria-hidden="true">
    <circle r="${r}" fill="none" stroke="var(--border)" stroke-width="3"/>
    <circle r="${r}" fill="none" stroke="${arc}" stroke-width="3" stroke-linecap="round"
      stroke-dasharray="${c.toFixed(2)}" stroke-dashoffset="${off.toFixed(2)}" transform="rotate(-90)"/>
    ${center}</svg>`;
}

function renderRoadmap(rows) {
  const blocked = rows.filter(r => stageKey(r.status) === 'blocked');
  const badge = document.getElementById('blocked-badge');
  badge.classList.toggle('hidden', blocked.length === 0);
  badge.textContent = `${blocked.length} blocked`;

  // group by Milestone — a distinct axis from Status/Board: one milestone spans many statuses at once.
  const groups = new Map();
  const order = [];
  for (const r of rows) {
    const key = (r.milestone && r.milestone !== '—') ? r.milestone : 'Unsorted';
    if (!groups.has(key)) { groups.set(key, []); order.push(key); }
    groups.get(key).push(r);
  }
  const stations = order.filter(k => k !== 'Unsorted');
  if (groups.has('Unsorted')) stations.push('Unsorted');

  if (!stations.length) {
    document.getElementById('road').innerHTML = '<div class="empty">No tasks tracked yet.</div>';
    return;
  }

  const info = stations.map(name => {
    const items = groups.get(name);
    const done = items.filter(isDoneRow).length;
    const state = done === items.length ? 'done' : (done > 0 || items.some(isActiveRow)) ? 'active' : 'upcoming';
    return { name, items, done, state };
  });
  let lastReached = -1;
  info.forEach((x, i) => { if (x.state !== 'upcoming') lastReached = i; });

  document.getElementById('road').innerHTML = info.map((x, i) => {
    const pct = x.items.length ? Math.round(x.done / x.items.length * 100) : 0;
    const label = x.state === 'done' ? 'Done' : x.state === 'active' ? 'In progress' : 'Upcoming';
    return `<div class="rstation ${i <= lastReached ? 'filled' : ''}">
      <div class="rnoderow"><div class="rnode">${ring(pct, x.state, i + 1)}</div></div>
      <div class="rbody">
        <div class="rname">${esc(x.name)}<span class="rcount">${x.done}/${x.items.length} · ${label}</span></div>
        ${x.items.map(r => `<div class="icard${isDoneRow(r) ? ' is-done' : ''}">${esc(r.slug)} — ${esc(r.scope)}</div>`).join('')}
      </div>
    </div>`;
  }).join('');
}

async function refreshTracker() {
  const res = await fetch('/api/tracker');
  const rows = await res.json();
  const hasRows = rows.length > 0;
  document.getElementById('tracker-empty').style.display = hasRows ? 'none' : 'block';
  document.getElementById('tracker-subtabs').classList.toggle('hidden', !hasRows);
  const boardActive = document.querySelector('#tracker-subtabs .subtab.active').dataset.sub === 'board';
  document.getElementById('board').classList.toggle('hidden', !hasRows || !boardActive);
  document.getElementById('road-wrap').classList.toggle('hidden', !hasRows || boardActive);
  renderBoard(rows);
  renderRoadmap(rows);
}

async function refresh() {
  const res = await fetch('/api/usage');
  usageData = await res.json();
  render();
  await refreshTracker();
}

setTab(...tabFromHash(), false);
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
            elif self.path == "/api/tracker":
                rows = parse_tracker_md(Path(cwd) / "docs" / ".tasks" / "TRACKER.md")
                self._send(200, "application/json", json.dumps(rows))
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
