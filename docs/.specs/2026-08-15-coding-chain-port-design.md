# Design: Port maestro's coding chain into cairn

## Summary

Port six maestro agents into cairn to give it an actual implementation path — today cairn's writer agents (`requirements-engineer`, `product-designer`, `solution-architect`) stop at planning artifacts, and coding work runs through raw `superpowers` skills in the main thread with no dedicated agent roles:

- `project-manager` — decomposes a PRD into a local task list (`docs/.tasks/TRACKER.md`), sitting between requirements and implementation
- `harness-engineer` — generates/updates `.harness/{architecture,standards,workflow}.md` from a codebase's own observed conventions
- `task-orchestrator` — Plan Mode (task file + feasibility assessment + branch) and Publish Mode (commit + PR/MR)
- `qa-engineer` — writes tests, TDD red phase (delegates TDD methodology to `superpowers:test-driven-development`)
- `software-engineer` — implements code, stack-agnostic, TDD green phase
- `qa-auditor` — independent post-implementation review (tests, coverage, code quality, conditional security/perf/dependency checks)

Plus one new command, `/cairn-run-task`, to create or resume a task directly.

All six are new agent files under `agents/`. No existing agent file is modified — not even `intent-analyzer`, which stays category-only (see "Integration with existing cairn routing" below). Only `CLAUDE.md` changes, gaining the new agent roster entries and a documented coding-chain sequence, same pattern as the existing writer-trio "End-to-end sequence."

## Source

- `~/Projects/maestro/.claude/agents/{project-manager,harness-engineer,task-orchestrator,qa-engineer,software-engineer,qa-auditor}.md`
- `~/Projects/maestro/.claude/skills/delivery-tracker/SKILL.md` (TRACKER.md format — local-only subset, see Task Decomposition below)
- `~/Projects/maestro/.claude/skills/harness-rules-guide/SKILL.md`
- `~/Projects/maestro/.claude/skills/coding-chain-guide/SKILL.md` (chain sequencing, fix-cycle routing — infra sections not ported, see below)

## Scope decision

Same principle as the prior writer-trio port: maestro is a fully meshed 19-agent framework; porting any one agent at face value pulls in the agents and infra it references. cairn stays self-contained, no fixed roster.

**What's explicitly NOT ported, and why:**

| maestro infra | Why dropped |
|---|---|
| GitLab/ClickUp sync itself (auth, MCP/CLI calls to an external backend) | Confirmed not needed — task identity and the task list both stay local (see Task Decomposition below); `project-manager` IS ported, but as a local-only decomposition agent, not a tracker-sync agent |
| `delivery-tracker`'s `tracker.html` static kanban viewer | Real, self-contained, zero-dependency — but extra scope beyond what was asked; `docs/.tasks/TRACKER.md` stays a plain Markdown table for now, viewer is a clean future add-on if wanted |
| `.codegraph/` MCP tool (call-site/blast-radius analysis) | Same precedent as `codebase-auditor`'s port — no codegraph dependency in cairn |
| `swarm.sh` (tmux + detached unattended runs, `SWARM_STATE.md`) | No unattended mode in this design — chain runs in the current session like every other cairn agent, worktree isolation comes from `superpowers:using-git-worktrees` instead |
| `.maestro/token-usage.db` MR token-usage section | cairn's usage tracking is the separate `/cairn-usage` dashboard, not per-task |
| Hard 80% coverage gate | Stack-agnostic here means coverage tooling availability varies; best-effort report instead (see Testing section) |
| Per-stack engineer-guide skills (react/fastapi/rust/tauri/etc.) | Stack-agnostic implementation — infer conventions from the repo itself, no maintained per-stack skill library |
| `LEARNINGS:` block → `CLAUDE.md` `## Learnings` merge | Separate feature, no merge mechanic exists in cairn today; replaced by the lighter Task State section (below), scoped to this port |
| ID Input Resolution (bare tracker ID → synthesized task file) | No tracker, nothing to resolve from |

## Agent roster

| Agent | Model | Role | Terminal? |
|---|---|---|---|
| `project-manager` | sonnet | Decomposes `docs/requirements/prd.md` (+ `user-stories.md`) into task stubs, writes `docs/.tasks/TRACKER.md` (local index). Update Mode auto-syncs each row's status from its matching `docs/.tasks/YYYY-MM-DD-<slug>.md` Task State, if one exists | Terminal |
| `harness-engineer` | sonnet | Generate/update `.harness/*.md` from observed conventions (or, on a fresh codebase, from a direct interview — see Fresh Codebase below), `AskUserQuestion` per-rule confirm gate, evidence-based by default, ~40-line cap per file | Terminal |
| `task-orchestrator` | sonnet | Plan Mode: hard-requires `docs/.plans/<feature>.md` to exist (reads it as the plan, does not re-author it — see Plan Dedup below), create/resume `docs/.tasks/YYYY-MM-DD-<feature-slug>.md` as a thin layer over it (feasibility assessment + worktree/branch + Task State only), run qa-engineer+software-engineer feasibility assessment, create branch via `superpowers:using-git-worktrees`. Publish Mode: consolidated commit, PR/MR via `gh`/`glab`, UAT checklist, surfaces consolidated harness-drift flag | Terminal (Publish) |
| `qa-engineer` | sonnet | Writes tests — pre-implementation (TDD red, hard-requires `superpowers:test-driven-development`) in the chain, or post-implementation in Direct Mode | Hands off |
| `software-engineer` | opus | Implements in-scope code, stack-agnostic, makes qa-engineer's tests pass (TDD green) | Hands off |
| `qa-auditor` | sonnet | Independent post-impl re-verification: scoped tests, best-effort coverage report, code quality; conditional security/perf/dependency checks (tag- or software-engineer-flagged, same routing as maestro) | Hands off → task-orchestrator Publish |

## Two flows

**Direct** (bug-fix/decision — matches intent-analyzer's existing Brainstorming-Gate-skip signal): `software-engineer` (Direct Mode, works on current branch, no automated commit/PR) → `qa-engineer` (tests written post-hoc) → done. No task file, no task-orchestrator, no branch automation.

**Chain** (new-feature/refactor — gate fires, planning already happened upstream): `task-orchestrator` (Plan) → `qa-engineer` (red) → `software-engineer` (green) → `qa-auditor` → `task-orchestrator` (Publish).

Fix-cycle routing carries over from maestro unchanged: `qa-auditor` routes test issues back to `qa-engineer`, implementation bugs and HIGH+ security/perf/dependency findings to `software-engineer`.

## Integration with existing cairn routing

**Approach: chain replaces the terminal execution step; `intent-analyzer` itself is untouched — zero changes to `agents/intent-analyzer.md`.** `intent-analyzer` already emits `ROUTING DECISION: coding` plus a `Context` field carrying `User Choice: brainstorm-first | proceed-directly` (from its existing Brainstorming Gate — fires for `new-feature`/`refactor`, skips for `bug-fix`/`decision`). Consistent with cairn's "no fixed roster, category not agent name" design, `intent-analyzer` never names a downstream agent — that judgment call belongs to whoever picks up the `ROUTING DECISION`, i.e. Claude in the main thread, guided by `CLAUDE.md`'s documented sequence (same pattern the writer trio already uses).

What changes is `CLAUDE.md` gaining a new documented sequence for `ROUTING DECISION: coding`:
- `User Choice: proceed-directly` → invoke `software-engineer` Direct Mode → `qa-engineer` (Direct flow)
- `User Choice: brainstorm-first` → after `spec-writing`/`plan-writing` produces a plan → invoke `task-orchestrator` Plan Mode → chain (Chain flow)

Rejected alternative: rebuilding a maestro-style small/direct-vs-large-task-orchestrator split as an independent second classifier inside `intent-analyzer`. Redundant with the gate's existing distinction, risks the two classifiers disagreeing on the same request, and would require `intent-analyzer` to start naming agents — breaking its category-only design.

## `.harness/` presence-gating

Matches maestro's pattern — `Glob`-check before loading, skip silently if `.harness/` doesn't exist, never block:

- `task-orchestrator` → `workflow.md` (branch naming, commit/PR format)
- `software-engineer` → `architecture.md` + `standards.md`
- `qa-engineer` → `standards.md`'s `## Testing` section
- `qa-auditor` → `architecture.md` + `standards.md`, raises a HIGH finding (routed to `software-engineer`) on task-introduced violations only

**Drift flagging:** `software-engineer`, `qa-engineer`, `qa-auditor` may each emit an optional `HARNESS FLAG:` note in their handoff output when they introduce/observe a pattern not covered by any existing `.harness/` rule (distinct from a violation — those go through `qa-auditor`'s HIGH-finding path above). `task-orchestrator` collects these across the chain and surfaces one consolidated `AskUserQuestion` at Publish Mode: run `harness-engineer` Update mode before publishing, or skip and publish as-is. `harness-engineer` still runs its own per-rule confirm gate when invoked — this is only the trigger.

`harness-engineer` is also invocable standalone at any time, and auto-suggested by `task-orchestrator` Plan Mode on first run if `.harness/` is absent entirely.

**Fresh codebase.** `harness-engineer`'s hard rule — never invent a rule with no observed basis — means Generate mode on a genuinely empty/near-empty repo (no source files beyond scaffolding) would otherwise write near-blank files full of `<!-- no convention observed -->` markers. Instead, Generate mode detects this case and switches to a pre-fill-then-interview flow:

1. **Pre-fill from existing planning artifacts.** `Glob`-check for `docs/architecture/architecture-spec.md` (+ `docs/backend/{db-schema,api-spec}.md`, `docs/adr/*.md` if present) — `solution-architect` commonly produces these before any code exists. Pull stack, layering, data-storage, and service-contract decisions already made there straight into `architecture.md` (and relevant `standards.md` sections), tagged **`from-architecture-spec`** citing the source doc.
2. **Interview for the rest.** Whatever isn't covered by those upstream docs (style conventions, test placement, workflow/branch/commit format — things an Architecture Specification doesn't decide) goes through `AskUserQuestion` directly. Written with a **`user-specified`** provenance tag.

Both tags stand in place of the usual evidence count, visibly distinct from observed rules. Once real code accumulates, a later Update mode run diffs observed conventions against the file as normal — pre-filled and user-specified rules stay untouched unless the codebase actively diverges (surfaced as a normal split/inconsistent-observation choice), and new observed rules get added alongside.

## Testing & verification

- `qa-engineer` hard-requires `Skill(skill: "superpowers:test-driven-development")` for the red/green/refactor methodology — own scope narrows to writing the actual test files and running them, not re-deriving TDD process rules. Same "hard-required, never reimplemented" pattern as `idea-explorer`/`spec-writing`/`plan-writing`.
- Framework/command detection: inspect the repo itself first (existing test files, package-manifest test scripts, CI config) — same "follow existing conventions" approach `documentation-engineer` already uses. `.harness/standards.md`'s `## Testing` section overrides the inferred guess when present.
- Coverage: best-effort, reported not gated. Runs whatever coverage tool is detected (same "skip silently if unavailable" precedent as `codebase-auditor`), never blocks publish on a hard threshold.

## Task identity & files

No tracker, so no T### numbers. Task identity is a feature-name slug, date-prefixed exactly like `docs/.plans/` and `docs/.specs/` already are:

- **`docs/.tasks/YYYY-MM-DD-<feature-slug>.md`** — owned by `task-orchestrator`, standalone format for tracking, not planning (not routed through `plan-writing`/`writing-plans` for *content* — a deliberate divergence from the "hard-required, never reimplemented" pattern for plan *authoring* specifically, while still hard-requiring `superpowers:using-git-worktrees` for the *worktree/git mechanics*). Committed/versioned like `docs/.plans/`, not gitignored state. Date prefix means collision is only possible same-day same-slug — `task-orchestrator` just asks (resume vs. new slug) if that happens.
- **`docs/.plans/`** stays exactly what it is today — output of `plan-writing`/`writing-plans` for architectural brainstorming work.

**Plan Dedup.** Chain flow only starts after the gate has already run `spec-writing`→`plan-writing`, which produces `docs/.plans/<feature>.md` — a full implementation plan. `task-orchestrator` Plan Mode hard-requires this file (same "Upstream Existence Check" pattern `solution-architect` uses for prd+user-flows) and reads it as *the* plan — it does not re-draft implementation steps into `docs/.tasks/`. That file adds only what `plan-writing` doesn't produce: the feasibility assessment, worktree/branch identity, and the Task State log. One consequence: `superpowers:executing-plans` is never invoked for Chain flow — the plan-tracking role it would normally play is replaced entirely by `task-orchestrator`'s own Task State log, and `docs/.plans/<feature>.md` itself stays static reference material once written.

**`## Task State` section**, inside the task file, two parts:
- `### Current` — overwritten by whichever agent just finished: phase, handoff target, status, worktree path + branch name (every downstream agent reads this first and operates in that worktree — the one place worktree identity is recorded, no separate marker file), key info the next agent needs right now. Read this first — top of file, one glance shows where things stand.
- `### History` — append-only, one summarized line per completed phase (not full detail — that lives in git history / actual test output).

## Task decomposition (`project-manager`)

Sits between requirements and implementation, as an **optional** last step after `requirements-engineer` — not a gate. Requires `docs/requirements/prd.md` to run at all (nothing to decompose without one), but nothing downstream requires `project-manager` to have run. Chain flow works fine straight off an ad hoc request with no `TRACKER.md` in sight — gate fires → `spec-writing`/`plan-writing` → `task-orchestrator`, same as if `project-manager` never existed. `TRACKER.md` is a nice-to-have index for when you do want task-list visibility, matching cairn's no-gates philosophy. Reads `user-stories.md` too if present, optional.

- **Generate mode** (no `docs/.tasks/TRACKER.md` yet): reads the PRD, proposes a decomposition into discrete task stubs, confirmed via `AskUserQuestion` before writing (same descriptive→prescriptive-style gate as `harness-engineer`, applied to task boundaries instead of code conventions). Writes `docs/.tasks/TRACKER.md`: one row per task — slug, one-line scope, status.
- **Granularity:** one row per user story when `user-stories.md` exists — a user story is already sized right for one branch/PR/TDD-cycle, and cairn's own `documentation-auditor` already traces every PRD `FR-###` to a user story, so the atomic boundary is already vetted. Falls back to one row per PRD feature/epic section when no `user-stories.md` exists to decompose from.
- **Update mode** (`TRACKER.md` exists): diffs the current PRD against it — new requirements become new rows, nothing gets silently removed. Also resyncs every row's status by `Glob`-ing `docs/.tasks/` for a file matching that row's slug and reading its Task State `### Current` phase (`Not Started` if no matching file yet, `In Progress: <phase>` from `### Current`, `Published` once `task-orchestrator` Publish Mode completed it). Read-only against the per-task files — never writes into them, that's `task-orchestrator`'s territory.
- Terminal — does not itself invoke `task-orchestrator`. A `TRACKER.md` row is picked up later, either via `/cairn-run-task <slug>` (see below) or a plain natural-language request naming the task — that's when the gate/`plan-writing`/`task-orchestrator` sequence actually runs for that one task.
- `docs/.tasks/TRACKER.md`'s slugs are the same namespace `task-orchestrator` creates per-task files in (`docs/.tasks/YYYY-MM-DD-<slug>.md`) — a row's slug and its eventual task file's slug must match for status auto-sync to find it.

**UAT checklist** — `task-orchestrator` Publish Mode generates a short manual-verification checklist from the task's scope, included in the PR/MR body. Kept from maestro; useful even solo as a pre-merge sanity pass.

## VCS / Publish

`task-orchestrator` Publish Mode targets both GitHub (`gh`) and GitLab (`glab`) — detects remote host from `origin` (if a repo has both a GitHub and GitLab remote, `origin` wins; no multi-remote publish), uses the matching CLI. Consolidated commit, UAT checklist, PR/MR creation.

## New command: `/cairn-run-task`

`/cairn-run-task <feature-slug>` — creates or resumes `docs/.tasks/YYYY-MM-DD-<feature-slug>.md` and runs the Chain flow from wherever its `### Current` state left off. Chain-flow only, since Direct flow never creates a task file — small bug-fixes stay natural-language-only through `intent-analyzer`'s normal routing, no command entry point for them. Still also reachable via plain natural-language request for Chain-flow work; this command is a direct entry point for the "call task, let it run" usage pattern.

## Open questions

None outstanding — all resolved during brainstorming, including the plan-authoring duplication originally flagged here (see Plan Dedup above: `task-orchestrator` now hard-requires and reads `docs/.plans/<feature>.md` rather than re-authoring a second plan).
