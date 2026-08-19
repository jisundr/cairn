# UAT Checklist: coding-chain-multi-repo-safety

Manual verification for the three related fixes in this task. Task 1 (the hook) has automated smoke coverage (`tests/smoke/test_goal_guard.sh`, 6/6 passing) — the items below are what that suite can't reach, per the plan's own Testing strategy (LLM-instruction changes, verified by inspection + a live dry run, not pytest).

## Task 1 — `/goal` misuse guard hook

- [ ] In a real session (not the smoke fixture), run `/goal docs/.plans/<some-slug>.md` against a plan with no sibling goal file — confirm the `additionalContext` warning appears and correctly says no goal file exists yet, suggesting `/cairn-run-task <slug>`.
- [ ] Run `/goal docs/.plans/<some-slug>-goal.md` against a real goal file — confirm no warning appears.
- [ ] Confirm a machine without `jq` on `PATH` sees no warning and no session breakage (hook exits 0 silently).

## Task 2 — `task-orchestrator` Plan Mode submodule detection/init

- [ ] Run `task-orchestrator` Plan Mode against a plan whose paths are **entirely** inside one submodule — confirm `Worktree` is scoped to the submodule (unchanged prior behavior) and `STATE.md`'s new `Submodule`/`Submodule branch` fields both read `none`.
- [ ] Run `task-orchestrator` Plan Mode against a **mixed** plan (touches both parent-repo paths and one submodule's paths — e.g. the real `2026-08-19-cairn-dashboard-react-redesign.md` plan this fix was written for) — confirm: worktree stays parent-scoped, `STATE.md`'s `Submodule`/`Submodule branch` are populated with the real submodule path/branch (never a hardcoded name), and the submodule directory is populated (not empty) inside the new worktree via `git submodule update --init`.
- [ ] Run against a plan touching two distinct submodules — confirm it falls back to `Submodule: none` with a `[warning]` noted in `Key info`, rather than guessing.

## Task 3 — `task-orchestrator` Publish Mode per-repo sequence

- [ ] Complete the mixed-scope dry run above through to Publish Mode — confirm the submodule gets its own commit + push + PR **before** the parent's commit, and the parent's commit captures the submodule's new pushed SHA (`git log -p` on the parent commit shows the submodule pointer bump to that exact SHA, not an earlier one).
- [ ] Confirm the parent PR body includes a `Submodule PR: <url>` line pointing at the real submodule PR.
- [ ] Confirm `project-manager` Status Sync → In Review fires only once, after both PRs exist — not twice, and not after the submodule PR alone.
- [ ] Confirm `STATE.md`'s final `Key info` records both PR URLs in the `PR (<submodule-name>): <url> · PR (parent): <url>` format, using the submodule's real directory name.
- [ ] Confirm the single-repo path (this very task's own publish) is unaffected: one commit, one PR, `Submodule: none` throughout.

## Task 4 — `plan-writing` complexity-routing

- [ ] Run `plan-writing` against a fixture plan with a `Modify:` entry that changes existing behavior — confirm the new Step 0 `AskUserQuestion` fires, citing the specific task/file that drove the recommendation, before any `/goal`-file offer is made.
- [ ] Choose "Route through Chain flow" at that prompt — confirm it hands off to `task-orchestrator` Plan Mode with the plan's slug, and the `/goal`-file offer step never runs.
- [ ] Run `plan-writing` against a purely additive plan (all `Create:`, or append-only `Modify:`) — confirm no question is asked and it proceeds straight to the existing `/goal`-file offer, unchanged.

## Documentation drift (deferred, tracked on `STATE.md`'s Harness flags — see Publish Mode's consolidated drift question)

- [ ] `.harness/architecture.md`'s Layering section still describes `hooks/` as "SessionStart hooks" only — needs a `harness-engineer` Update Mode pass to note the new `UserPromptSubmit` hook.
- [ ] `.harness/standards.md`'s `## Testing` section's `tests/smoke/*.sh` prerequisite claim needs splitting by script kind — `test_goal_guard.sh` needs `jq`, not `claude`/`tmux`.
