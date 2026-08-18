---
description: Create or resume a coding-chain task and run it (Chain flow only), or with no target, run a backoff-paced monitoring check of every active Unattended task.
argument-hint: [slug-or-path-or-ticket] [--unattended]
---

# /cairn-run-task

Creates or resumes `docs/.tasks/YYYY-MM-DD-<feature-slug>/` and runs the Chain flow from wherever its `STATE.md` left off, given a target. With no target, runs a backoff-paced monitoring check of every active Unattended task instead (see Resuming and monitoring).

## Input resolution

Accept `$ARGUMENTS` as one of:
- Empty `$ARGUMENTS` — no target given at all. Run **Backoff loop mode** (below, under `## Resuming and monitoring`) and stop here — do not fall through to slug/path/ticket resolution, do not ask an `AskUserQuestion` about Attended-vs-unattended, and do not dispatch `task-orchestrator` Plan Mode. This is the one case Input resolution doesn't resolve to a single task.
- A bare slug (e.g. `user-login`) — `Glob` `docs/.tasks/*-<slug>/` for an existing task folder, or `docs/.tasks/TRACKER.md` for a matching row if no task folder exists yet.
- A pasted path (to the task folder, any file inside it, or a `docs/.plans/*.md` file) — resolve to the containing task folder / matching slug.
- A ticket URL/ID — resolve via `docs/.tasks/TRACKER.md`'s Ticket column (requires ticket sync to be active for that row).

Direct flow never creates a task folder — this command has nothing to resume for a small bug-fix; those stay natural-language-only through `intent-analyzer`'s normal routing.

## Attended vs. unattended

(This section applies once a single target has been resolved — see Input resolution's empty-`$ARGUMENTS` case above, which never reaches here.)

If `--unattended` is present in `$ARGUMENTS`: force unattended (tmux-detached) mode.

If absent: check whether the resolved task's `STATE.md` already records a `Mode:` from a prior run — if so, use it. Otherwise, ask via `AskUserQuestion`: "Run this task attended (current session) or unattended (tmux-detached, for long-running work)?" — never silently default either way.

## Invocation

(This section applies once a single target has been resolved — see Input resolution's empty-`$ARGUMENTS` case above, which never reaches here.)

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

**Backoff loop mode.** `/cairn-run-task` invoked with no target (e.g. under the built-in `/loop` skill, `/loop /cairn-run-task`) checks every active Unattended task in one pass instead of a single named target — this is the mode Input resolution's empty-`$ARGUMENTS` bullet routes to. **This entire mode never runs a state-changing tmux command**: discovery (item 1), fingerprinting (item 2), and comparison (items 3/5) never touch tmux at all; item 3's bounded `tmux capture-pane` (a read-only tail, same as Monitor's own rule) is the only tmux command messaging ever runs, including on a first-sighting/baseline tick. The one and only tmux-*mutating* action reachable from this mode is the single `tmux kill-session` call inside Stale detection's `STALLED` branch below, and it fires only after item 4's own condition (30-min-cap interval, 3 consecutive unchanged ticks, `Phase` not `PUBLISH`/`HANDOFF NEEDED`) is fully met for that specific task — never as a side effect of any other step, and never on a baseline/first-sighting tick, which by definition hasn't accumulated any unchanged ticks yet.

1. `Glob docs/.tasks/*/STATE.md`, filter to `Mode: Unattended`, and exclude any task whose `Status` field already starts with `STALLED (<timestamp>)` (see Stale detection below — this marker is what makes exclusion durable across `/loop` restarts, not this loop's own transient memory; `Status` is used rather than `Harness flags` because `Harness flags` is read by `task-orchestrator` Publish Mode for its harness/doc-drift question and a monitoring marker there would be misread as one — any chain agent's normal `Status` write on resume overwrites and clears a stale marker as a side effect of its own phase-completion bookkeeping, so no separate manual-clear step exists; a task that stalls again before ever reaching another `Status` write stays excluded until a human edits `Status` by hand). A task at `HANDOFF NEEDED` stays in the discovery set (see item 3) — it is not excluded, only its repeat message is suppressed. A task at `Phase: PUBLISH` is excluded *unless* this loop's own running state has not yet recorded seeing it at `PUBLISH` (i.e. the very first tick that observes the transition) — that one tick is kept in so item 5's final message can fire; every tick after, once this loop's transient memory has recorded the `PUBLISH` sighting, it's excluded like any other terminal task. A `/loop` restart cold-starts this memory, so a task that reached `PUBLISH` in a prior loop lifetime and is restarted into doesn't re-fire the final message — an acceptable, low-stakes gap (unlike `STALLED`, nothing destructive happens from missing it).
2. Per task, per tick: read `Phase` + count `HISTORY.md` lines matching the `<ISO-8601 UTC> — <PHASE> — <note>` line format documented in `skills/coding-chain-shared/SKILL.md` (not a raw line count of the whole file, which would also count the heading and blank separator lines), compare against the last-seen fingerprint kept in this loop's own running state (not written to any task file — read-only, same as Monitor above). No prior fingerprint for this task in this loop's running state (first sighting since the loop started, or since a `/loop` restart) → record the current `Phase`/line-count as the baseline, emit no message, start this task's interval at 1 min. This is neither Unchanged nor Changed — it's the one-time baseline case both of those branches assume already happened.
3. Unchanged → double that task's own backoff interval (start 1 min, cap 30 min); no message — except a task sitting at `HANDOFF NEEDED` whose fingerprint is genuinely unchanged still gets checked at its current interval (up to the 30-min cap) rather than being dropped, so a later phase advance past `HANDOFF NEEDED` is still observed; suppress only a repeat of the *same* pending-question message, not the check itself, and never apply item 4's `STALLED` rule to a `HANDOFF NEEDED` task regardless of tick count — a task correctly waiting on a human answer is never `STALLED`. Changed → reset that task's interval to 1 min, message the user with the new `Phase`/latest `HISTORY.md` line (plus the pending question from `Key info` and a bounded `tmux capture-pane`, per Monitor's existing rule, narrowed to first sighting in this loop if the new `Phase` is `HANDOFF NEEDED`).
4. Once a task's own backoff has been at the 30-min cap for 3 consecutive unchanged ticks — **and its `Phase` is not `PUBLISH` or `HANDOFF NEEDED`, per item 3's exception** — declare `STALLED` per Stale detection below (which writes the durable marker item 1 reads) and drop it from this tick's active set.
5. A task reaching `PUBLISH` is treated as Changed on the tick that first observes it there (item 3's Changed branch fires normally, since `Phase` changed) — the message sent is the final one (PR/MR URL) instead of the usual phase-advance note. It stays in the discovery set for that one tick specifically so this message can fire, then item 1 excludes it from every tick after.
6. Return control to `/loop` after each pass — this command never owns the timer itself, the same pattern the built-in `/loop` skill already provides for any recurring check.

Silent on an unchanged tick across the board — the whole point of backing off. See `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md` for the full design.

**Stale detection.** The backoff loop mode above supplies the "repeated checks" this relies on: 3 consecutive unchanged ticks once a task's own backoff interval has reached its 30-min cap (≈90 min of confirmed no-progress at the slowest cadence) triggers `STALLED` — the loop's cheap `Phase` + `HISTORY.md`-line-count fingerprint (backoff loop mode, item 2) is sufficient on its own; a manual single-target check may additionally confirm with `git rev-parse HEAD` + `git status --porcelain` (inside the worktree) before declaring `STALLED` if extra certainty is wanted, but the loop's own repeated-tick trigger doesn't require it. `STALLED` never fires on a task whose `Phase` is `PUBLISH` (already terminal) or `HANDOFF NEEDED` (a clean pause, not a stall) — enforced by the backoff loop's item 3/4 exception on the loop path, and binding equally on a manual single-target check (this rule is unconditional regardless of which path triggered the check). On `STALLED`: prepend `STALLED (<ISO-8601 UTC timestamp>) — ` to `STATE.md`'s `Status` field (the one field with no other programmatic reader, unlike `Harness flags`) and append a `HISTORY.md` line, then stop the detached run with `tmux kill-session -t <branch>`. `STALLED` is distinct from a clean finish and from a clean pause — it is not a `Phase` value (the `Phase` vocabulary in `skills/coding-chain-shared/SKILL.md` is unchanged by this), it's a marker the backoff loop's own discovery filter (item 1 above) reads to exclude an already-stalled task durably across `/loop` restarts.
