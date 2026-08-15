---
description: Create or resume a coding-chain task and run it (Chain flow only).
argument-hint: <slug-or-path-or-ticket> [--unattended]
---

# /cairn-run-task

Creates or resumes `docs/.tasks/YYYY-MM-DD-<feature-slug>/` and runs the Chain flow from wherever its `STATE.md` left off. Also the entry point for monitoring and stale-detecting an unattended run (see Resuming and monitoring).

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

Once resolved (task folder identified or about to be created) and mode determined, dispatch per **Resuming and monitoring** below. A fresh task, or one whose `STATE.md` reads `Phase: PLAN`, goes to `task-orchestrator` Plan Mode with the resolved slug and mode — that's the common case, and `task-orchestrator` takes it from there per its own Plan Mode process.

## Resuming and monitoring

**Resume.** A task parked mid-chain doesn't restart at Plan Mode — Plan Mode only covers the `PLAN` phase. Once the task folder is resolved, `Read` its `STATE.md` and dispatch to the agent its `Handoff to:` field names, giving that agent the task folder path in the opening context:

| `Phase` | Dispatch to |
|---|---|
| (no task folder yet) or `PLAN` | `task-orchestrator` Plan Mode |
| `DOC-GATE` | `documentation-auditor` (Doc Gate), then resolve findings and advance to `QA-RED` per `task-orchestrator` PLAN MODE Step 11 |
| `QA-RED` | `qa-engineer` (Chain mode) |
| `IMPLEMENT` | `software-engineer` (Chain mode) |
| `QA-AUDIT` | whichever agent `Handoff to:` names — `qa-auditor`, or `qa-engineer`/`software-engineer` on a fix-cycle route-back |
| `DOC-POST-IMPL` | `task-orchestrator` Publish Mode |
| `HANDOFF NEEDED` | nothing automatically — report the pending question from `Key info` and wait for an answer, then re-dispatch per the `Handoff to:` field |
| `PUBLISH` | nothing — terminal; report the PR/MR URL |

Always trust `Handoff to:` over the phase table when the two disagree — it's the field every chain agent writes explicitly.

**Monitor.** On a monitoring request (`/cairn-run-task <target>` against an already-launched unattended run, or an explicit "check on it"), report phase, branch, worktree, and PR/MR from `STATE.md` + `HISTORY.md` **only** — never derive state from tmux pane text. When `Phase: HANDOFF NEEDED`, add a bounded `tmux capture-pane -t <branch> -p | tail -n 20` for extra context on what it's paused on. Don't start a new chain run as a side effect of a monitoring check.

**Stale detection.** Fingerprint each check as `git rev-parse HEAD` + `git status --porcelain` (inside the worktree) + `STATE.md`'s `Phase`. If the fingerprint is unchanged across repeated checks with no phase advancement and no terminal state (`PUBLISH` or `HANDOFF NEEDED`), report `STALLED` — record it in `STATE.md`/`HISTORY.md` and stop the detached run with `tmux kill-session -t <branch>`. `STALLED` is distinct from a clean finish and from a clean pause.
