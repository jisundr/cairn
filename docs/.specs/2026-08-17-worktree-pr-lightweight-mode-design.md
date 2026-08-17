# Design: Lightweight worktree+PR/MR mode for Direct flow, bounded-path, and doc-sync work

## Summary

Extends "always recommend a worktree + PR/MR" beyond `task-orchestrator`'s existing Chain-flow Plan/Publish mechanism to three paths that today never create either: `software-engineer` Direct Mode (bug-fix/decision requests), `superpowers:brainstorming`'s bounded path, and `documentation-engineer` doc-sync work. Motivated by the just-shipped PR/MR usage-token report (`docs/.specs/` PR/MR usage-token design — see the coding-chain sequence in `CLAUDE.md`): that report needs a PR/MR to land in, and none of these three paths ever produce one, so their usage is never recorded anywhere.

`superpowers:brainstorming`'s spike path is explicitly out of scope — a spike's whole point is throwaway, unkept work; forcing a PR on it would contradict the path's own design.

Suggested, never forced — matches cairn's existing "no gates" posture (e.g. `harness-engineer`'s auto-suggestion on missing `.harness/`). Each of the three trigger points asks via `AskUserQuestion` before any file gets touched, since worktree isolation only works if it happens *before* implementation starts, not retrofitted after.

## Scope decision

| Decision | Chosen | Why |
|---|---|---|
| Which paths | Direct flow, bounded path, doc-sync | Spike is explicitly throwaway by design — excluded. |
| Reuse strategy | New `task-orchestrator` **Lightweight mode** (a third `START` branch) | Reuses the exact worktree-creation (Plan Mode Step 5) and PR-creation (Publish Mode Steps 4–6) code paths already proven in Chain flow, rather than duplicating that logic into three other agents or extracting a new shared skill (bigger refactor, touches Plan/Publish too, rejected as more surface than this change needs). |
| Gate strength | Suggested via `AskUserQuestion`, never forced | Matches cairn's stated "no warranty, no gates, use your judgment" posture. A default-on/opt-out design was considered and rejected — it would reverse that posture for the first time, turning every small bug-fix into a branch+worktree+PR by default. |

## Trigger points

The ask happens once, at the start of each path, before any file is touched:

- **Direct flow** — after `intent-analyzer` routes `coding` + `proceed-directly`, before dispatching `software-engineer` Direct Mode. Asked by the main-thread session, per `CLAUDE.md`'s existing "Claude's own documented judgment call" framing for this flow.
- **Bounded path** (`superpowers:brainstorming`) — after the in-chat design is approved, before "Implement — proceed with the normal development workflow." Same main-thread-asks pattern; `superpowers:brainstorming` itself is not modified (out of cairn's own files), the ask lives in the calling session the same way `cairn:spec-writing`'s bypass-capture rule already does.
- **Doc-sync** (`documentation-engineer`) — start of Create/Update mode, before Step 2 (discover existing docs).

If yes: `task-orchestrator` Lightweight Start runs before the doing agent starts; Lightweight Finish runs after it's done.

## `task-orchestrator` Lightweight mode

A third mode alongside Plan/Publish, detected the same way (opening context names it explicitly). Two thin entry points:

**Lightweight Start** — reuses Plan Mode Step 5 (`Skill(skill: "superpowers:using-git-worktrees")`) only. No `docs/.plans/` requirement, no task folder, no `STATE.md`/`HISTORY.md`, no Environment Preflight, no feasibility assessment, no Doc Gate. Branch name `direct/<slug>` / `bounded/<slug>` / `doc/<slug>` (mirrors Chain's `<task-type>/<slug>`) — slug derived ad hoc from the request by the calling session, since there's no plan file to source a canonical one from. Returns a start timestamp and the worktree path as plain text to the caller; nothing is written to any file (there's no task folder to write it into) — the caller holds both until Finish.

**Lightweight Finish** — reuses Publish Mode Step 4 (remote host detection), Step 5 (consolidated commit), Step 6 (PR/MR creation). No `UAT.md`, no ticket sync, no drift-flag question (none of `Harness flags`/`Key info` exist without a `STATE.md`). PR/MR body includes the usage report described below.

Same worktree-creation and PR-creation logic Chain flow already exercises — this is a new `START` branch and two new step-sequences in `task-orchestrator.md`, not new mechanics.

## Changes to the doing agents

- **`software-engineer` Direct Mode** — Step 4 (load context) gains a check: if the opening context names a `Worktree:` path (Lightweight Start already ran), `cd` into it, same as Chain mode's Step 2. Its Direct-mode `PHASE HANDOFF` text becomes conditional: unchanged (current-branch language) when no worktree was created; when one was, states it's working inside `<worktree>` and that Lightweight Finish runs once `qa-engineer`'s post-hoc tests land.
- **`qa-engineer` Direct Mode** — same worktree-awareness (`cd` in if named in context); its terminal handoff triggers Lightweight Finish when a worktree is in play, instead of ending with no commit/PR as today.
- **`documentation-engineer`** — gains the same optional `Worktree:` field in its opening context; Create/Update Step 1 `cd`s into it if present. Its own terminal `COMPLETION` triggers Lightweight Finish directly (doc-sync has no `qa-engineer` step in between).
- **Bounded path** — the ask and the worktree `cd` happen in the main-thread session driving the brainstorming dialogue, since "Implement — proceed with the normal development workflow" is generic instruction there, not a fixed agent dispatch.

None of these agents gain new tools — just an optional `Worktree:` field they read from opening context, the same shape Chain mode already uses via `STATE.md`'s `Worktree` field (here passed directly in context instead, since there's no `STATE.md` to read it from).

## Usage report for Lightweight mode

`scripts/usage_dashboard.py` gains a second CLI mode: `--window-report <start-iso> <end-iso> [cwd]`. Reuses `usage_by_windows()` (added for the PR/MR usage-token feature) with a single window labeled `Work`; same markdown-table formatting minus the phase breakdown — one row plus `Total`, same unpriced-model note and "approximate" caveat. Lightweight Finish calls this instead of `--task-report`, passing the timestamp Lightweight Start returned and now.

## Error handling

- Declining the ask at any trigger point is exactly today's existing behavior — pure opt-in addition, no new failure mode.
- `tmux`/`gh`/`glab` failures during Lightweight Start/Finish get the same `TERMINATED`-style handling `task-orchestrator` already has for Chain flow (its existing EXIT & DERAILMENT table) — no new error paths.
- If Lightweight Start ran but the doing agent never reaches Finish (e.g. a Direct-mode fix turns out to need the full Chain flow instead — `software-engineer`'s existing EXIT row already anticipates this), the worktree is left as-is, uncommitted. No auto-cleanup — matches cairn's existing "never delete things automatically" posture (e.g. `docs/.plans/` only deleted on observed ticket closure). Whoever's driving the session decides whether to abandon it or hand it to `task-orchestrator` Plan Mode properly.

## Testing

`--window-report` gets the same `tests/test_usage_dashboard.py` pure-function coverage as `--task-report` — single-window slicing is a strict subset of `usage_by_windows()`, already exercised by that suite. The agent-file changes themselves aren't unit-testable; verified the way every other cairn agent change is, per `CLAUDE.md`'s Testing section: run each affected path headless against a scratch directory (`claude -p ... --plugin-dir ...`), confirming the ask fires, a decline behaves exactly as today, and an accept produces a real worktree + PR/MR with a usage line in the body.

## Versioning

Behavior change to `task-orchestrator`, `software-engineer`, `qa-engineer`, `documentation-engineer`, and `scripts/usage_dashboard.py`, plus the Direct-flow/bounded-path documentation in `CLAUDE.md`'s coding-chain sequence — bump `.claude-plugin/plugin.json` per `CLAUDE.md`'s Versioning section (minor, new feature) once implemented.
