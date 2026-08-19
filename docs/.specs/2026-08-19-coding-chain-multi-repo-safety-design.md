# Coding-Chain Multi-Repo Safety — Design Spec

**Date:** 2026-08-19
**Status:** Approved

## Problem

While preparing to run `docs/.plans/2026-08-19-cairn-dashboard-react-redesign.md` — a plan spanning the parent `cairn` repo and its `dashboard/` submodule — through cairn's coding chain, three related gaps surfaced, all variants of the same failure: a plan that spans more than one git repo (or is otherwise non-trivial) can leak into an execution path that has no concept of that, and the resulting PR lands on the wrong repo or the work never gets committed correctly at all.

1. **A prior run bypassed the chain entirely.** The user ran the built-in `/goal` slash command pointed directly at the raw plan file, expecting it to execute/sanitize the plan. `/goal` sets a completion condition from a proper goal file (`docs/.plans/YYYY-MM-DD-<feature-name>-goal.md`, per `plan-writing`'s own optional step) — it isn't an execution entrypoint. Whatever ran underneath had zero submodule awareness and put the PR on the parent repo.

2. **`task-orchestrator`'s own submodule handling can't cover this plan either.** Plan Mode Step 3 only scopes the worktree to a submodule if *every* plan-listed path sits inside it. This plan's Tasks 1–6 are parent-only and Tasks 7–10 touch `dashboard/` *and* bump the parent's submodule pointer in the same task — so the condition never holds, everything defaults to the parent repo, and Chain-mode agents never commit (that's exclusively `task-orchestrator`'s job — see `agents/software-engineer.md:245`) — so the submodule's own work would never even get committed inside its own repo, let alone published.

3. **Nothing steers a complex plan away from `/goal` in the first place.** `plan-writing`'s only post-write step today is an optional `/goal`-file offer, regardless of how complex or existing-behavior-changing the plan is.

## Goals

- A plan touching the parent repo plus exactly one submodule publishes correctly: both repos get their own commit, push, and PR, in the right order.
- A user pointing `/goal` at a raw plan file gets told what `/goal` actually does, instead of silently running it against the wrong thing.
- A freshly written plan that changes existing behavior gets steered toward Chain flow before a `/goal`-file offer is even made.

## Non-goals

- Generic N-submodule support (nested submodules, multiple sibling submodules in one plan). Scope is exactly parent + one submodule — YAGNI; nothing in cairn's own repo layout or any currently known consuming project needs more, and building it now is speculative.
- Hard-blocking `/goal` invocations. Every existing cairn hook (`check-setup.sh`, `log-version.sh`) is non-blocking, best-effort, `exit 0` on any failure — this stays consistent with that; the guard is a warning, not an enforcement mechanism.
- Changing `superpowers:using-git-worktrees` itself. It already has submodule-detection logic for its own Step 0 (distinguishing "in a worktree" from "in a submodule"); the new submodule-*population* step is added by `task-orchestrator` after that skill hands control back, not inside the vendored skill.

## Design

### A. `task-orchestrator` multi-repo Publish support

**Plan Mode Step 3 (Submodule scope detection) — redefined.** Instead of "every listed path sits inside a submodule," check whether *any* plan-listed path falls under a submodule root (`git submodule status` to enumerate roots). If paths fall under more than one distinct submodule, that's outside this design's scope (Non-goals) — fall back to today's behavior (no submodule-specific handling, everything scoped to parent) and note this in `Key info` as a `[warning]`-tier "plan touches multiple submodules, not auto-handled" flag. If paths fall under exactly zero or exactly one submodule, proceed as below.

**New Step 5.5 — Submodule initialization** (runs immediately after Step 5's branch/worktree creation): if Step 3 detected one touched submodule, run `git submodule update --init <submodule-path>` inside the freshly created worktree, then `cd <submodule-path> && git checkout -b <branch-name>` using the same branch name Step 5 chose for the parent. This is required regardless of how "deep" the submodule fix goes — `git worktree add` does not auto-populate submodules, so without this step `dashboard/` is an empty directory inside any new worktree and anything depending on its contents (`npm install`, the plan's own file edits) fails outright. If no submodule was detected, this step is a no-op.

**`STATE.md` gains two fields** (Step 9, Plan Mode): `Submodule: <path> | none`, `Submodule branch: <name> | none`. No other schema change — `Worktree`/`Branch` keep meaning "the parent repo's."

**Publish Mode becomes repo-ordered, not single-shot.** Restructured steps (replacing the old Steps 4–6; Steps 1–3 and 7–9 keep their numbers and mostly keep their content, noted below):

- **Step 4 — Remote host detection**: run once per repo in play (parent, and the submodule if `STATE.md`'s `Submodule` field isn't `none`) — `git remote get-url origin` from inside each, independently mapped to `gh`/`glab`.
- **Step 5 — Submodule publish** (only if `Submodule != none`): from inside the submodule worktree path, stage and commit everything there (plain conventional-commit message — no `.harness/workflow.md` lookup, since `.harness/` conventions belong to the parent repo, not necessarily the submodule), `git push -u origin <submodule-branch>`, create its PR/MR via the CLI detected for it in Step 4, record the URL.
- **Step 6 — Parent publish** (renamed/renumbered from the old Steps 5–6, merged): back in the parent worktree root, stage and commit everything — this now correctly captures the submodule's new pushed commit via `git add <submodule-path>`, since Step 5 already ran. Commit message follows `.harness/workflow.md`'s `## Commits / MR` convention if loaded, else the existing plain default. Push, create the parent PR/MR — body includes the UAT checklist (Step 2) and usage report (Step 2.5) as today, plus, when a submodule PR exists, a line linking it (`Submodule PR: <url>`). Record the URL. If no submodule is in play, this step is exactly today's old Step 5+6 behavior, unchanged.
- **Step 7 — Ticket sync (In Review)**: unchanged trigger condition, except when a submodule is in play it fires only once **both** PRs exist (i.e., after Step 6 completes, not after Step 5 alone).
- **Step 8 — Ticket sync (Done) and plan cleanup**: unchanged, except "PR/MR observed merged/closed" means both PRs when a submodule is in play — plan cleanup (deleting `docs/.plans/<slug>.md`) waits for both.
- **Step 9 — Update `STATE.md`**: `Key info` holds both URLs when applicable — `PR (dashboard): <url> · PR (parent): <url>` — instead of a single URL.

**Plan Mode Step 10 (Ticket sync, In Progress) is unchanged** — already fires at the right moment (right after worktree/branch creation, before Doc Gate) and isn't affected by any of the above.

### B. `/goal` misuse guard hook

New `UserPromptSubmit` hook, `hooks/scripts/goal-guard.sh`, registered in `hooks/hooks.json` alongside the existing `SessionStart` entries — same non-blocking, best-effort philosophy (`set -uo pipefail`, `exit 0` on anything unexpected, never fails the session).

**Detection.** Read stdin JSON's `prompt` field (the raw user prompt, per Claude Code's `UserPromptSubmit` hook contract — same stdin-JSON pattern `log-version.sh` already uses for `session_id`). Match against `^/goal\s+(\S+\.md)\b` — extract the path argument only when the prompt looks like `/goal <something ending in .md>`. Any other `/goal` form (a completion-condition sentence, `/goal` with no args, `/goal clear`) doesn't match — hook exits 0 immediately, silent.

**Check.** If the matched path is under `docs/.plans/` and does **not** end in `-goal.md`, this looks like a raw plan file, not a goal file. Inject `additionalContext` (same `hookSpecificOutput.additionalContext` shape `check-setup.sh` uses) explaining: `/goal` sets a completion condition, it does not execute a plan; point at the sibling `docs/.plans/<same-date-and-slug>-goal.md` if it exists (glob-check before claiming this), and suggest `/cairn-run-task <slug>` as the actual execution entrypoint for a plan. If the path already ends in `-goal.md`, or isn't under `docs/.plans/` at all, no context is injected — this is the expected, correct usage.

### C. `plan-writing` complexity-routing

New step in `skills/plan-writing/SKILL.md`'s Override 2, inserted before the existing offer step (existing Steps 1–8 keep their numbers; this is "Step 0"):

**Step 0 — Complexity check.** Read the plan's `### Task N:` blocks and their **Files** sections (same read `task-orchestrator`/the invoking session already does per CLAUDE.md's existing regression-risk heuristic). If any task's `Modify:` entry changes an existing file's current behavior (not a purely additive/appended change), present via `AskUserQuestion`: *"This plan changes existing behavior — recommend running it through the coding chain (`task-orchestrator`) instead of a `/goal` loop, for independent verification. Route through Chain flow, or continue with `/goal`-file drafting?"* citing which task/file drove the recommendation.

- **Chain flow chosen:** skip the existing `/goal`-offer step (Step 1) entirely — a `/goal` file has no role once Chain flow is running its own Attended/Unattended machinery. Hand off to `task-orchestrator` Plan Mode with the plan's slug.
- **Continue with `/goal` chosen, or the plan is purely additive (no `Modify:` trips the heuristic):** proceed to the existing Step 1 offer, unchanged.

This moves the heuristic from being CLAUDE.md prose the invoking session has to remember and apply manually, into a step the skill runs every time it's invoked — it can no longer be silently skipped by whichever session happens to write the plan. `CLAUDE.md`'s Chain-flow-sequence section gets a one-line edit: the existing heuristic paragraph is replaced with a pointer to `plan-writing`'s Step 0, so there's exactly one copy of this logic, not two that can drift.

## Testing strategy

Per cairn's existing convention (`tests/smoke/*.sh` asserts on observable artifacts, never parsed LLM prose — `release-manager`'s smoke suite is the precedent, covering only its non-interactive Detect→Propose path and leaving anything behind an `AskUserQuestion` confirmation to code inspection):

- **`goal-guard.sh` (Section B)** is pure deterministic shell logic — fully covered by a new `tests/smoke/goal_guard.sh`: feed fixture stdin JSON (`prompt` values covering a raw-plan path, a proper `-goal.md` path, a non-`.md` argument, no argument) and assert exact stdout/exit-code per case. Real pass/fail, no LLM involved.
- **`task-orchestrator` submodule steps (Section A)** are LLM-instruction-following, not deterministic code, and require an actual worktree/submodule to exist — not smoke-testable as unit-level shell assertions. Verified by code inspection (matching how `release-manager`'s Execute-step mechanics are covered) plus a manual dry run: run the fixed `task-orchestrator` against the actual dashboard plan once implemented, and confirm via observable artifacts — `STATE.md`'s `Submodule`/`Submodule branch` fields, two PR URLs recorded in `Key info`, `git log` in both repos — not by reading the agent's own prose output.
- **`plan-writing` Step 0 (Section C)** — same treatment: a manual walkthrough against a fixture plan with a known `Modify:`-existing-behavior entry, asserting the `AskUserQuestion` fires and the correct hand-off follows, verified by code inspection of the instructions plus one live run, not automated pytest coverage.

## Open questions

None — all decisions above were resolved during brainstorming (see below).

## Decisions made during brainstorming (for traceability)

- Scope is parent + exactly one submodule, not generic N-submodule support (YAGNI).
- No second `git worktree add` for the submodule — `git submodule update --init` inside the existing parent worktree is sufficient and simpler, since a submodule is already its own independent repo once initialized.
- Submodule publish happens before parent publish, so the parent's pointer-bump commit captures the submodule's already-pushed SHA, and the parent PR can link the submodule PR.
- The `/goal` guard is a soft warning (`additionalContext` injection), never a hard block — matches every existing cairn hook's non-blocking philosophy.
- `plan-writing`'s new Step 0 fully replaces the CLAUDE.md-prose version of the regression-risk heuristic for the plan-writing entry point specifically; CLAUDE.md is updated to point here instead of restating it.
- `project-manager` Status Sync timing (Publish Mode Steps 7–8) now waits for both PRs when a submodule is in play, rather than firing on the first one.
- Plan Mode Step 10 (ticket sync at "In Progress") already covers the "task is now in progress" moment correctly and needs no change.
