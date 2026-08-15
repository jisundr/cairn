# Coding Chain Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port 6 maestro agents (`project-manager`, `harness-engineer`, `task-orchestrator`, `qa-engineer`, `software-engineer`, `qa-auditor`) into cairn, giving it an actual implementation path beyond planning artifacts, plus one new command (`/cairn-run-task`) and one new shared skill (`coding-chain-shared`) holding template assets.

**Architecture:** Two flows — Direct (small bug-fixes, `software-engineer`→`qa-engineer`, no task file) and Chain (`task-orchestrator`→`documentation-auditor`→`qa-engineer`→`software-engineer`→`qa-auditor`→`documentation-auditor`→`task-orchestrator`, full task-folder tracking). `intent-analyzer` is untouched — only `CLAUDE.md` gains the new roster + documented sequence. Task state lives in `docs/.tasks/YYYY-MM-DD-<slug>/` (STATE.md/HISTORY.md/UAT.md), decomposed from a PRD by `project-manager` into `docs/.tasks/TRACKER.md`, optionally synced to a GitHub/GitLab/ClickUp ticket.

**Tech Stack:** Markdown agent/command/skill files (Claude Code plugin convention — no compiled code). Verification is `claude plugin validate . --strict` (plugin manifest/structure) plus headless `claude -p` runs against a scratch directory (cairn's own documented approach for command files — see repo's `CLAUDE.md` → "Testing a command end-to-end"). No pytest/TDD red-green applies here; there's no application code, only prompt content.

**Spec:** `docs/.specs/2026-08-15-coding-chain-port-design.md` — the plan argues from the spec, so the spec travels with it; executors read both. Every task below cites the exact spec section(s) it implements.

## Global Constraints

- Agent frontmatter fields: `name`, `description` (quoted, single string, includes `<example>` blocks per existing agent convention — see `agents/codebase-auditor.md` and `agents/documentation-auditor.md` for the shape), `tools`, `model`, `color`.
- Model assignments (spec "Agent roster"): `harness-engineer` sonnet, `project-manager` sonnet, `task-orchestrator` sonnet, `qa-engineer` sonnet, `software-engineer` opus, `qa-auditor` sonnet.
- File path conventions (spec "Task identity & files" / "Task decomposition"): `docs/.tasks/TRACKER.md` (flat), `docs/.tasks/YYYY-MM-DD-<slug>/{STATE.md,HISTORY.md,UAT.md}` (folder per task), `docs/.plans/YYYY-MM-DD-<slug>.md` (existing convention, read not written by this port), `.harness/{architecture,standards,workflow}.md` (committed, not gitignored — spec "`.harness/` is committed, not gitignored").
- No code comments unless the WHY is non-obvious (repo-wide convention, `CLAUDE.md`).
- Every new/changed agent or command file requires a `.claude-plugin/plugin.json` version bump before this plan's final commit (repo's `CLAUDE.md` → "Versioning" — minor bump, new agents/commands).
- `claude plugin validate . --strict` must pass after every task that adds or edits an agent/command/skill file — run it as each task's verification step, not just at the end.

---

### Task 1: Shared skill scaffold — `coding-chain-shared`

**Files:**
- Create: `skills/coding-chain-shared/SKILL.md`
- Create: `skills/coding-chain-shared/assets/TRACKER.template.md`
- Create: `skills/coding-chain-shared/assets/task/STATE.template.md`
- Create: `skills/coding-chain-shared/assets/task/HISTORY.template.md`
- Create: `skills/coding-chain-shared/assets/task/UAT.template.md`
- Create: `skills/coding-chain-shared/assets/harness/architecture.template.md`
- Create: `skills/coding-chain-shared/assets/harness/standards.template.md`
- Create: `skills/coding-chain-shared/assets/harness/workflow.template.md`

**Interfaces:**
- Consumes: spec sections "Templates", "Task decomposition (`project-manager`)", "Documentation gates" (phase list), "Unattended execution" (phase list) — this task's outputs are the literal file content for those sections.
- Produces: every later task (2–7, 9) invokes `Skill(skill: "coding-chain-shared")` at the start of its run and reads these template paths — the exact paths above are the interface later tasks depend on. Do not rename them.

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: coding-chain-shared
description: Shared template assets for cairn's coding-chain agents (project-manager, harness-engineer, task-orchestrator, qa-engineer, software-engineer, qa-auditor) — TRACKER.md format, per-task STATE/HISTORY/UAT templates, .harness/ templates. Loaded by each at the start of a run that creates or reads these files.
---

# Coding Chain Shared — Template Assets

Shared file templates used across the coding chain. Each agent loads this skill once at the start of any run that creates or reads `docs/.tasks/TRACKER.md`, a per-task folder, or `.harness/`.

## Templates in this skill

- `assets/TRACKER.template.md` — seed content for `docs/.tasks/TRACKER.md` (`project-manager`, Generate mode)
- `assets/task/STATE.template.md` — seed content for `docs/.tasks/<slug>/STATE.md` (`task-orchestrator`, Plan Mode)
- `assets/task/HISTORY.template.md` — seed content for `docs/.tasks/<slug>/HISTORY.md` (`task-orchestrator`, Plan Mode)
- `assets/task/UAT.template.md` — seed content for `docs/.tasks/<slug>/UAT.md` (`task-orchestrator`, Publish Mode)
- `assets/harness/architecture.template.md`, `standards.template.md`, `workflow.template.md` — seed shape for `.harness/*.md` (`harness-engineer`, Generate mode)

Every template's headings are structural scaffolding only — content under them is always derived (evidence-based for `.harness/`, decomposed-from-PRD for `TRACKER.md`, chain-state for `STATE.md`/`HISTORY.md`/`UAT.md`), never copied verbatim from the template itself.

## Status values (`TRACKER.md`)

`Idea` · `Groomed` · `In Progress: <phase>` · `In Review` · `Blocked` · `Done` — see `assets/TRACKER.template.md` for the legend. `Idea` = no ticket yet (rows can be hand-authored, never required to trace to a PRD requirement). `Groomed` = a ticket exists, chain not yet started. `In Progress`/`In Review`/`Done` mirror the ticket's own status, flipped live by `task-orchestrator` via `project-manager`. `Blocked` maps from `STATE.md`'s `HANDOFF NEEDED` phase.

## Phase values (`STATE.md`)

`PLAN` · `DOC-GATE` · `QA-RED` · `IMPLEMENT` · `QA-AUDIT` · `DOC-POST-IMPL` · `PUBLISH` — one per chain-agent invocation, in order. Plus `HANDOFF NEEDED` as an unattended-only pause state.
```

- [ ] **Step 2: Write `assets/TRACKER.template.md`**

```markdown
# Task Tracker

> Decomposed from docs/requirements/prd.md by `project-manager`. Status is auto-derived — from the linked ticket once one exists (authoritative), otherwise from docs/.tasks/YYYY-MM-DD-<slug>/STATE.md. Never edit Status by hand, it's overwritten on next sync.

| Slug | Scope | Status | Ticket | Task File |
|---|---|---|---|---|
| — | [one-line scope, from a user story or PRD feature] | Idea | — | — |

**Status values:** Idea · Groomed · In Progress: <phase> · In Review · Blocked · Done

Run `project-manager` (Update mode) to add rows as the PRD grows, sync tickets, and resync Status. Rows can also be hand-authored directly in this table — `project-manager` never requires a hand-authored `Idea` row to trace back to a PRD requirement.
```

- [ ] **Step 3: Write `assets/task/STATE.template.md`**

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

- [ ] **Step 4: Write `assets/task/HISTORY.template.md`**

```markdown
# History: <slug>

<!-- Append-only. One line per completed phase, in order. Not full detail — that lives in git history / actual test output. -->
```

- [ ] **Step 5: Write `assets/task/UAT.template.md`**

```markdown
# UAT Checklist: <slug>

<!-- Empty until task-orchestrator Publish Mode writes the checklist. -->
```

- [ ] **Step 6: Write `assets/harness/architecture.template.md`**

```markdown
> Refines coding-chain behavior. Cannot skip chain agents or verification.

# Architecture Rules

## Stack
<!-- no convention observed -->

## Layering
<!-- no convention observed -->

## Boundaries
<!-- no convention observed -->

## Data
<!-- no convention observed -->
```

- [ ] **Step 7: Write `assets/harness/standards.template.md`**

```markdown
> Refines coding-chain behavior. Cannot skip chain agents or verification.

# Coding Standards

## Naming
<!-- no convention observed -->

## Error handling
<!-- no convention observed -->

## Testing
<!-- no convention observed -->

## Logging
<!-- no convention observed -->
```

- [ ] **Step 8: Write `assets/harness/workflow.template.md`**

```markdown
> Refines coding-chain behavior. Gates are additive only.

# Workflow Rules

## Branching
- Branch names: feature/<slug> or refactor/<slug>.

## Commits / MR
- Conventional commits enforced.
- MR/PR description must include the UAT checklist.

## Gates (additive)
<!-- no convention observed -->
```

- [ ] **Step 9: Validate**

Run: `claude plugin validate . --strict`
Expected: passes (skill has valid frontmatter, no broken references — nothing yet references `coding-chain-shared`, that starts in Task 2).

- [ ] **Step 10: Commit**

```bash
git add skills/coding-chain-shared/
git commit -m "Add coding-chain-shared skill with template assets

Foundational shared templates for the coding-chain port: TRACKER.md,
per-task STATE/HISTORY/UAT, and .harness/ seed shapes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `harness-engineer`

**Files:**
- Create: `agents/harness-engineer.md`

**Interfaces:**
- Consumes: spec sections "`.harness/` presence-gating", "Fresh codebase", "`.harness/` is committed, not gitignored"; `skills/coding-chain-shared/assets/harness/*.template.md` (Task 1) for seed shape; `agents/codebase-auditor.md` for structural convention (frontmatter shape, SYSTEM ROLE / WORKFLOW INTENT / HARD REQUIREMENTS / numbered process / PHASE HANDOFF / EXIT & DERAILMENT / START sections).
- Produces: `.harness/architecture.md`, `.harness/standards.md`, `.harness/workflow.md` (read by Tasks 4–7's agents). `harness-engineer`'s exact name is what `task-orchestrator` (Task 4) auto-suggests invoking.

- [ ] **Step 1: Write frontmatter**

```yaml
---
name: harness-engineer
description: "Use this agent to generate or update the .harness/ convention files (architecture.md, standards.md, workflow.md) for the current codebase — deriving draft rules from the project's own observed conventions instead of hand-authoring them from a blank template. On a fresh/near-empty codebase, falls back to pre-filling from docs/architecture/architecture-spec.md when present, then interviewing for the rest, rather than writing evidence-free files. .harness/ is committed (not gitignored) so every clone/submodule gets the standard setup automatically.

<example>
Context: User wants agent-loaded convention files generated from what the codebase already does.
user: \"Generate harness rules for this repo\"
assistant: \"I'll use harness-engineer to observe the codebase's conventions, propose draft rules for confirmation, and write .harness/.\"
<commentary>
Harness generation request — dispatch harness-engineer.
</commentary>
</example>

<example>
Context: .harness/ already exists but the codebase evolved since it was written.
user: \"Our .harness/standards.md is stale\"
assistant: \"I'll re-run harness-engineer in Update mode — it diffs observed conventions against the codified rules and proposes amendments through the same confirm gate.\"
<commentary>
Existing .harness/ detected — Update mode, not Generate.
</commentary>
</example>"
tools: Read, Glob, Grep, Bash, AskUserQuestion, Write, Edit
model: sonnet
color: pink
---
```

- [ ] **Step 2: Write SYSTEM ROLE + WORKFLOW INTENT**

Model the shape on `agents/codebase-auditor.md` lines 9–25. Content requirements (spec "`.harness/` presence-gating" / "Fresh codebase"):
- Scope is exclusively the three `.harness/` files at the project root — never application source, never `.claude/`-equivalent cairn files.
- Two modes: Generate (no `.harness/` yet) and Update (`.harness/` exists — diff observed vs. codified, propose amendments through the same confirm gate).
- Terminal — no automatic handoff.
- Invoked standalone by the user at any time, or auto-suggested by `task-orchestrator` Plan Mode on first run if `.harness/` is absent (Task 4 depends on this exact trigger wording).

- [ ] **Step 3: Write HARD REQUIREMENTS**

Must include, near-verbatim from the spec:
- ONLY write files under `.harness/` (root) — never invent a rule with no observed basis.
- An evidence-free section stays empty with a `<!-- no convention observed -->` marker (matches Task 1's template).
- ALWAYS present derived rules for confirmation via `AskUserQuestion` before writing anything — the descriptive→prescriptive gate is mandatory, never skipped, never auto-applied.
- ALWAYS surface a split/inconsistent observation as an explicit choice — never silently pick one.
- ALWAYS enforce a ~40-line-per-file cap, dropping the weakest-evidence rules first.
- Must run in the main thread, never as a dispatched background subagent — the confirm gate depends on `AskUserQuestion`.
- `.harness/` is committed, not gitignored (spec section of the same name) — this agent's `Write`/`Edit` calls target tracked files, no special git-exclude step.

- [ ] **Step 4: Write the Mode Detection + Generate + Update process**

- Mode detection: `Glob` for existing `.harness/*.md` at the project root.
- **Generate mode, standard path:** observe the codebase (layering, naming, error handling, test placement, `git log` commit/branch patterns via `Bash`), derive rules with an evidence count each, present via `AskUserQuestion` for per-rule confirm/edit/drop, write confirmed rules into the three files (seeded from `skills/coding-chain-shared/assets/harness/*.template.md`, Task 1).
- **Generate mode, fresh-codebase path** (spec "Fresh codebase" section, verbatim behavior): detect a genuinely empty/near-empty repo (no source files beyond scaffolding). Step 1 — pre-fill: `Glob` for `docs/architecture/architecture-spec.md` (+ `docs/backend/{db-schema,api-spec}.md`, `docs/adr/*.md` if present); pull stack/layering/data-storage/service-contract decisions into `architecture.md`/`standards.md`, tagged `from-architecture-spec` citing the source doc. Step 2 — interview: `AskUserQuestion` for whatever isn't covered (style, test placement, workflow/branch/commit format), tagged `user-specified`. Both tags replace the usual evidence count.
- **Update mode:** diff observed conventions against the existing files, propose amendments through the same confirm gate; `from-architecture-spec`/`user-specified` rules stay untouched unless the codebase actively diverges (surfaced as a split choice), new observed rules added alongside.

- [ ] **Step 5: Write PHASE HANDOFF + EXIT & DERAILMENT HANDLING + START**

Model on `codebase-auditor.md`'s equivalent sections. Terminal — no handoff. Completion block reports mode used (Generate/Update, and fresh-codebase-interview if that path fired), files written, rule counts by provenance tag (observed / from-architecture-spec / user-specified).

- [ ] **Step 6: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 7: Headless smoke test**

```bash
mkdir -p /tmp/cairn-harness-test && cd /tmp/cairn-harness-test && git init -q
claude -p "generate harness rules for this repo" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: agent detects the empty repo, runs the fresh-codebase interview path (no `docs/architecture/` present in this scratch dir), writes `.harness/*.md` with `user-specified`-tagged content only. Inspect the scratch dir's `.harness/` files to confirm — don't just trust the reported output.

- [ ] **Step 8: Commit**

```bash
git add agents/harness-engineer.md
git commit -m "Add harness-engineer agent

Generates/updates .harness/ convention files from observed codebase
conventions, with a fresh-codebase interview fallback that pre-fills
from docs/architecture/architecture-spec.md when present.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `project-manager`

**Files:**
- Create: `agents/project-manager.md`

**Interfaces:**
- Consumes: spec sections "Task decomposition (`project-manager`)", "Ticket Sync"; `skills/coding-chain-shared/assets/TRACKER.template.md` (Task 1); `skills/writer-shared/SKILL.md` for Upstream Existence Check convention (pattern only — `project-manager` doesn't load `writer-shared` itself, it's not a writer-trio agent, but reuses the same `Glob`-based existence-check mechanic).
- Produces: `docs/.tasks/TRACKER.md` and ticket URLs, read by `task-orchestrator` (Task 4) and `/cairn-run-task` (Task 8).

- [ ] **Step 1: Write frontmatter**

```yaml
---
name: project-manager
description: "Use this agent to decompose a PRD into a local task list (docs/.tasks/TRACKER.md) and to own all ticket content authoring (GitHub/GitLab issue or ClickUp task) once a plan exists for a row. Optional last step after requirements-engineer, never a gate — nothing downstream requires it to have run. Also the only agent that writes to an external tracker; task-orchestrator calls it to flip ticket status rather than touching gh/glab/ClickUp itself.

<example>
Context: PRD exists, user wants a task breakdown.
user: \"Break the PRD into tasks\"
assistant: \"I'll use project-manager to decompose the PRD into docs/.tasks/TRACKER.md, one row per user story.\"
<commentary>
PRD-to-tasks decomposition — dispatch project-manager Generate mode.
</commentary>
</example>

<example>
Context: TRACKER.md exists, PRD has grown.
user: \"Sync the tracker, we added new requirements\"
assistant: \"I'll run project-manager in Update mode to diff the PRD and resync ticket status.\"
<commentary>
TRACKER.md exists — Update mode, not Generate.
</commentary>
</example>"
tools: Read, Glob, Grep, Bash, AskUserQuestion, Write, Edit
model: sonnet
color: teal
---
```

- [ ] **Step 2: Write SYSTEM ROLE + WORKFLOW INTENT**

Content requirements:
- Sits between requirements and implementation, optional last step after `requirements-engineer` — not a gate.
- Requires `docs/requirements/prd.md` to run at all (Upstream Existence Check via `Glob`, same pattern as `writer-shared`'s check — TERMINATED-style message if absent). Reads `user-stories.md` too if present, optional.
- Terminal — does not itself invoke `task-orchestrator`.

- [ ] **Step 3: Write Generate mode**

- No `docs/.tasks/TRACKER.md` yet: read the PRD, propose a decomposition into task stubs, confirm via `AskUserQuestion` before writing (descriptive→prescriptive gate, same shape as `harness-engineer`'s rule-confirm gate).
- Granularity: one row per user story when `user-stories.md` exists (a user story is already sized right for one branch/PR/TDD-cycle, and `documentation-auditor` already traces every PRD `FR-###` to a user story). Falls back to one row per PRD feature/epic section when no `user-stories.md` exists.
- Write `docs/.tasks/TRACKER.md` seeded from `skills/coding-chain-shared/assets/TRACKER.template.md` (Task 1): slug, one-line scope, Status `Idea`, empty Ticket/Task File columns.
- Rows can also be hand-authored directly in the table — never require a hand-authored `Idea` row to trace back to a PRD requirement.

- [ ] **Step 4: Write Update mode**

- `docs/.tasks/TRACKER.md` exists: diff current PRD against it — new PRD-derived requirements become new `Idea` rows, nothing silently removed, hand-authored `Idea` rows left untouched.
- Resync every row's Status: from its ticket if one exists (authoritative — backend owns content, `TRACKER.md` owns board state), else `Glob` `docs/.tasks/` for a matching `STATE.md` phase (`Idea`/`Groomed`/`In Progress: <phase>`/`In Review`/`Blocked`/`Done`).
- Read-only against per-task folders — never write into them, that's `task-orchestrator`'s territory.

- [ ] **Step 5: Write Ticket Sync section**

Content requirements, verbatim from spec "Ticket Sync":
- Backend: GitHub/GitLab auto-detected from `origin` (same `git remote`-based detection `task-orchestrator` Publish Mode uses), or ClickUp via explicit opt-in config (no git-remote signal for it) — no sync at all when neither is configured, degrades to fully-local behavior.
- Once `plan-writing` produces `docs/.plans/<slug>.md` for a row, the next Update mode run creates/updates a matching ticket — title from the row's scope, body synced from the plan's actual content (not just a link, since the local file won't outlive the ticket). Write the ticket URL into `TRACKER.md`'s Ticket column and into `docs/.plans/<slug>.md` itself (a `Ticket:` line near the top) — linking both ways.
- Creating the ticket is the `Idea` → `Groomed` transition.
- `task-orchestrator` calls `project-manager` (this agent) to perform status flips at chain checkpoints (In Progress / In Review / Done) rather than touching `gh`/`glab`/ClickUp itself — invocation mechanics (what gets passed) are out of scope for this task, keep this agent's own status-write logic self-contained and callable, exact calling convention is a follow-up.
- UAT checklist gets included in the ticket body too when sync is active.

- [ ] **Step 6: Write PHASE HANDOFF + EXIT & DERAILMENT HANDLING + START**

Terminal — no handoff. Completion block reports mode, rows added/updated, tickets created/synced (or "no backend configured" if local-only).

- [ ] **Step 7: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 8: Headless smoke test**

```bash
mkdir -p /tmp/cairn-pm-test/docs/requirements && cd /tmp/cairn-pm-test && git init -q
cat > docs/requirements/prd.md <<'EOF'
# Test PRD
## Features
- User login
- Password reset
EOF
claude -p "decompose the prd into tasks" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: `docs/.tasks/TRACKER.md` created with two `Idea` rows (no `user-stories.md` present, so PRD-feature-level granularity), no ticket sync attempted (no `origin` remote configured in this scratch repo). Inspect the file directly.

- [ ] **Step 9: Commit**

```bash
git add agents/project-manager.md
git commit -m "Add project-manager agent

Decomposes a PRD into docs/.tasks/TRACKER.md and owns ticket content
authoring for GitHub/GitLab/ClickUp, once a plan exists for a row.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `task-orchestrator`

**Files:**
- Create: `agents/task-orchestrator.md`

**Interfaces:**
- Consumes: spec sections "Task identity & files", "Documentation gates", "Submodules", "Unattended execution", "VCS / Publish"; `skills/coding-chain-shared` (Task 1) for `STATE.md`/`HISTORY.md`/`UAT.md` templates; `superpowers:using-git-worktrees` (hard-required, external); `project-manager` (Task 3) for ticket status-flip calls.
- Produces: `docs/.tasks/YYYY-MM-DD-<slug>/{STATE.md,HISTORY.md,UAT.md}`, git branches/worktrees, PR/MR — read/used by Tasks 5–7 (`qa-engineer`/`software-engineer`/`qa-auditor`) and Task 8 (`/cairn-run-task`).

- [ ] **Step 1: Write frontmatter**

```yaml
---
name: task-orchestrator
description: "Use this agent to run the coding-chain's Plan and Publish steps. Plan Mode: hard-requires an existing docs/.plans/<slug>.md (reads it as the plan, never re-authors it), creates docs/.tasks/YYYY-MM-DD-<slug>/, runs a qa-engineer+software-engineer feasibility assessment, creates the branch/worktree via superpowers:using-git-worktrees. Publish Mode: consolidated commit, PR/MR via gh/glab, UAT checklist, surfaces harness+doc-drift flags, closes the ticket and deletes the local plan draft once closure is observed. First and last agent in the chain.

<example>
Context: A docs/.plans/ file exists for a task and the user wants to start work.
user: \"Run the user-login task\"
assistant: \"I'll invoke task-orchestrator Plan Mode — it'll hard-require the plan, set up the branch/worktree, and hand off to qa-engineer.\"
<commentary>
Chain-flow start — task-orchestrator Plan Mode is always first.
</commentary>
</example>

<example>
Context: qa-auditor has just finished a clean pass.
user: (chain handoff, not a direct user message)
assistant: \"qa-auditor handed off clean — invoking task-orchestrator Publish Mode.\"
<commentary>
task-orchestrator is also the chain's terminal agent.
</commentary>
</example>"
tools: Read, Glob, Grep, Bash, AskUserQuestion, Write, Edit
model: sonnet
color: orange
---
```

- [ ] **Step 2: Write SYSTEM ROLE + WORKFLOW INTENT**

Content requirements:
- First and last agent in Chain flow. Two modes: Plan and Publish.
- Chain sequence this agent sits at the ends of (spec "Two flows"): Plan → `documentation-auditor` (Doc Gate) → `qa-engineer` → `software-engineer` → `qa-auditor` → `documentation-auditor` (Doc Post-Impl) → Publish.
- Never invoked for Direct flow (bug-fix/decision) — that goes straight to `software-engineer` Direct Mode.

- [ ] **Step 3: Write Plan Mode**

Content requirements, verbatim from spec "Task identity & files" / "Plan Dedup" / "Naming match" / "Submodules":
- Hard-require `docs/.plans/<slug>.md` via `Glob(docs/.plans/*-<slug>.md)` — matched on slug only, not date. If absent: `TERMINATED: docs/.plans/*-<slug>.md is required before task-orchestrator can run. Create a plan first.`
- Read the plan as-is — never re-author implementation steps into `docs/.tasks/`.
- Create `docs/.tasks/YYYY-MM-DD-<slug>/` (folder, seeded from `skills/coding-chain-shared/assets/task/*.template.md`, Task 1). Date-prefix collision (same-day same-slug): ask via `AskUserQuestion` (resume existing vs. new slug).
- Detect submodule scope from the plan's Files section (paths inside a submodule directory) — if scoped there, create the worktree/branch inside that submodule instead of the parent repo.
- Load `.harness/workflow.md` if present (`Glob`-check, skip silently if absent) — its `## Branching` section governs the branch name chosen below.
- Create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` — hard-required, this agent never reimplements worktree mechanics itself. Branch name: `.harness/workflow.md`'s convention if loaded, else default `<task-type>/<slug>` (`feature/<slug>` or `refactor/<slug>`, matching the plan's task type).
- Run feasibility assessment: dispatch `qa-engineer` and `software-engineer` to assess test/implementation feasibility against the plan (no files written yet).
- If `.harness/` is absent entirely, suggest running `harness-engineer` (this is the exact trigger `harness-engineer`, Task 2, documents).
- Ask Attended/Unattended if `/cairn-run-task` didn't already specify (see Task 8) and `STATE.md` doesn't record a prior mode.
- Write `STATE.md`: `Mode`, `Phase: PLAN`, `Handoff to: qa-engineer`, `Plan:` pointer, `Ticket:` (from `TRACKER.md` if synced), `Worktree`, `Branch`, `Key info`. Append one `HISTORY.md` line.
- If ticket sync is active: call `project-manager` to flip ticket status to In Progress.
- Hand off to `documentation-auditor` for Doc Gate (spec "Documentation gates") — NOT directly to `qa-engineer`. Doc Gate checks whether the plan's scope requires doc updates; a HIGH-severity finding surfaces via `AskUserQuestion` (proceed anyway / stop and fix upstream docs first) before continuing to `qa-engineer`. Lower-severity findings just get noted in `STATE.md`'s `Key info`.

- [ ] **Step 4: Write Publish Mode**

Content requirements, verbatim from spec "VCS / Publish" / "Documentation gates" / "`.harness/` presence-gating" (drift flagging) / "Ticket Sync":
- Triggered after `qa-auditor` → `documentation-auditor` (Doc Post-Impl) hands off clean.
- Generate the UAT checklist from the task's scope → write `UAT.md`. If `.harness/workflow.md` was loaded in Plan Mode, its `## Commits / MR` section governs commit message format and what the PR/MR description must include (UAT checklist at minimum, per the template).
- Surface ONE consolidated `AskUserQuestion`: harness-drift flags (collected `HARNESS FLAG:` notes from `software-engineer`/`qa-engineer`/`qa-auditor` across the chain) + Doc Post-Impl findings — run `harness-engineer` Update mode, run `documentation-engineer` for doc drift, both, or skip and publish as-is.
- Detect remote host from `origin` (`gh` for GitHub, `glab` for GitLab; if a repo has both, `origin` wins — no multi-remote publish).
- Consolidated commit — includes the task folder's final state (now committed, no longer scratch).
- Create PR/MR with the UAT checklist in the body.
- If ticket sync is active: call `project-manager` to flip ticket status to In Review at PR/MR creation, then Done once merged/closed (this may be a later invocation, not necessarily in the same Publish Mode run — note this as a follow-up check, not a blocking wait).
- Once ticket closure is observed (immediately if it coincides with this Publish run, or on a later invocation otherwise): delete `docs/.plans/<slug>.md` (the local plan draft — the ticket is now the permanent record).
- Update `STATE.md` to `Phase: PUBLISH`, final `HISTORY.md` entry.

- [ ] **Step 5: Write Unattended Execution section**

Content requirements, verbatim from spec "Unattended execution":
- Two modes: Attended (default, current session) and Unattended (tmux-detached, ported from maestro's `swarm.sh`).
- Unattended: tmux hard prerequisite, launch via `tmux new-session -d`, attach via `tmux attach -t <branch>`.
- `STATE.md`+`HISTORY.md` are the control-plane files (same files as Attended, no separate format).
- Handoff-needed pause: a step that can't resolve alone in an unattended context (`AskUserQuestion` unavailable in a detached run) sets `STATE.md`'s `Phase: HANDOFF NEEDED` with the question in `Key info`, appends to `HISTORY.md`, stops cleanly. Resume: human edits `STATE.md`'s answer field, re-triggers the run (same worktree/branch reused).
- Monitoring: read-only pass reports progress from `STATE.md`/`HISTORY.md`, bounded `tmux capture-pane` tail on `HANDOFF NEEDED`.
- Stale detection: fingerprint via `git rev-parse HEAD` + `git status --porcelain` + current phase; repeated identical fingerprints with no completion → stalled, stop.

- [ ] **Step 6: Write PHASE HANDOFF + EXIT & DERAILMENT HANDLING + START**

Two PHASE HANDOFF blocks (Plan → Doc Gate, Publish → terminal). EXIT rows: plan file missing (TERMINATED), same-day slug collision (ask), `.harness/` absent (suggest `harness-engineer`, don't block), no ticket sync configured (proceed local-only).

- [ ] **Step 7: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 8: Commit**

```bash
git add agents/task-orchestrator.md
git commit -m "Add task-orchestrator agent

Plan Mode (hard-requires an existing plan, sets up branch/worktree/
task-folder, feasibility assessment) and Publish Mode (commit, PR/MR,
UAT checklist, drift-flag consolidation, ticket close). First and
last agent in the coding chain.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: `qa-engineer`

**Files:**
- Create: `agents/qa-engineer.md`

**Interfaces:**
- Consumes: spec section "Testing & verification"; `superpowers:test-driven-development` (hard-required, external) for TDD methodology; `STATE.md` from Task 4's output shape (reads `Plan:`, `Worktree` fields).
- Produces: failing tests + updated `STATE.md`/`HISTORY.md` (`Phase: QA-RED`), read by Task 6 (`software-engineer`).

- [ ] **Step 1: Write frontmatter**

```yaml
---
name: qa-engineer
description: "Use this agent to write tests in the coding chain — pre-implementation (TDD red phase, hard-requires superpowers:test-driven-development) when handed off from task-orchestrator, or post-implementation in Direct Mode when handed off from software-engineer. Detects test framework/commands from the repo itself, with .harness/standards.md's Testing section overriding the guess when present.

<example>
Context: task-orchestrator Plan Mode just handed off (via Doc Gate).
user: (chain handoff)
assistant: \"Invoking qa-engineer to write failing tests from the plan before implementation starts.\"
<commentary>
Chain flow, pre-implementation — TDD red phase.
</commentary>
</example>

<example>
Context: software-engineer just finished a Direct Mode fix.
user: (chain handoff)
assistant: \"Invoking qa-engineer to write tests for the fix that just landed.\"
<commentary>
Direct flow — tests written post-hoc, not pre-implementation.
</commentary>
</example>"
tools: Read, Glob, Grep, Bash, Write, Edit
model: sonnet
color: green
---
```

- [ ] **Step 2: Write SYSTEM ROLE + WORKFLOW INTENT**

Content requirements:
- Two modes, detected from opening context: Chain (pre-implementation, from `task-orchestrator`'s Doc Gate handoff) or Direct (post-implementation, from `software-engineer`'s Direct Mode handoff).
- Hard-requires `Skill(skill: "superpowers:test-driven-development")` at the start of every run for the red/green/refactor methodology — this agent's own scope narrows to writing the actual test files and running them, never re-deriving TDD process rules itself. If the skill fails to load: `ABORT: The superpowers plugin is required and not installed.`

- [ ] **Step 3: Write the test-writing process**

- Chain mode: read `STATE.md` (`Worktree`, `Plan:`), `cd` into the worktree, read `docs/.plans/<slug>.md` for scope (the sole content source — never `docs/.tasks/`).
- Framework/command detection: inspect the repo itself first (existing test files, package-manifest test scripts, CI config). `.harness/standards.md`'s `## Testing` section overrides the inferred guess when present (`Glob`-check, skip silently if `.harness/` absent).
- Write failing tests per `superpowers:test-driven-development`'s red-phase discipline; confirm each fails for the right reason (missing implementation, not a test bug).
- Direct mode: same detection, tests written after implementation already exists.
- May emit an optional `HARNESS FLAG:` note in handoff output when observing a pattern not covered by any existing `.harness/` rule.
- Update `STATE.md` (`Phase: QA-RED`, `Handoff to: software-engineer`), append `HISTORY.md`.

- [ ] **Step 4: Write PHASE HANDOFF + EXIT & DERAILMENT HANDLING + START**

Hands off to `software-engineer`. EXIT row: `superpowers` plugin missing → ABORT, no fallback to improvised TDD.

- [ ] **Step 5: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 6: Commit**

```bash
git add agents/qa-engineer.md
git commit -m "Add qa-engineer agent

Writes tests in the coding chain, TDD red phase pre-implementation
(hard-requires superpowers:test-driven-development) or post-hoc in
Direct Mode.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: `software-engineer`

**Files:**
- Create: `agents/software-engineer.md`

**Interfaces:**
- Consumes: spec sections "Agent roster" (Direct Mode), "Two flows", "`.harness/` presence-gating"; `STATE.md` from Task 4/5's output shape.
- Produces: implementation + updated `STATE.md`/`HISTORY.md` (`Phase: IMPLEMENT`), read by Task 7 (`qa-auditor`).

- [ ] **Step 1: Write frontmatter**

```yaml
---
name: software-engineer
description: "Use this agent to implement code in the coding chain — stack-agnostic, no per-stack guide skills, following whatever conventions exist in the repo plus .harness/architecture.md and standards.md when present. Two modes: Chain (from qa-engineer's failing tests, TDD green phase, hands off to qa-auditor) and Direct (small bug-fix/decision requests with no task file, works on the current branch, no automated commit/PR — hands off to qa-engineer post-hoc).

<example>
Context: qa-engineer just wrote failing tests from the plan.
user: (chain handoff)
assistant: \"Invoking software-engineer to implement until the tests pass.\"
<commentary>
Chain flow — TDD green phase.
</commentary>
</example>

<example>
Context: intent-analyzer routed a small bug-fix with User Choice: proceed-directly.
user: \"Fix the off-by-one in the pagination helper\"
assistant: \"Small, single-scope fix — invoking software-engineer Direct Mode.\"
<commentary>
Direct flow, no task file, no task-orchestrator.
</commentary>
</example>"
tools: Read, Glob, Grep, Bash, Write, Edit
model: opus
color: red
---
```

- [ ] **Step 2: Write SYSTEM ROLE + WORKFLOW INTENT**

Content requirements:
- Stack-agnostic: no per-stack engineer-guide skills. Infer conventions from the repo itself.
- Two modes: Chain (from `qa-engineer`'s red-phase handoff) and Direct (from `intent-analyzer`'s `User Choice: proceed-directly` for `bug-fix`/`decision` task types — works on the current branch, no automated commit/PR, no task file).

- [ ] **Step 3: Write the implementation process**

- Chain mode: read `STATE.md` (`Worktree`, `Plan:`), `cd` into the worktree, read `docs/.plans/<slug>.md` for scope + `qa-engineer`'s failing tests. Load `.harness/architecture.md`+`standards.md` if present (`Glob`-check, skip silently if absent). Implement until tests pass.
- May raise a `TEST FIX REQUEST` back to `qa-engineer` if a specific test looks wrong (test bug, not implementation bug) rather than force-implementing to match a bad test.
- Direct mode: implement directly against the current branch/working tree, no worktree, no `STATE.md`.
- May emit an optional `HARNESS FLAG:` note on an uncovered pattern.
- Chain mode: update `STATE.md` (`Phase: IMPLEMENT`, `Handoff to: qa-auditor`), append `HISTORY.md`.

- [ ] **Step 4: Write PHASE HANDOFF + EXIT & DERAILMENT HANDLING + START**

Chain mode hands off to `qa-auditor`; Direct mode hands off to `qa-engineer` (post-hoc tests). EXIT row: `TEST FIX REQUEST` routing back to `qa-engineer`.

- [ ] **Step 5: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 6: Commit**

```bash
git add agents/software-engineer.md
git commit -m "Add software-engineer agent

Implements code in the coding chain, stack-agnostic. Chain mode (TDD
green phase, opus) and Direct mode (small ad hoc fixes, no task file).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: `qa-auditor`

**Files:**
- Create: `agents/qa-auditor.md`

**Interfaces:**
- Consumes: spec sections "Agent roster", "`.harness/` presence-gating", "Testing & verification" (coverage), "Two flows" (fix-cycle routing); `STATE.md` from Task 6's output shape.
- Produces: pass/fail verdict + updated `STATE.md`/`HISTORY.md` (`Phase: QA-AUDIT`), read by `documentation-auditor` (Doc Post-Impl, existing agent, no change) and Task 4's Publish Mode.

- [ ] **Step 1: Write frontmatter**

```yaml
---
name: qa-auditor
description: "Use this agent for the independent post-implementation re-verification in the coding chain, after software-engineer completes. Reruns scoped tests (task-affected files only), best-effort coverage report (never gated), code quality review, and conditional security/perf/dependency checks. Loads .harness/architecture.md + standards.md and raises a HIGH finding for task-introduced violations only (pre-existing violations untouched). Routes fix requests: test issues to qa-engineer, implementation bugs and HIGH+ findings to software-engineer.

<example>
Context: software-engineer just finished implementing, tests passing.
user: (chain handoff)
assistant: \"Invoking qa-auditor for the independent post-implementation review.\"
<commentary>
qa-auditor is the consolidated review step after software-engineer, before Publish.
</commentary>
</example>"
tools: Read, Glob, Grep, Bash, Write, Edit
model: sonnet
color: purple
---
```

- [ ] **Step 2: Write SYSTEM ROLE + WORKFLOW INTENT**

Content requirements:
- Independent re-verification, not the first test run — `qa-engineer` already wrote and `software-engineer` already passed the tests earlier.
- Chain-flow only, invoked after `software-engineer`'s Chain-mode handoff.

- [ ] **Step 3: Write the audit process**

- Read `STATE.md` (`Worktree`), `cd` into the worktree.
- Always run: scoped tests (task-affected files only, not full suite), best-effort coverage report (whatever coverage tool is detected in the repo, skip silently if none — never blocks, report the number only), code quality review.
- Conditionally run: security review (tag or `software-engineer`-flagged concern), performance review (same), dependency audit (new package installation flagged).
- Load `.harness/architecture.md`+`standards.md` if present. Raise a HIGH finding — routed to `software-engineer` — for any task-*introduced* violation only; leave pre-existing violations untouched.
- Fix-cycle routing (carried over from maestro unchanged): test issues → `qa-engineer`; implementation bugs or HIGH+ security/perf/dependency findings → `software-engineer`.
- May emit an optional `HARNESS FLAG:` note.
- On a clean pass: update `STATE.md` (`Phase: QA-AUDIT`, `Handoff to: documentation-auditor` for Doc Post-Impl), append `HISTORY.md`.

- [ ] **Step 4: Write PHASE HANDOFF + EXIT & DERAILMENT HANDLING + START**

Clean pass hands off to `documentation-auditor` (Doc Post-Impl, existing agent — this task does not modify `agents/documentation-auditor.md`). Fix-cycle loops route back into the chain, appending fresh `HISTORY.md` lines each time.

- [ ] **Step 5: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 6: Commit**

```bash
git add agents/qa-auditor.md
git commit -m "Add qa-auditor agent

Independent post-implementation re-verification: scoped tests,
best-effort coverage, code quality, conditional security/perf/
dependency checks. Fix-cycle routing to qa-engineer/software-engineer.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: `/cairn-run-task` command

**Files:**
- Create: `commands/cairn-run-task.md`

**Interfaces:**
- Consumes: spec sections "New command: `/cairn-run-task`", "Unattended execution"; `docs/.tasks/TRACKER.md` (Task 3's output) and `docs/.tasks/<slug>/STATE.md` (Task 4's output) as the resolution targets.
- Produces: nothing new on disk — this command's job is to resolve input and invoke `task-orchestrator` (Task 4).

- [ ] **Step 1: Read an existing command for structural convention**

Read `commands/cairn-doctor.md` in full before writing — mirror its frontmatter and instruction-prose shape (commands are natural-language instructions, not code, per this repo's own `CLAUDE.md`).

- [ ] **Step 2: Write the command**

Content requirements, verbatim from spec "New command: `/cairn-run-task`":

```markdown
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
```

- [ ] **Step 3: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 4: Headless smoke test**

Per this repo's `CLAUDE.md` → "Testing a command end-to-end":

```bash
mkdir -p /tmp/cairn-runtask-test/docs/.tasks && cd /tmp/cairn-runtask-test && git init -q
cat > docs/.tasks/TRACKER.md <<'EOF'
| Slug | Scope | Status | Ticket | Task File |
|---|---|---|---|---|
| user-login | User can log in | Idea | — | — |
EOF
claude -p "/cairn:cairn-run-task user-login" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: command resolves the `user-login` slug against `TRACKER.md`, finds no `docs/.plans/*-user-login.md` yet, and reports that `task-orchestrator`'s hard-require would fail — a plan must exist first (spec "Plan Dedup"). Confirms input resolution works even in the not-ready-yet case; a full green-path smoke test needs a real plan file and is covered by Tasks 4–7's own verification instead.

- [ ] **Step 5: Commit**

```bash
git add commands/cairn-run-task.md
git commit -m "Add /cairn-run-task command

Direct entry point for Chain-flow work — resolves a slug, path, or
ticket link to a task folder and invokes task-orchestrator.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: `CLAUDE.md` updates

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: all of Tasks 1–8's outputs (this task documents them); existing `CLAUDE.md` "Architecture" section's bullet-per-agent format and "End-to-end sequence" convention for the writer trio.
- Produces: the discoverability layer — nothing downstream in this plan depends on it, but it's how a future session (or user) finds these agents at all.

- [ ] **Step 1: Add roster bullets**

Insert 6 new bullets into the "Architecture" section, matching the existing one-paragraph-per-agent style (see `documentation-auditor`'s and `codebase-auditor`'s existing bullets for length/tone). One bullet each for `project-manager`, `harness-engineer`, `task-orchestrator`, `qa-engineer`, `software-engineer`, `qa-auditor` — condensed summaries pointing at behavior, not the full spec re-pasted. Cross-reference `docs/.specs/2026-08-15-coding-chain-port-design.md` for full detail, same as existing bullets reference their own source agents.

- [ ] **Step 2: Add the coding-chain sequence section**

New subsection (parallel to the existing "End-to-end sequence" for the writer trio): document Direct flow, Chain flow (including the two Documentation Gate invocations), and the two entry points (`/cairn-run-task` and natural-language routing via `intent-analyzer`'s existing `ROUTING DECISION: coding` + `User Choice` fields — explicitly note `intent-analyzer` itself is unmodified, this is Claude's own documented judgment call per the spec's "Integration with existing cairn routing" section).

- [ ] **Step 3: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "Document coding-chain agents and sequence in CLAUDE.md

Adds roster bullets for the 6 new agents and a Direct/Chain flow
sequence section, same pattern as the existing writer-trio docs.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: Version bump + final validation

**Files:**
- Modify: `.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: repo's `CLAUDE.md` → "Versioning" (minor bump for new agents/commands).
- Produces: nothing consumed downstream — this is the plan's closing task.

- [ ] **Step 1: Bump the version**

Edit `.claude-plugin/plugin.json`: `"version": "0.9.0"` → `"version": "0.10.0"` (minor bump — new agents/commands, per this repo's own Versioning rule).

- [ ] **Step 2: Full plugin validation**

Run: `claude plugin validate . --strict`
Expected: passes clean — every agent/command/skill file from Tasks 1–9 present and well-formed.

- [ ] **Step 3: Full test suite**

Run: `pytest tests/ -v -s`
Expected: `tests/test_usage_dashboard.py`'s deterministic subset stays green (unaffected by this port). `tests/test_intent_routing.py`'s eval suite stays at or above `MIN_PASS` — this port makes zero changes to `agents/intent-analyzer.md`, so no regression is expected there; a flip on a single case is normal model variance per this repo's own testing guidance, not a blocker.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "Bump to 0.10.0 for the coding-chain port

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
