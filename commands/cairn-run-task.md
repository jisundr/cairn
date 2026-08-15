---
description: Create or resume a coding-chain task and run it (Chain flow only).
argument-hint: <slug-or-path-or-ticket> [--unattended]
---

# /cairn-run-task

Creates or resumes `docs/.tasks/YYYY-MM-DD-<feature-slug>/` and runs the Chain flow from wherever its `STATE.md` left off.

## Input resolution

Accept `$ARGUMENTS` as one of:
- A bare slug (e.g. `user-login`) — `Glob` `docs/.tasks/*-<slug>/` for an existing task folder, or `docs/.tasks/TRACKER.md` for a matching row if no task folder exists yet.
- A pasted path (to the task folder, any file inside it, or a `docs/.plans/*.md` file) — resolve to the containing task folder / matching slug.
- A ticket URL/ID — resolve via `docs/.tasks/TRACKER.md`'s Ticket column (requires ticket sync to be active for that row).

Direct flow never creates a task folder — this command has nothing to resume for a small bug-fix; those stay natural-language-only through `intent-analyzer`'s normal routing.

## Attended vs. unattended

If `--unattended` is present in `$ARGUMENTS`: force unattended (tmux-detached) mode.

If absent: check whether the resolved task's `STATE.md` already records a `Mode:` from a prior run — if so, use it. Otherwise, ask via `AskUserQuestion`: "Run this task attended (current session) or unattended (tmux-detached, for long-running work)?" — never silently default either way.

## Invocation

Once resolved (task folder identified or about to be created) and mode determined, invoke `task-orchestrator` Plan Mode with the resolved slug and mode. `task-orchestrator` takes it from there per its own Plan Mode process.
