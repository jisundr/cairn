"""
Unit tests for scripts/usage_dashboard.py's aggregation logic.

Unlike tests/test_intent_routing.py, this is a pure function over local
files — no model calls, no `claude` CLI, fully deterministic. Always
green; a failure here is a real regression, not model variance.
"""

import http.client
import importlib.util
import json
import threading
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


def test_encode_project_dir_replaces_all_non_alphanumeric_chars():
    assert usage_dashboard.encode_project_dir("/Users/jay.son/my_repo") == "-Users-jay-son-my-repo"


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


def test_calc_cost_known_model():
    usage = {
        "input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    rate = usage_dashboard.MODEL_PRICING["claude-sonnet-5"]
    expected = rate["input"] + rate["output"]
    assert usage_dashboard.calc_cost("claude-sonnet-5", usage) == pytest.approx(expected)


def test_calc_cost_includes_cache_rates():
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 1_000_000,
        "cache_read_input_tokens": 1_000_000,
    }
    rate = usage_dashboard.MODEL_PRICING["claude-sonnet-5"]
    expected = rate["cache_write"] + rate["cache_read"]
    assert usage_dashboard.calc_cost("claude-sonnet-5", usage) == pytest.approx(expected)


def test_calc_cost_unknown_model_returns_none():
    usage = {"input_tokens": 100, "output_tokens": 100, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    assert usage_dashboard.calc_cost("some-unreleased-model", usage) is None


def test_aggregate_usage_computes_session_cost_and_flags_unpriced(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    _write_session(transcripts_dir, "session-priced", [
        _assistant_line("2026-08-14T01:00:00Z", "claude-sonnet-5", input_tokens=1_000_000, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
    ])
    _write_session(transcripts_dir, "session-unpriced", [
        _assistant_line("2026-08-14T02:00:00Z", "some-unreleased-model"),
    ])

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)
    by_id = {s["session_id"]: s for s in result["sessions"]}

    rate = usage_dashboard.MODEL_PRICING["claude-sonnet-5"]
    assert by_id["session-priced"]["cost"] == pytest.approx(rate["input"])
    assert by_id["session-priced"]["unpriced_calls"] == 0

    assert by_id["session-unpriced"]["cost"] == 0
    assert by_id["session-unpriced"]["unpriced_calls"] == 1

    assert result["totals"]["cost"] == pytest.approx(rate["input"])
    assert result["totals"]["unpriced_calls"] == 1


def test_aggregate_by_model(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    _write_session(transcripts_dir, "session-a", [
        _assistant_line("2026-08-14T01:00:00Z", "claude-sonnet-5", input_tokens=10, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
    ])
    _write_session(transcripts_dir, "session-b", [
        _assistant_line("2026-08-14T02:00:00Z", "claude-haiku-4-5", input_tokens=20, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
        _assistant_line("2026-08-14T02:01:00Z", "claude-sonnet-5", input_tokens=5, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
    ])

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)
    by_model = {row["model"]: row for row in result["by_model"]}

    assert by_model["claude-sonnet-5"]["input_tokens"] == 15
    assert by_model["claude-sonnet-5"]["calls"] == 2
    assert by_model["claude-haiku-4-5"]["input_tokens"] == 20
    assert by_model["claude-haiku-4-5"]["calls"] == 1


def test_aggregate_by_version(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    _write_session(transcripts_dir, "session-a", [_assistant_line("2026-08-14T01:00:00Z", "claude-sonnet-5")])
    _write_session(transcripts_dir, "session-b", [_assistant_line("2026-08-14T02:00:00Z", "claude-sonnet-5")])

    cairn_dir = cwd / ".cairn"
    cairn_dir.mkdir()
    (cairn_dir / "version-log.jsonl").write_text(
        "\n".join([
            json.dumps({"session_id": "session-a", "timestamp": "2026-08-14T01:00:00Z", "version": "0.9.0"}),
            json.dumps({"session_id": "session-b", "timestamp": "2026-08-14T02:00:00Z", "version": "0.10.0"}),
        ]) + "\n"
    )

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)
    by_version = {row["version"]: row for row in result["by_version"]}

    assert by_version["0.9.0"]["calls"] == 1
    assert by_version["0.10.0"]["calls"] == 1


def test_subagent_and_skill_calls_counted(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    line = json.dumps({
        "type": "assistant",
        "timestamp": "2026-08-14T01:00:00Z",
        "message": {
            "model": "claude-sonnet-5",
            "usage": {"input_tokens": 1, "output_tokens": 1, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
            "content": [
                {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "cairn:intent-analyzer"}},
                {"type": "tool_use", "name": "Skill", "input": {"skill": "cairn:spec-writing"}},
                {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "cairn:intent-analyzer"}},
            ],
        },
    })
    _write_session(transcripts_dir, "session-a", [line])

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)
    by_subagent = {row["name"]: row["calls"] for row in result["by_subagent"]}
    by_skill = {row["name"]: row["calls"] for row in result["by_skill"]}

    assert by_subagent["cairn:intent-analyzer"] == 2
    assert by_skill["cairn:spec-writing"] == 1


def test_session_carries_model_costs_subagents_and_skills(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    line = json.dumps({
        "type": "assistant",
        "timestamp": "2026-08-14T01:00:00Z",
        "message": {
            "model": "claude-sonnet-5",
            "usage": {"input_tokens": 1, "output_tokens": 1, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
            "content": [
                {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "cairn:intent-analyzer"}},
                {"type": "tool_use", "name": "Skill", "input": {"skill": "cairn:spec-writing"}},
            ],
        },
    })
    _write_session(transcripts_dir, "session-a", [line])

    result = usage_dashboard.aggregate_usage(str(cwd), projects_root)
    session = result["sessions"][0]

    assert "claude-sonnet-5" in session["model_costs"]
    assert session["subagents"] == {"cairn:intent-analyzer": 1}
    assert session["skills"] == {"cairn:spec-writing": 1}
    # all-time aggregates still populate the same as before this fix
    assert result["by_subagent"][0]["name"] == "cairn:intent-analyzer"


def test_parse_tracker_md_parses_rows_with_milestone(tmp_path):
    tracker = tmp_path / "TRACKER.md"
    tracker.write_text(
        "# Task Tracker\n\n"
        "| Slug | Milestone | Scope | Status | Ticket | Task File |\n"
        "|---|---|---|---|---|---|\n"
        "| add-auth | v1 launch | Add login flow | In Progress: QA-RED | #42 | docs/.tasks/2026-08-14-add-auth |\n"
        "| — | — | [one-line scope, from a user story or PRD feature] | Idea | — | — |\n"
    )

    rows = usage_dashboard.parse_tracker_md(tracker)

    assert len(rows) == 1
    assert rows[0] == {
        "slug": "add-auth",
        "milestone": "v1 launch",
        "scope": "Add login flow",
        "status": "In Progress: QA-RED",
        "ticket": "#42",
        "task_file": "docs/.tasks/2026-08-14-add-auth",
    }


def test_parse_tracker_md_legacy_table_without_milestone_column(tmp_path):
    tracker = tmp_path / "TRACKER.md"
    tracker.write_text(
        "# Task Tracker\n\n"
        "| Slug | Scope | Status | Ticket | Task File |\n"
        "|---|---|---|---|---|\n"
        "| add-auth | Add login flow | Idea | — | — |\n"
    )

    rows = usage_dashboard.parse_tracker_md(tracker)

    assert rows[0]["milestone"] == "—"
    assert rows[0]["slug"] == "add-auth"


def test_parse_tracker_md_missing_file_returns_empty(tmp_path):
    assert usage_dashboard.parse_tracker_md(tmp_path / "nope.md") == []


def test_parse_history_md_extracts_timestamped_lines(tmp_path):
    history = tmp_path / "HISTORY.md"
    history.write_text(
        "# History: add-auth\n\n"
        "<!-- Append-only. -->\n"
        "2026-08-17T14:00:00Z — PLAN — plan read, worktree created\n"
        "2026-08-17T14:30:00Z — DOC-GATE — clean, no findings\n"
    )

    entries = usage_dashboard.parse_history_md(history)

    assert entries == [
        {"timestamp": "2026-08-17T14:00:00Z", "phase": "PLAN", "note": "plan read, worktree created"},
        {"timestamp": "2026-08-17T14:30:00Z", "phase": "DOC-GATE", "note": "clean, no findings"},
    ]


def test_parse_history_md_skips_untimestamped_lines(tmp_path):
    history = tmp_path / "HISTORY.md"
    history.write_text(
        "# History: add-auth\n\n"
        "2026-08-17T14:00:00Z — PLAN — plan read\n"
        "some free-text note with no timestamp prefix\n"
        "2026-08-17T14:30:00Z — DOC-GATE — clean\n"
    )

    entries = usage_dashboard.parse_history_md(history)

    assert len(entries) == 2
    assert [e["phase"] for e in entries] == ["PLAN", "DOC-GATE"]


def test_parse_history_md_legacy_file_no_timestamps_returns_empty(tmp_path):
    history = tmp_path / "HISTORY.md"
    history.write_text("# History: add-auth\n\nPLAN complete, worktree created\nDOC-GATE clean\n")

    assert usage_dashboard.parse_history_md(history) == []


def test_parse_history_md_missing_file_returns_empty(tmp_path):
    assert usage_dashboard.parse_history_md(tmp_path / "nope.md") == []


def test_phase_windows_chains_consecutive_entries():
    entries = [
        {"timestamp": "2026-08-17T14:00:00Z", "phase": "PLAN", "note": "x"},
        {"timestamp": "2026-08-17T14:30:00Z", "phase": "DOC-GATE", "note": "y"},
        {"timestamp": "2026-08-17T15:00:00Z", "phase": "QA-RED", "note": "z"},
    ]

    windows = usage_dashboard.phase_windows(entries)

    assert windows[0][0] == "PLAN"
    assert windows[0][2] == "2026-08-17T14:00:00Z"
    assert windows[0][1] == "2026-08-17T13:00:00Z"  # 1h lookback, no prior entry
    assert windows[1] == ("DOC-GATE", "2026-08-17T14:00:00Z", "2026-08-17T14:30:00Z")
    assert windows[2] == ("QA-RED", "2026-08-17T14:30:00Z", "2026-08-17T15:00:00Z")


def test_phase_windows_empty_entries_returns_empty():
    assert usage_dashboard.phase_windows([]) == []


def test_usage_by_windows_buckets_turns_by_timestamp(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))

    _write_session(transcripts_dir, "session-a", [
        _assistant_line("2026-08-17T13:30:00Z", "claude-sonnet-5", input_tokens=1_000_000, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
        _assistant_line("2026-08-17T14:15:00Z", "claude-sonnet-5", input_tokens=2_000_000, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
    ])

    windows = [
        ("PLAN", "2026-08-17T13:00:00Z", "2026-08-17T14:00:00Z"),
        ("DOC-GATE", "2026-08-17T14:00:00Z", "2026-08-17T14:30:00Z"),
    ]

    stats = usage_dashboard.usage_by_windows(str(cwd), projects_root, windows)

    rate = usage_dashboard.MODEL_PRICING["claude-sonnet-5"]
    assert stats["PLAN"]["calls"] == 1
    assert stats["PLAN"]["cost"] == pytest.approx(rate["input"])
    assert stats["DOC-GATE"]["calls"] == 1
    assert stats["DOC-GATE"]["cost"] == pytest.approx(rate["input"] * 2)


def test_usage_by_windows_no_transcripts_dir_returns_zeroed_buckets(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"

    windows = [("PLAN", "2026-08-17T13:00:00Z", "2026-08-17T14:00:00Z")]
    stats = usage_dashboard.usage_by_windows(str(cwd), projects_root, windows)

    assert stats["PLAN"]["calls"] == 0
    assert stats["PLAN"]["cost"] == 0


def test_build_task_report_no_task_folder_reports_unavailable(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"

    report = usage_dashboard.build_task_report(str(cwd), projects_root, "add-auth")

    assert "unavailable" in report.lower()


def test_build_task_report_legacy_history_reports_unavailable(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    task_dir = cwd / "docs" / ".tasks" / "2026-08-17-add-auth"
    task_dir.mkdir(parents=True)
    (task_dir / "HISTORY.md").write_text("PLAN complete\n")
    projects_root = tmp_path / "claude_projects"

    report = usage_dashboard.build_task_report(str(cwd), projects_root, "add-auth")

    assert "unavailable" in report.lower()
    assert "predates timestamp tracking" in report.lower()


def test_build_task_report_renders_markdown_table(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    task_dir = cwd / "docs" / ".tasks" / "2026-08-17-add-auth"
    task_dir.mkdir(parents=True)
    (task_dir / "HISTORY.md").write_text(
        "2026-08-17T14:00:00Z — PLAN — plan read\n"
        "2026-08-17T14:30:00Z — DOC-GATE — clean\n"
    )
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))
    _write_session(transcripts_dir, "session-a", [
        _assistant_line("2026-08-17T14:10:00Z", "claude-sonnet-5", input_tokens=1_000_000, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
    ])

    report = usage_dashboard.build_task_report(str(cwd), projects_root, "add-auth")

    assert "PLAN" in report
    assert "DOC-GATE" in report
    assert "Total" in report
    assert "approximate" in report.lower()


def test_build_window_report_renders_single_row(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))
    _write_session(transcripts_dir, "session-a", [
        _assistant_line("2026-08-17T14:10:00Z", "claude-sonnet-5", input_tokens=1_000_000, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
        _assistant_line("2026-08-17T15:30:00Z", "claude-sonnet-5", input_tokens=5_000_000, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),  # outside window
    ])

    report = usage_dashboard.build_window_report(str(cwd), projects_root, "2026-08-17T14:00:00Z", "2026-08-17T15:00:00Z")

    assert "Work" in report
    assert "Total" in report
    assert "approximate" not in report.lower()  # single explicit window, not the phase-table's backdated-PLAN caveat
    assert "1,000,000" in report  # in-window turn's tokens only
    assert "6,000,000" not in report  # would only appear if the out-of-window turn were also included


def test_build_window_report_no_transcripts_reports_unavailable(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"

    report = usage_dashboard.build_window_report(str(cwd), projects_root, "2026-08-17T14:00:00Z", "2026-08-17T15:00:00Z")

    assert report == "Usage: unavailable (no transcripts found for this project/window)"


def test_parse_state_md_parses_key_value_lines(tmp_path):
    state = tmp_path / "STATE.md"
    state.write_text(
        "# Task: my-slug\n"
        "\n"
        "Mode: Unattended\n"
        "Phase: HANDOFF NEEDED\n"
        "Handoff to: qa-engineer\n"
        "Status: waiting on a decision\n"
        "Plan: docs/.plans/my-slug.md\n"
        "Ticket: none\n"
        "Worktree: /tmp/worktree\n"
        "Branch: feature/my-slug\n"
        "Key info: needs a human answer\n"
        "Harness flags: none\n"
    )
    result = usage_dashboard.parse_state_md(state)
    assert result["mode"] == "Unattended"
    assert result["phase"] == "HANDOFF NEEDED"
    assert result["handoff_to"] == "qa-engineer"
    assert result["worktree"] == "/tmp/worktree"
    assert result["branch"] == "feature/my-slug"


def test_parse_state_md_missing_file_returns_empty(tmp_path):
    assert usage_dashboard.parse_state_md(tmp_path / "nope.md") == {}


def test_parse_state_md_ignores_non_key_value_lines(tmp_path):
    state = tmp_path / "STATE.md"
    state.write_text("# Task: my-slug\n\nMode: Attended\n\nJust some prose, no colon here really\n")
    result = usage_dashboard.parse_state_md(state)
    assert result == {"mode": "Attended"}


def test_discover_swarms_finds_unattended_tasks_only(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_dashboard, "_tmux_has_session", lambda branch: True)
    cwd = tmp_path / "myproject"
    unattended = cwd / "docs" / ".tasks" / "2026-08-19-my-slug"
    unattended.mkdir(parents=True)
    (unattended / "STATE.md").write_text(
        "Mode: Unattended\nPhase: IMPLEMENT\nStatus: working\nHandoff to: software-engineer\n"
        "Worktree: /tmp/wt\nBranch: feature/my-slug\nKey info: none\n"
    )
    (unattended / "HISTORY.md").write_text(
        "2026-08-19T10:00:00Z — PLAN — plan read\n2026-08-19T10:05:00Z — IMPLEMENT — coding\n"
    )
    attended = cwd / "docs" / ".tasks" / "2026-08-19-other-slug"
    attended.mkdir(parents=True)
    (attended / "STATE.md").write_text("Mode: Attended\nPhase: IMPLEMENT\nStatus: working\n")

    swarms = usage_dashboard.discover_swarms(str(cwd))

    assert len(swarms) == 1
    swarm = swarms[0]
    assert swarm["slug"] == "2026-08-19-my-slug"
    assert swarm["phase"] == "IMPLEMENT"
    assert swarm["branch"] == "feature/my-slug"
    assert swarm["history_count"] == 2
    assert swarm["last_history"]["phase"] == "IMPLEMENT"
    assert swarm["tmux_alive"] is True
    assert [h["phase"] for h in swarm["recent_history"]] == ["IMPLEMENT", "PLAN"]


def test_discover_swarms_recent_history_caps_at_5_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_dashboard, "_tmux_has_session", lambda branch: True)
    cwd = tmp_path / "myproject"
    task = cwd / "docs" / ".tasks" / "2026-08-19-my-slug"
    task.mkdir(parents=True)
    (task / "STATE.md").write_text("Mode: Unattended\nPhase: PUBLISH\nBranch: feature/x\n")
    lines = [
        f"2026-08-19T{10 + i:02d}:00:00Z — PHASE{i} — note {i}" for i in range(7)
    ]
    (task / "HISTORY.md").write_text("\n".join(lines) + "\n")

    swarms = usage_dashboard.discover_swarms(str(cwd))
    recent = swarms[0]["recent_history"]
    assert len(recent) == 5
    assert recent[0]["phase"] == "PHASE6"
    assert recent[-1]["phase"] == "PHASE2"


def test_discover_swarms_no_tasks_dir_returns_empty(tmp_path):
    assert usage_dashboard.discover_swarms(str(tmp_path / "myproject")) == []


def test_discover_swarms_tmux_missing_binary_sets_none(tmp_path, monkeypatch):
    def raise_missing(branch):
        raise FileNotFoundError("tmux not found")
    monkeypatch.setattr(usage_dashboard, "_tmux_has_session", lambda branch: None)
    cwd = tmp_path / "myproject"
    task = cwd / "docs" / ".tasks" / "2026-08-19-my-slug"
    task.mkdir(parents=True)
    (task / "STATE.md").write_text("Mode: Unattended\nPhase: PLAN\nBranch: feature/x\n")

    swarms = usage_dashboard.discover_swarms(str(cwd))
    assert swarms[0]["tmux_alive"] is None


def test_tmux_pane_tail_returns_last_lines(monkeypatch):
    class FakeResult:
        returncode = 0
        stdout = b"line1\nline2\nline3\n"
    monkeypatch.setattr(usage_dashboard.subprocess, "run", lambda *a, **k: FakeResult())
    tail = usage_dashboard._tmux_pane_tail("feature/x", lines=2)
    assert tail == ["line2", "line3"]


def test_tmux_pane_tail_missing_binary_returns_none(monkeypatch):
    def raise_missing(*a, **k):
        raise FileNotFoundError("no tmux")
    monkeypatch.setattr(usage_dashboard.subprocess, "run", raise_missing)
    assert usage_dashboard._tmux_pane_tail("feature/x") is None


def test_discover_swarms_includes_pane_tail_only_on_handoff_needed(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_dashboard, "_tmux_has_session", lambda branch: True)
    monkeypatch.setattr(usage_dashboard, "_tmux_pane_tail", lambda branch, lines=20: ["paused here"])
    cwd = tmp_path / "myproject"
    task = cwd / "docs" / ".tasks" / "2026-08-19-my-slug"
    task.mkdir(parents=True)
    (task / "STATE.md").write_text("Mode: Unattended\nPhase: HANDOFF NEEDED\nBranch: feature/x\n")

    swarms = usage_dashboard.discover_swarms(str(cwd))
    assert swarms[0]["pane_tail"] == ["paused here"]

    (task / "STATE.md").write_text("Mode: Unattended\nPhase: IMPLEMENT\nBranch: feature/x\n")
    swarms = usage_dashboard.discover_swarms(str(cwd))
    assert swarms[0]["pane_tail"] is None


def test_serve_static_serves_existing_file(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>hi</html>")
    (dist / "app.js").write_text("console.log(1)")

    content_type, body = usage_dashboard.serve_static(dist, "/app.js")
    assert body == b"console.log(1)"
    assert "javascript" in content_type


def test_serve_static_falls_back_to_index_for_unknown_path(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa root</html>")

    content_type, body = usage_dashboard.serve_static(dist, "/some/client/route")
    assert body == b"<html>spa root</html>"
    assert content_type == "text/html"


def test_serve_static_missing_dist_returns_none(tmp_path):
    assert usage_dashboard.serve_static(tmp_path / "dist", "/") is None


def test_serve_static_blocks_path_traversal(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa root</html>")
    secret = tmp_path / "secret.txt"
    secret.write_text("shh")

    content_type, body = usage_dashboard.serve_static(dist, "/../secret.txt")
    assert body == b"<html>spa root</html>"


def test_plugin_root_resolves_to_the_repo_the_script_lives_in():
    # PLUGIN_ROOT must be derived from the script's own file location
    # (scripts/usage_dashboard.py -> repo root), not from any notion of cwd —
    # that's the whole point of issue #14's fix.
    assert usage_dashboard.PLUGIN_ROOT == SCRIPT_PATH.resolve().parent.parent


def test_do_get_serves_static_assets_from_plugin_root_not_cwd(tmp_path, monkeypatch):
    # The consuming project (`cwd`) has its own dashboard-dist with different
    # content. Before issue #14's fix, the server resolved static assets from
    # `Path(cwd) / "dashboard" / "dist"` and would have served this instead.
    # dashboard-dist/ (an ordinary tracked directory, not the dashboard/
    # submodule's dist/ output) is what's actually served now — see the
    # follow-up to PR #15 / issue #14's remaining gap.
    cwd = tmp_path / "consuming_project"
    cwd_dist = cwd / "dashboard-dist"
    cwd_dist.mkdir(parents=True)
    (cwd_dist / "index.html").write_text("<html>wrong: served from cwd</html>")

    # The plugin's own install root has the real build output.
    plugin_root = tmp_path / "plugin_root"
    plugin_dist = plugin_root / "dashboard-dist"
    plugin_dist.mkdir(parents=True)
    (plugin_dist / "index.html").write_text("<html>correct: served from plugin root</html>")

    monkeypatch.setattr(usage_dashboard, "PLUGIN_ROOT", plugin_root)

    projects_root = tmp_path / "claude_projects"
    projects_root.mkdir()
    handler_cls = usage_dashboard.make_handler(str(cwd), projects_root)
    server = usage_dashboard.http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("GET", "/")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert "correct: served from plugin root" in body
    assert "wrong: served from cwd" not in body


def test_do_get_static_500_reports_plugin_root_path_when_dist_missing(tmp_path, monkeypatch):
    # When dashboard-dist/ is missing at PLUGIN_ROOT (shouldn't happen on a
    # normal checkout, since it's ordinary tracked content, not a submodule
    # gitlink), the 500 error must point at the plugin's install location,
    # not at cwd, so the user knows where to actually fix it.
    cwd = tmp_path / "consuming_project"
    cwd.mkdir()

    plugin_root = tmp_path / "plugin_root"
    plugin_root.mkdir()
    monkeypatch.setattr(usage_dashboard, "PLUGIN_ROOT", plugin_root)

    projects_root = tmp_path / "claude_projects"
    projects_root.mkdir()
    handler_cls = usage_dashboard.make_handler(str(cwd), projects_root)
    server = usage_dashboard.http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("GET", "/")
        response = conn.getresponse()
        status = response.status
        body = response.read().decode("utf-8")
        conn.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert status == 500
    assert str(plugin_root / "dashboard-dist") in body
    assert str(cwd) not in body
