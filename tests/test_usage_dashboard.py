"""
Unit tests for scripts/usage_dashboard.py's aggregation logic.

Unlike tests/test_intent_routing.py, this is a pure function over local
files — no model calls, no `claude` CLI, fully deterministic. Always
green; a failure here is a real regression, not model variance.
"""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "usage_dashboard.py"
spec = importlib.util.spec_from_file_location("usage_dashboard", SCRIPT_PATH)
usage_dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage_dashboard)


def _assistant_line(timestamp, model, **usage_overrides):
    usage = {
        "input_tokens": 10,
        "output_tokens": 20,
        "cache_creation_input_tokens": 5,
        "cache_read_input_tokens": 100,
    }
    usage.update(usage_overrides)
    return json.dumps({
        "type": "assistant",
        "timestamp": timestamp,
        "message": {"model": model, "usage": usage},
    })


def _write_session(transcripts_dir, session_id, lines):
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    (transcripts_dir / f"{session_id}.jsonl").write_text("\n".join(lines) + "\n")


def test_encode_project_dir_replaces_slashes():
    assert usage_dashboard.encode_project_dir("/Users/me/cairn") == "-Users-me-cairn"


def test_aggregate_usage_sums_tokens_and_joins_version(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    _write_session(transcripts_dir, "session-a", [
        json.dumps({"type": "mode", "sessionId": "session-a"}),  # non-assistant, should be skipped
        _assistant_line("2026-08-14T01:00:00Z", "claude-sonnet-5", input_tokens=10, output_tokens=20),
        _assistant_line("2026-08-14T01:01:00Z", "claude-sonnet-5", input_tokens=5, output_tokens=15),
    ])

    cairn_dir = cwd / ".cairn"
    cairn_dir.mkdir()
    (cairn_dir / "version-log.jsonl").write_text(
        json.dumps({"session_id": "session-a", "timestamp": "2026-08-14T01:00:00Z", "version": "0.1.0"}) + "\n"
    )

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)

    assert result["project"] == str(cwd)
    assert len(result["sessions"]) == 1
    session = result["sessions"][0]
    assert session["session_id"] == "session-a"
    assert session["version"] == "0.1.0"
    assert session["calls"] == 2
    assert session["input_tokens"] == 15
    assert session["output_tokens"] == 35
    assert result["totals"]["input_tokens"] == 15
    assert result["totals"]["calls"] == 2


def test_aggregate_usage_missing_version_log_defaults_unknown(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    _write_session(transcripts_dir, "session-b", [
        _assistant_line("2026-08-14T02:00:00Z", "claude-haiku-4-5"),
    ])
    # no .cairn/version-log.jsonl at all

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)

    assert result["sessions"][0]["version"] == "unknown"


def test_aggregate_usage_no_transcripts_dir_returns_empty(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"  # never created

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)

    assert result["sessions"] == []
    assert result["totals"]["calls"] == 0


def test_session_with_no_assistant_usage_is_excluded(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    _write_session(transcripts_dir, "session-c", [
        json.dumps({"type": "mode", "sessionId": "session-c"}),
        json.dumps({"type": "file-history-snapshot", "sessionId": "session-c"}),
    ])

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)

    assert result["sessions"] == []


def test_sessions_sorted_newest_first(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    _write_session(transcripts_dir, "session-old", [_assistant_line("2026-08-14T01:00:00Z", "claude-sonnet-5")])
    _write_session(transcripts_dir, "session-new", [_assistant_line("2026-08-14T03:00:00Z", "claude-sonnet-5")])

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)

    assert [s["session_id"] for s in result["sessions"]] == ["session-new", "session-old"]
