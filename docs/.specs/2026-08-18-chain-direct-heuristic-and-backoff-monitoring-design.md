# Design: Chain-vs-Direct routing heuristic + backoff monitoring loop

## Summary

Two related additions to cairn's coding-chain execution model, both born directly from this session's own experience running three concurrent Unattended chain tasks (`release-manager`, `goal-file-plan-writing`, `pr-reviewer`) against cairn's own repo:

1. **A routing heuristic** for the moment a plan exists and the invoking session must decide whether to run the full Chain flow (`task-orchestrator` Plan Mode → ... → Publish Mode) or Direct flow with worktree isolation (`task-orchestrator` Lightweight mode). Today that decision has no documented basis beyond "brainstorm-first always reaches Chain flow" — there's no judgment call for "this plan is small enough that Chain's full machinery is disproportionate."
2. **A backoff-paced monitoring loop** for `/cairn-run-task`'s existing Monitor entry point, so Unattended runs get checked on a decaying cadence instead of only when a human happens to remember to look. Motivated directly by two failures observed in this session: `release-manager`'s Unattended launch silently stalled on a `bypassPermissions` denial with nothing surfacing that; `pr-reviewer` legitimately paused at a Doc Gate `HANDOFF NEEDED` with no proactive notification either.

Neither addition creates a new agent or command — both are documented judgment calls / process extensions inside `CLAUDE.md` and `commands/cairn-run-task.md`, the same "Claude's own documented judgment call" pattern the existing Direct/Chain routing already uses.

## Scope decision

| Decision | Chosen | Why |
|---|---|---|
| Heuristic decision mode | Heuristic + confirm via `AskUserQuestion`, never silent | Matches cairn's existing pattern everywhere else this kind of fork occurs (Lightweight Start's ask, `harness-engineer`'s suggestion, the worktree+PR ask in `spec-writing`'s bounded-path handoff). |
| Heuristic signal | **Regression risk**: does any task in the plan `Modify:` an *existing* file in a way that changes its current behavior (not just an appended paragraph/bullet)? If yes → recommend Chain. If every task is `Create:` (new files) or purely additive `Modify:` (append-only, no behavior change) → recommend Direct-with-worktree. | User-selected, after two rounds of refinement. Rejected alternatives: raw task count alone (doesn't explain why `goal-file-plan-writing`, only 3 tasks, correctly needed Chain — it modified an existing load-bearing skill file); "touches shared docs like CLAUDE.md/README.md" alone (over-broad — nearly every plan in this repo touches those, would make the heuristic always say Chain). Regression risk is the signal that actually explains all three of today's runs: `goal-file-plan-writing` modified existing `skills/plan-writing/SKILL.md` (regression risk → Chain, correctly); `release-manager`/`pr-reviewer` created new agent files, but were large/complex on their own (5 and 7 tasks) — this design's threshold is risk-based, not count-based, but a large *new* plan can still independently justify Chain on the judgment call's own terms if the implementer/main-thread session considers it warranted; the heuristic's mandatory trigger is regression risk specifically. |
| Heuristic mechanism | A judgment call the main-thread session makes reading the plan's Files blocks — not a mechanical rule (e.g. not "any Modify: line means Chain", since an append-only doc edit is also a `Modify:` line) | Distinguishing "changes existing behavior" from "purely additive" requires reading what the task actually does, the same kind of judgment `qa-auditor` already applies distinguishing a line `git diff` shows as added/modified from a pre-existing one. A rigid grep-based rule would misclassify append-only `Modify:` entries as regression risk. |
| Trigger point | Immediately after `plan-writing` produces `docs/.plans/<slug>.md`, before dispatching either `task-orchestrator` Plan Mode or `software-engineer` Direct Mode + Lightweight Start | The exact fork point CLAUDE.md's Chain-flow-entry documentation already describes ("once `spec-writing` → `plan-writing`'s architectural path has produced `docs/.plans/<slug>.md`") — cheapest point to redirect, no wasted Plan Mode work if Direct turns out right. |
| Backoff change-signal | `STATE.md`'s `Phase` + `HISTORY.md`'s line count | Reuses (a cheaper subset of) the fingerprint `/cairn-run-task`'s existing Stale detection already defines (`git rev-parse HEAD` + `git status --porcelain` + `Phase`) — cheap enough to check every tick without needing a `git` invocation inside the worktree each time. |
| Backoff driver | `/loop` on `/cairn-run-task` with **no target** — a new "check all active Unattended tasks" mode, one loop instance covers every concurrently-running task | User-selected over "one `/loop` per task" — a single running loop scales to N concurrent tasks (this session had 3) without the user needing to track N separate loop instances. |
| Backoff shape | Starts at 1 min, doubles on each unchanged tick (1→2→4→8→16→30), caps at 30 min. Any change (phase advance, new `HISTORY.md` line) resets fully to 1 min. | User-selected. A task that just moved is the one most likely to move again soon, so a full reset (not a partial step-down) is warranted. |
| Notify rule | Silent on an unchanged tick. Messages the user only on: phase advance, `HANDOFF NEEDED` newly reached, `STALLED` newly declared, or `PUBLISH`/terminal reached. | User-selected. Matches "manage correctly without user worried the job was stuck" — per-tick noise would cause exactly the anxiety this is meant to prevent; the user is told the moment there's something to actually decide or notice, and told proactively if something is genuinely wrong (`STALLED`), so silence otherwise reads as "still fine," not "unknown." |
| Stale-detection integration | The backoff loop becomes the mechanism that performs the repeated checks Stale detection's existing "unchanged across repeated checks" language already assumes but never specified a source for | `/cairn-run-task`'s Stale detection was previously only exercised when a human happened to re-invoke `/cairn-run-task` against the same target repeatedly — nothing supplied that repetition systematically. The loop supplies it for free. |
| STALLED threshold | 3 consecutive unchanged ticks *after* a task's own backoff has reached its 30-min cap (≈90 min of confirmed no-progress at the slowest cadence, reached quickly for anything genuinely alive since the ramp itself starts at 1 min) | User-selected, refined from an initial 2-tick proposal to 3. Would have caught `release-manager`'s silent `bypassPermissions` stall from this session within roughly 90 minutes of it actually happening, instead of only being noticed because the session happened to check. |

## Part 1 — Chain-vs-Direct routing heuristic

### Flow

Runs once, at the fork point already documented in `CLAUDE.md`'s Chain-flow-entry section — after `plan-writing`'s architectural path has produced `docs/.plans/<slug>.md`, before dispatching anything else:

1. Read the plan file. For each `### Task N:` block, read its **Files** section.
2. For each `Modify: <path>` entry, judge whether the task's own step descriptions change that file's existing behavior (a new section/paragraph that doesn't alter what already works there is additive; a change to existing logic, an existing agent's process steps, an existing skill's methodology, or similar is regression risk).
3. If any task carries regression risk by that judgment → recommend **Chain**. If every task is `Create:` only or purely additive `Modify:` → recommend **Direct-with-worktree**.
4. Present via one `AskUserQuestion`: the recommendation, plus which task/file drove it (or, for a Direct recommendation, confirmation that nothing modifies existing behavior). Options: accept the recommendation, or override to the other flow.
5. On Chain: proceed to `task-orchestrator` Plan Mode as today, unchanged.
6. On Direct-with-worktree: proceed to the existing Direct flow, with the "run `task-orchestrator` Lightweight Start first?" ask (already documented in CLAUDE.md's Direct-flow section) now defaulting to *yes* in the recommendation's framing — the whole point of choosing this branch is to still get worktree isolation, so the ask is really "confirm Lightweight Start", not "worktree or not".

### Where this is documented

A new step in `CLAUDE.md`'s Chain-flow-entry description (the same paragraph that currently says the Direct/Chain fork is "Claude's own documented judgment call... rather than inside `intent-analyzer`"). No agent file changes. No `intent-analyzer` changes — `intent-analyzer` already only classifies `User Choice: brainstorm-first`, it has never itself decided Chain vs. Direct; this heuristic slots into the existing gap between that classification and the dispatch it currently maps to unconditionally.

## Part 2 — Backoff monitoring loop

### Flow

Extends `commands/cairn-run-task.md`'s existing **Monitor** section (currently: "on a monitoring request against an already-launched unattended run... report phase, branch, worktree, and PR/MR from `STATE.md` + `HISTORY.md` only"). Adds a no-target invocation mode, intended to be run under `/loop` (e.g. `/loop /cairn-run-task`, no slug argument):

1. **Discover active tasks**: `Glob docs/.tasks/*/STATE.md`, filter to `Mode: Unattended` and `Phase` not already `PUBLISH` or a `HANDOFF NEEDED` this loop has already reported once.
2. **Per task, per tick**: read `Phase` + count `HISTORY.md` lines. Compare against the last-seen fingerprint (kept in the loop's own running state, not written to any task file — this is a read-only monitoring pass, consistent with Monitor's existing "never derive state from tmux pane text... don't start a new chain run as a side effect" rule).
3. **Unchanged** → bump that task's own backoff interval (double, cap 30 min); no message.
4. **Changed** → reset that task's interval to 1 min; message the user with the new `Phase`/latest `HISTORY.md` line. If the new `Phase` is `HANDOFF NEEDED`, include the pending question from `Key info` (same content the existing Monitor path already surfaces on a manual check) plus a bounded `tmux capture-pane` if useful, per Monitor's existing rule.
5. **Stale check**: once a task's own backoff has been at the 30-min cap for 3 consecutive unchanged ticks, declare `STALLED` — record it in that task's `STATE.md`/`HISTORY.md`, stop the detached run (`tmux kill-session -t <branch>`), message the user, and drop it from the discovery set (Step 1) on the next tick.
6. **Terminal**: a task reaching `PUBLISH` gets one final message (PR/MR URL) and is dropped from the discovery set.
7. Loop returns control to `/loop` after each pass — this command never owns the timer itself, consistent with the pattern `pr-reviewer`'s Thread Watch mode (design already committed in this repo) already established for the built-in `/loop` skill.

### Where this is documented

Extends `commands/cairn-run-task.md`'s existing "Monitor" and "Stale detection" sections directly — same file, no new command. The per-task backoff state (last-seen fingerprint, current interval, tick count at cap) is transient to the running `/loop` invocation, never persisted to `STATE.md`/`HISTORY.md` itself (those files record *task* state, not monitor state) — a `STALLED` declaration is the one thing this loop writes, and only because Stale detection already specifies that write today.

## Out of scope

- No change to `task-orchestrator`'s own Plan/Publish/Lightweight mode mechanics — this design only decides *which* of those gets dispatched (Part 1) and *how often* an already-running one gets checked (Part 2).
- No new persistent monitor-state file — per-task backoff intervals live only inside the running `/loop` invocation's own memory for that session; restarting `/loop` starts every active task back at a 1-minute interval, which is an acceptable cold-start cost, not a correctness problem.
- No change to `documentation-auditor`'s Doc Gate/Doc Post-Impl behavior — Part 1's regression-risk judgment is a routing decision made before Chain flow even starts, not a substitute for Doc Gate's own findings once Chain flow is running.
