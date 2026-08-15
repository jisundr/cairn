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
- `~/Projects/maestro/.claude/skills/delivery-tracker/SKILL.md` (TRACKER.md format, and its source-of-truth layering — backend owns content, TRACKER.md owns board state — reused for Ticket Sync, see Task Decomposition below)
- `~/Projects/maestro/.claude/skills/harness-rules-guide/SKILL.md`
- `~/Projects/maestro/.claude/skills/coding-chain-guide/SKILL.md` (chain sequencing, fix-cycle routing, and its "Unattended Runs (swarm.sh)" section)
- `~/Projects/maestro/.claude/scripts/swarm.sh` (tmux/worktree/stale-detection mechanics — ported, see Unattended Execution below)

## Scope decision

Same principle as the prior writer-trio port: maestro is a fully meshed 19-agent framework; porting any one agent at face value pulls in the agents and infra it references. cairn stays self-contained, no fixed roster.

**What's explicitly NOT ported, and why:**

| maestro infra | Why dropped |
|---|---|
| ClickUp-only assumption | Backend is GitHub/GitLab (auto-detected from `origin`, reusing `task-orchestrator` Publish Mode's existing detection) or ClickUp (explicit opt-in config, no git-remote signal for it) — not ClickUp-only like maestro defaulted. See Ticket Sync below; this reopens and replaces the earlier "fully local, no tracker" decision. |
| `delivery-tracker`'s `tracker.html` static kanban viewer | Real, self-contained, zero-dependency — but extra scope beyond what was asked; `docs/.tasks/TRACKER.md` stays a plain Markdown table for now, viewer is a clean future add-on if wanted |
| `.codegraph/` MCP tool (call-site/blast-radius analysis) | Same precedent as `codebase-auditor`'s port — no codegraph dependency in cairn |
| Maestro's Interactive/Auto mode distinction | Claude Code itself already has auto/manual permission modes — no need to reimplement a separate mode split on top of them. Only Attended vs. Unattended remains as a coding-chain-specific distinction (see Unattended Execution below) |
| `.maestro/token-usage.db` MR token-usage section | cairn's usage tracking is the separate `/cairn-usage` dashboard, not per-task |
| Hard 80% coverage gate | Stack-agnostic here means coverage tooling availability varies; best-effort report instead (see Testing section) |
| Per-stack engineer-guide skills (react/fastapi/rust/tauri/etc.) | Stack-agnostic implementation — infer conventions from the repo itself, no maintained per-stack skill library |
| `LEARNINGS:` block → `CLAUDE.md` `## Learnings` merge | Separate feature, no merge mechanic exists in cairn today; replaced by the lighter Task State section (below), scoped to this port |
| ID Input Resolution (bare tracker ID → synthesized task file from scratch, no local file required yet) | Partially reinstated, lighter — `/cairn-run-task` accepts a ticket URL/ID (see New command below), but only to look up an *existing* `TRACKER.md` row/task folder, never to synthesize one from nothing the way maestro's version does |

## Agent roster

| Agent | Model | Role | Terminal? |
|---|---|---|---|
| `project-manager` | sonnet | Decomposes `docs/requirements/prd.md` (+ `user-stories.md`) into task stubs, writes `docs/.tasks/TRACKER.md` (local index). Owns ticket content authoring (GitHub/GitLab issue or ClickUp task) once a plan exists for a row — see Ticket Sync. Update Mode auto-syncs each row's status from its ticket (if one exists) or its matching `docs/.tasks/YYYY-MM-DD-<slug>/STATE.md` otherwise | Terminal |
| `harness-engineer` | sonnet | Generate/update `.harness/*.md` from observed conventions (or, on a fresh codebase, from a direct interview — see Fresh Codebase below), `AskUserQuestion` per-rule confirm gate, evidence-based by default, ~40-line cap per file | Terminal |
| `task-orchestrator` | sonnet | Plan Mode: hard-requires `docs/.plans/<feature>.md` to exist (reads it as the plan, does not re-author it — see Plan Dedup below), create/resume `docs/.tasks/YYYY-MM-DD-<feature-slug>/` as a thin layer over it (feasibility assessment + worktree/branch + STATE.md/HISTORY.md only), run qa-engineer+software-engineer feasibility assessment, create branch via `superpowers:using-git-worktrees`. Flips the ticket's status live at chain milestones when ticket sync is active (see Ticket Sync). Publish Mode: consolidated commit, PR/MR via `gh`/`glab`, UAT checklist, surfaces consolidated harness+doc-drift flag, closes the ticket and deletes the local plan draft once closure is observed | Terminal (Publish) |
| `qa-engineer` | sonnet | Writes tests — pre-implementation (TDD red, hard-requires `superpowers:test-driven-development`) in the chain, or post-implementation in Direct Mode | Hands off |
| `software-engineer` | opus | Implements in-scope code, stack-agnostic, makes qa-engineer's tests pass (TDD green) | Hands off |
| `qa-auditor` | sonnet | Independent post-impl re-verification: scoped tests, best-effort coverage report, code quality; conditional security/perf/dependency checks (tag- or software-engineer-flagged, same routing as maestro) | Hands off → task-orchestrator Publish |

## Two flows

**Direct** (bug-fix/decision — matches intent-analyzer's existing Brainstorming-Gate-skip signal): `software-engineer` (Direct Mode, works on current branch, no automated commit/PR) → `qa-engineer` (tests written post-hoc) → done. No task file, no task-orchestrator, no branch automation.

**Chain** (new-feature/refactor — gate fires, planning already happened upstream): `task-orchestrator` (Plan) → `documentation-auditor` (Doc Gate) → `qa-engineer` (red) → `software-engineer` (green) → `qa-auditor` → `documentation-auditor` (Doc Post-Impl) → `task-orchestrator` (Publish). See Documentation Gates below.

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

**Drift flagging:** `software-engineer`, `qa-engineer`, `qa-auditor` may each emit an optional `HARNESS FLAG:` note in their handoff output when they introduce/observe a pattern not covered by any existing `.harness/` rule (distinct from a violation — those go through `qa-auditor`'s HIGH-finding path above). `task-orchestrator` collects these across the chain and surfaces one consolidated `AskUserQuestion` at Publish Mode — alongside `documentation-auditor`'s Doc Post-Impl findings, see Documentation Gates below, same prompt: run `harness-engineer` Update mode, run `documentation-engineer` for doc drift, both, or skip and publish as-is. `harness-engineer` still runs its own per-rule confirm gate when invoked — this is only the trigger.

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

- **`docs/.tasks/YYYY-MM-DD-<feature-slug>/`** — owned by `task-orchestrator`, a **folder** (not a single file — see Unattended Execution below for why), standalone format for tracking, not planning (not routed through `plan-writing`/`writing-plans` for *content* — a deliberate divergence from the "hard-required, never reimplemented" pattern for plan *authoring* specifically, while still hard-requiring `superpowers:using-git-worktrees` for the *worktree/git mechanics*). Scratch (git-excluded within the worktree) while the chain is actively running; `task-orchestrator`'s Publish Mode commit explicitly includes the folder's final state, making it permanent history once merged — `TRACKER.md`'s Task File link stays valid forever, it's never cleaned up post-merge. Date prefix means collision is only possible same-day same-slug — `task-orchestrator` just asks (resume vs. new slug) if that happens.
- **`docs/.plans/`** stays exactly what it is today — output of `plan-writing`/`writing-plans` for architectural brainstorming work.

**Plan Dedup.** Chain flow only starts after the gate has already run `spec-writing`→`plan-writing`, which produces `docs/.plans/<feature>.md` — a full implementation plan.

**Bounded-path work never reaches the chain.** `intent-analyzer`'s gate firing `brainstorm-first` doesn't guarantee a `docs/.plans/` file — the brainstorming dialogue itself still classifies spike/bounded/architectural, and only the architectural path produces a plan document (`spec-writing`→`plan-writing`); its bounded path implements directly, inline, in that same session (TDD applies, no plan doc, per `superpowers:brainstorming`'s own rules) — the work is just done by the time brainstorming ends. This isn't a gap to route around: Chain flow is self-selecting on "a `docs/.plans/` file exists for this slug," not on task type — nobody invokes `/cairn-run-task` for work that finished during brainstorming, so `task-orchestrator`'s hard-require on the plan file never actually fails in practice, it simply never gets asked to run for bounded-classified work. `task-orchestrator` Plan Mode hard-requires this file (same "Upstream Existence Check" pattern `solution-architect` uses for prd+user-flows) and reads it as *the* plan — it does not re-draft implementation steps into `docs/.tasks/`. That folder adds only what `plan-writing` doesn't produce: the feasibility assessment, worktree/branch identity, and the Task State log. If the plan itself needs updating mid-chain (scope turned out off), that edit happens inside the feature worktree like everything else — committed to the feature branch, merged into `main` at Publish along with the code. No separate main-checkout write, no dedicated planning branch/worktree — one worktree per task stays the whole model, kept simple. To look at a plan/task without a terminal `cd`, `STATE.md`'s `Worktree:` path is a ready `code <path>` target for VS Code.

**Naming match.** The plan's `<feature-name>` must equal the task's slug exactly, so lookup is unambiguous: `Glob(docs/.plans/*-<slug>.md)` — matched on slug only, not date, since the plan may have been written days before the task actually runs. When the user asks `plan-writing` to create a plan for a `TRACKER.md` row, the row's slug is what gets passed through as the plan's feature-name — not independently chosen.

One nuance this resolves: `writing-plans`' own plan template carries a `REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans` header and an Execution Handoff step asking the user to choose between them — neither of which is `task-orchestrator`'s chain. No change to `plan-writing`/`writing-plans` is needed to resolve this: plan *creation* and task *execution* are two separate, explicitly user-triggered actions in this design (per Task Decomposition below — a user picks a `TRACKER.md` row and asks for a plan; running the task is a distinct later request). Whatever `plan-writing`'s own Execution Handoff dialogue suggests is simply not acted on in the coding-chain context — the user's subsequent "run this task" (or `/cairn-run-task`) request is what invokes `task-orchestrator` directly, superseding it. `docs/.plans/<feature>.md` stays static reference material once written; `superpowers:executing-plans` is never invoked for Chain flow.

**`STATE.md`** (inside the task folder) — overwritten by whichever agent just finished: phase, handoff target, status, a `Plan:` pointer to the `docs/.plans/` file this task tracks (see Templates below), worktree path + branch name (every downstream agent reads this first and operates in that worktree — the one place worktree identity is recorded, no separate marker file), key info the next agent needs right now. Read this first — one glance shows where things stand. `HISTORY.md`, alongside it, is the append-only log: one summarized line per completed phase (not full detail — that lives in git history / actual test output).

**Phase values:** `PLAN` · `DOC-GATE` · `QA-RED` · `IMPLEMENT` · `QA-AUDIT` · `DOC-POST-IMPL` · `PUBLISH` — one per chain agent invocation, in order (see Documentation Gates below for the two `DOC-*` phases). Plus `HANDOFF NEEDED` as a pause state, unattended-only (see Unattended Execution below).

## Documentation gates

Matches maestro's `DOC PASS` phase, but as two invocations of the existing `documentation-auditor` — no new agent, no changes to `agents/documentation-auditor.md`. This is a deliberate, scoped exception to that agent's "never automatically after a write" convention, specific to the coding chain (its manual/on-demand use everywhere else in cairn is unaffected).

- **Doc Gate** (right after `task-orchestrator` Plan, before `qa-engineer` starts): checks whether the plan's scope will require doc updates, against what already exists. Read-only, reports findings only, same as always. A HIGH-severity finding (plan contradicts existing docs, or depends on a doc that isn't there) surfaces via `AskUserQuestion` before continuing — proceed anyway, or stop and fix upstream docs first. Anything lower severity just gets noted in `STATE.md`'s `Key info` and the chain continues.
- **Doc Post-Impl** (after `qa-auditor`, before Publish): checks docs (README/setup/API/dev-guides) against what actually got built. Findings don't block or auto-fix (`documentation-auditor` never invokes a writer agent itself) — they fold into the *same* consolidated `AskUserQuestion` `task-orchestrator` already surfaces at Publish for harness-drift flags: run `documentation-engineer` to fix doc drift, run `harness-engineer` Update mode for harness drift, both, or skip and publish as-is.
- Maestro's per-submodule README/CLAUDE.md auto-write and `LEARNINGS:` merge at this step are dropped — the former would require `documentation-auditor` to write, which it doesn't do in cairn; the latter's merge mechanic doesn't exist here at all (already dropped, see Scope decision).

## Submodules

Light support only — not maestro's full subsystem (Pre-Chain Preflight, Post-Merge Submodule Sync with a merge-target-vs-tracked-branch guard, `pending-submodule-sync.md` tracking, auto-triggered by `gitlab-mr-reviewer`'s Thread Watch). That's a subsystem of its own, and its trigger mechanism (`gitlab-mr-reviewer`) isn't ported here anyway.

- `task-orchestrator` detects submodule scope from the plan's Files section (paths inside a submodule directory) and creates the worktree/branch inside that submodule instead of the parent repo.
- **No copy step needed for `.harness/`** — since it's committed (see below), `git worktree add` already carries it into any new worktree, parent or submodule, same as any other tracked file. Maestro needed `swarm.sh` to explicitly copy `.harness/` in because it's gitignored there; that whole mechanism is unnecessary here.
- Parent-repo pointer bump after a submodule PR merges stays manual — same as today, no automation added.

## `.harness/` is committed, not gitignored

Reverses maestro's own convention (gitignored by design there). Committing it means: it propagates to every clone/checkout automatically — any developer, or any submodule, gets the standard setup for free, no separate distribution step. It also directly eliminates the worktree-copy problem above. `.harness/`'s own content is still 100% evidence-derived and confirmed via `AskUserQuestion` before writing (see `.harness/` presence-gating above) — only its git status changes, not how it's generated.

## Unattended execution

Long-running Chain-flow tasks can run detached, unsupervised — same mechanism as maestro's `swarm.sh`, ported as-is rather than replaced with Claude Code's native background primitives: tmux is a hard prerequisite, every run launches via `tmux new-session -d`, attach with `tmux attach -t <branch>`. Applies to Chain flow only — Direct flow's small fixes have no reason to run unattended.

- **Two modes total**, replacing maestro's three-way Interactive/Auto/Unattended split (Claude Code's own permission modes already cover the Interactive-vs-Auto distinction, nothing to reimplement there): **Attended** (default — runs in the current session like every other cairn agent) and **Unattended** (tmux-detached).
- **`docs/.tasks/<slug>/STATE.md` + `HISTORY.md`** take `SWARM_STATE.md`'s control-plane role — the durable, coarse-by-design record that survives a session boundary (which resuming an unattended run needs). Same files used for attended runs — no separate unattended-only format.
- **Handoff-needed pause.** A chain step that hits something it can't resolve alone in an unattended context (`AskUserQuestion` isn't available in a detached run, same constraint noted elsewhere in this design for background subagents) sets `STATE.md`'s `Phase: HANDOFF NEEDED` with its question in `Key info`, appends the same to `HISTORY.md`, and stops cleanly rather than hanging. A human resolves it by editing `STATE.md`'s answer field and re-triggering the run to resume (same worktree/branch reused).
- **Monitoring.** A read-only monitor pass reports progress + branch/PR status from `STATE.md`/`HISTORY.md` alone, printing the question and a bounded `tmux capture-pane` tail on `HANDOFF NEEDED`.
- **Stale detection.** Fingerprints progress each check via `git rev-parse HEAD` + `git status --porcelain` + `STATE.md`'s current phase; repeated identical fingerprints with no completion conclude the run is stalled and stop it, rather than running forever.

## Task decomposition (`project-manager`)

Sits between requirements and implementation, as an **optional** last step after `requirements-engineer` — not a gate. Requires `docs/requirements/prd.md` to run at all (nothing to decompose without one), but nothing downstream requires `project-manager` to have run. Chain flow works fine straight off an ad hoc request with no `TRACKER.md` in sight — gate fires → `spec-writing`/`plan-writing` → `task-orchestrator`, same as if `project-manager` never existed. `TRACKER.md` is a nice-to-have index for when you do want task-list visibility, matching cairn's no-gates philosophy. Reads `user-stories.md` too if present, optional.

- **Generate mode** (no `docs/.tasks/TRACKER.md` yet): reads the PRD, proposes a decomposition into discrete task stubs, confirmed via `AskUserQuestion` before writing (same descriptive→prescriptive-style gate as `harness-engineer`, applied to task boundaries instead of code conventions). Writes `docs/.tasks/TRACKER.md`: one row per task — slug, one-line scope, status (`Idea` — no ticket yet), ticket link (empty until a plan exists — see Ticket Sync below). Rows can also be hand-authored directly in the table (matching maestro's own "Idea rows authored here by hand") — `project-manager` never requires an `Idea` row to trace back to a PRD requirement, only PRD-derived rows go through its diff logic.
- **Granularity:** one row per user story when `user-stories.md` exists — a user story is already sized right for one branch/PR/TDD-cycle, and cairn's own `documentation-auditor` already traces every PRD `FR-###` to a user story, so the atomic boundary is already vetted. Falls back to one row per PRD feature/epic section when no `user-stories.md` exists to decompose from.
- **Update mode** (`TRACKER.md` exists): diffs the current PRD against it — new PRD-derived requirements become new `Idea` rows, nothing gets silently removed, hand-authored `Idea` rows are left untouched (no PRD to diff them against). Also resyncs every row's Status — from the ticket if one exists for that row (authoritative, matching maestro's own source-of-truth layering: backend owns content, `TRACKER.md` owns board state), falling back to `Glob`-ing `docs/.tasks/` for a matching `STATE.md` phase when no ticket exists yet (`Idea` / `Groomed` / `In Progress: <phase>` / `In Review` / `Blocked` / `Done`). Read-only against the per-task folders — never writes into them, that's `task-orchestrator`'s territory.
- Terminal — does not itself invoke `task-orchestrator`. A `TRACKER.md` row is picked up later, either via `/cairn-run-task <slug-or-path-or-ticket>` (see below) or a plain natural-language request naming the task — that's when the gate/`plan-writing`/`task-orchestrator` sequence actually runs for that one task.
- `docs/.tasks/TRACKER.md`'s slugs are the same namespace `task-orchestrator` creates per-task folders in (`docs/.tasks/YYYY-MM-DD-<slug>/`) — a row's slug and its eventual task folder's slug must match for status auto-sync to find it.

### Ticket Sync

`project-manager` owns all ticket content authoring — same responsibility maestro's version has, scoped to two backends instead of ClickUp-only: **GitHub/GitLab** (auto-detected from `origin`, reusing `task-orchestrator` Publish Mode's existing host detection) or **ClickUp** (explicit opt-in, needs its own API auth config — no git-remote signal for it).

- Once `plan-writing` produces `docs/.plans/<slug>.md` for a `TRACKER.md` row, `project-manager`'s next Update mode run creates (or updates) a matching ticket — issue/task title from the row's scope, body synced from the plan's content (not just a link, since the local file won't outlive the ticket — see below). Writes the ticket URL into `TRACKER.md`'s Ticket column and into `docs/.plans/<slug>.md` itself (a `Ticket:` line near the top), linking both ways.
- **`docs/.plans/<slug>.md` is a working draft, not the permanent record** — kept locally so the chain isn't hitting the tracker API on every read (`task-orchestrator`'s Naming Match `Glob` lookup stays exactly as specced, local-file-based). Creating the ticket is also the `Idea` → `Groomed` transition: a row is `Idea` until it has one. From there, status flips at the same three checkpoints maestro's own TRACKER STATUS SYNC uses — **In Progress** at branch/plan creation (Plan Mode start), **In Review** at PR/MR creation (Publish Mode, once opened), **Done** once merged/closed — plus **Blocked**, mapped from `STATE.md`'s `HANDOFF NEEDED` phase (see Unattended Execution), so a paused task reads as Blocked on the board rather than silently stuck In Progress.
- **`project-manager` owns the actual write, `task-orchestrator` calls it** — `task-orchestrator` never talks to `gh`/`glab`/ClickUp directly for status; at each checkpoint it invokes `project-manager` to perform the flip, keeping "the only agent that touches the external tracker" a single, consistent boundary (same agent that does the initial ticket creation/sync). Exact invocation mechanics (sync call, what gets passed) are a follow-up design, not detailed here yet.
- **Local plan file persists until the ticket closes** — not a fixed Publish-time delete. Ticket close normally coincides with `task-orchestrator` flipping status to Done at Publish, but if closure happens later or separately (manual close, delayed review), the local file just stays until then. `task-orchestrator` deletes `docs/.plans/<slug>.md` once it observes the ticket is closed — at Publish if that's when closure happens, or on a later invocation otherwise.
- No sync at all when neither GitHub/GitLab nor ClickUp is configured — `project-manager` and `task-orchestrator` degrade to the fully-local behavior already specced elsewhere (local Status derivation, plan never deleted automatically). Ticket sync is additive, not required.

**UAT checklist** — `task-orchestrator` Publish Mode generates a short manual-verification checklist from the task's scope, included in the PR/MR body (and, when ticket sync is active, in the ticket too). Kept from maestro; useful even solo as a pre-merge sanity pass.

## VCS / Publish

`task-orchestrator` Publish Mode targets both GitHub (`gh`) and GitLab (`glab`) — detects remote host from `origin` (if a repo has both a GitHub and GitLab remote, `origin` wins; no multi-remote publish), uses the matching CLI. Consolidated commit, UAT checklist, PR/MR creation.

## New command: `/cairn-run-task`

`/cairn-run-task <slug-or-path-or-ticket> [--unattended]` — creates or resumes `docs/.tasks/YYYY-MM-DD-<feature-slug>/` and runs the Chain flow from wherever its `STATE.md` left off. Accepts a bare slug, a pasted path (to the task folder, any file inside it, or the `docs/.plans/` file), or a ticket URL/ID (resolved via `TRACKER.md`'s Ticket column when ticket sync is active) — resolves any of these to the right task rather than requiring the bare slug only. Chain-flow only, since Direct flow never creates a task folder — small bug-fixes stay natural-language-only through `intent-analyzer`'s normal routing, no command entry point for them.

**Attended vs. unattended:** `--unattended` forces the tmux-detached mode. If omitted, and `STATE.md` doesn't already record a mode from a prior run, `AskUserQuestion` asks once (Attended / Unattended) before starting — never silently defaults either way. Still also reachable via plain natural-language request for Chain-flow work (attended only — unattended needs the explicit flag or the prompt, there's no natural-language trigger for it); this command is a direct entry point for the "call task, let it run" usage pattern.

## Templates

Adapted from maestro's `harness-rules-guide/assets/*.template.md` and `delivery-tracker/assets/TRACKER.template.md` — literal template assets, not just prose format description. Live under a new shared skill, `skills/coding-chain-shared/assets/`, referenced by `project-manager`/`harness-engineer`/`task-orchestrator` the way `writer-shared` is referenced by the writer trio.

**`docs/.tasks/TRACKER.template.md`** — stripped of maestro's backend/milestone/promote-to-GitLab-ClickUp language entirely, since there's no backend:

```markdown
# Task Tracker

> Decomposed from docs/requirements/prd.md by `project-manager`. Status is auto-derived — from the linked ticket once one exists (authoritative), otherwise from docs/.tasks/YYYY-MM-DD-<slug>/STATE.md. Never edit Status by hand, it's overwritten on next sync.

| Slug | Scope | Status | Ticket | Task File |
|---|---|---|---|---|
| — | [one-line scope, from a user story or PRD feature] | Idea | — | — |

**Status values:** Idea · Groomed · In Progress: <phase> · In Review · Blocked · Done

Run `project-manager` (Update mode) to add rows as the PRD grows, sync tickets, and resync Status.
```

(Resolves the earlier open question about a Task File column — yes, included, filled in once `task-orchestrator` creates the matching file.)

**`docs/.tasks/<slug>/STATE.md`** — the live handoff file `task-orchestrator` creates, with the `## Task State` shape locked earlier plus an explicit `Plan:` pointer field (closing the question that was still open when this section was first drafted — every downstream agent now has one unambiguous place to find the actual implementation plan):

```markdown
# Task: <slug>

Mode: Attended
Phase: PLAN
Handoff to: qa-engineer
Status: <short status>
Plan: docs/.plans/<file>.md
Ticket: <url, or none>
Worktree: <path>
Branch: <branch-name>
Key info: <whatever the next agent needs right now>
Harness flags: none
```

**`docs/.tasks/<slug>/HISTORY.md`** and **`docs/.tasks/<slug>/UAT.md`** are separate files, not sections of `STATE.md` — `HISTORY.md` is the append-only phase log (one line per completed phase, kept as its own file so it can grow long without bloating the small file every chain step re-reads on every handoff); `UAT.md` is empty until `task-orchestrator` Publish Mode writes the checklist.

**`.harness/architecture.template.md`, `standards.template.md`, `workflow.template.md`** — kept structurally identical to maestro's (Stack/Layering/Boundaries/Data; Naming/Error handling/Testing/Logging; Branching/Commits-MR/Gates), evidence-driven so the actual headings barely matter — content is 100% derived at generation time, never templated. One real change: `workflow.template.md`'s branch-naming example line drops maestro's `feature/T###-<slug>` (no T### here) for **`<task-type>/<slug>`** — `feature/<slug>` or `refactor/<slug>`, matching the two Chain-flow task types.

## Open questions

None outstanding — all resolved during brainstorming, including the plan-authoring duplication originally flagged here (see Plan Dedup above: `task-orchestrator` now hard-requires and reads `docs/.plans/<feature>.md` rather than re-authoring a second plan).
