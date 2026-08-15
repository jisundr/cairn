# Coding Chain Environment Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the coding chain a preflight check that catches a "works on my machine" environment before a task starts — a 4th `.harness/` convention file (`environment.md`, typed machine-checkable rules) authored by `harness-engineer`, executed by a new `task-orchestrator` Plan Mode step before branch/worktree creation.

**Architecture:** No new agent. `harness-engineer` gains a 4th file (`environment.md`) in its existing Generate/Update modes, using the same evidence-derivation + `AskUserQuestion` confirm-gate pattern as `architecture.md`/`standards.md`/`workflow.md`, but with a typed check vocabulary (`tool-version`, `port-open`, `env-var-set`, escape-hatch `command`) instead of prose rules. `task-orchestrator` gains a new Plan Mode Step 4.5 — Environment Preflight — between the existing `.harness/workflow.md` load (Step 4) and branch/worktree creation (Step 5): loads `.harness/environment.md` if present, runs each check, and gates on any failed `[blocking]` check the same way Step 7's feasibility assessment already gates (`AskUserQuestion` Attended / `HANDOFF NEEDED` Unattended).

**Tech Stack:** Markdown agent/skill files (Claude Code plugin convention — no compiled code). Verification is `claude plugin validate . --strict` plus headless `claude -p` smoke tests against scratch directories, same approach as the original coding-chain port (`docs/.plans/2026-08-15-coding-chain-port.md`).

**Spec:** `docs/.specs/2026-08-15-coding-chain-environment-preflight-design.md` — the plan argues from the spec, so the spec travels with it; executors read both. Every task below cites the exact spec section(s) it implements.

## Global Constraints

- `.harness/environment.md` check kinds (spec "`.harness/environment.md` format"): `tool-version` (`tool`, `min`), `port-open` (`host`, `port`), `env-var-set` (`name`), `command` (`cmd`, `expect-exit` — the only kind that runs raw shell). Every check carries `[blocking]` or `[warning]` plus an evidence note.
- Same ~40-line cap per `.harness/` file as the other three (repo-wide `harness-engineer` convention).
- A check whose command can't execute at all counts as **failed**, not skipped/`UNVERIFIED` (spec "Scope decision" table — deliberate divergence from `codebase-auditor`'s best-effort-skip precedent).
- No code comments unless the WHY is non-obvious (repo-wide convention, `CLAUDE.md`).
- Every changed agent/skill file requires a `.claude-plugin/plugin.json` version bump before this plan's final commit (repo's `CLAUDE.md` → "Versioning" — minor bump, new capability on existing agents).
- `claude plugin validate . --strict` must pass after every task that edits an agent/skill file — run it as each task's verification step, not just at the end.

---

### Task 1: `coding-chain-shared` — environment template + SKILL.md

**Files:**
- Create: `skills/coding-chain-shared/assets/harness/environment.template.md`
- Modify: `skills/coding-chain-shared/SKILL.md`

**Interfaces:**
- Consumes: spec section "`.harness/environment.md` format"; existing `skills/coding-chain-shared/assets/harness/{architecture,standards,workflow}.template.md` for header-line/section-heading convention.
- Produces: `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/harness/environment.template.md` — the seed path Task 2's `harness-engineer` edits read by path (never renamed).

- [ ] **Step 1: Write `environment.template.md`**

```markdown
> Refines coding-chain behavior. Blocking checks gate task-orchestrator Plan Mode.

# Environment Checks

## Toolchain
<!-- no convention observed -->

## Services
<!-- no convention observed -->

## Env vars
<!-- no convention observed -->

## Other checks
<!-- no convention observed -->
```

- [ ] **Step 2: Add the template to `SKILL.md`'s bundle list**

Edit `skills/coding-chain-shared/SKILL.md`. Replace:

```markdown
- `assets/harness/architecture.template.md`, `standards.template.md`, `workflow.template.md` — seed shape for `.harness/*.md` (`harness-engineer`, Generate mode)
```

With:

```markdown
- `assets/harness/architecture.template.md`, `standards.template.md`, `workflow.template.md`, `environment.template.md` — seed shape for `.harness/*.md` (`harness-engineer`, Generate mode). `environment.md` differs from the other three: its rules are a typed, machine-checkable vocabulary (`tool-version` / `port-open` / `env-var-set` / `command`) executed by `task-orchestrator`'s Environment Preflight step, not prose guidance other agents read and follow — each rule also carries a `[blocking]`/`[warning]` severity tag the other three files don't have.
```

- [ ] **Step 3: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 4: Commit**

```bash
git add skills/coding-chain-shared/assets/harness/environment.template.md skills/coding-chain-shared/SKILL.md
git commit -m "Add environment.md template to coding-chain-shared

Seed shape for harness-engineer's new 4th .harness/ file — typed,
machine-checkable environment rules (tool versions, service
reachability, env vars) distinct from the other three files' prose
conventions.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `harness-engineer` — 4th file support

**Files:**
- Modify: `agents/harness-engineer.md`

**Interfaces:**
- Consumes: spec section "`harness-engineer` changes"; Task 1's `environment.template.md`.
- Produces: `.harness/environment.md` (read by Task 3's `task-orchestrator` Step 4.5).

- [ ] **Step 1: Update the frontmatter description**

Edit `agents/harness-engineer.md`. Replace:

```
description: "Use this agent to generate or update the .harness/ convention files (architecture.md, standards.md, workflow.md) for the current codebase — deriving draft rules from the project's own observed conventions instead of hand-authoring them from a blank template. On a fresh/near-empty codebase, falls back to pre-filling from docs/architecture/architecture-spec.md when present, then interviewing for the rest, rather than writing evidence-free files. .harness/ is committed (not gitignored) so every clone/submodule gets the standard setup automatically.
```

With:

```
description: "Use this agent to generate or update the .harness/ convention files (architecture.md, standards.md, workflow.md, environment.md) for the current codebase — deriving draft rules from the project's own observed conventions instead of hand-authoring them from a blank template. environment.md is a typed, machine-checkable vocabulary (tool versions, service reachability, env var presence) that task-orchestrator's Environment Preflight step executes before a task starts, distinct from the other three files' prose guidance. On a fresh/near-empty codebase, falls back to pre-filling from docs/architecture/architecture-spec.md when present, then interviewing for the rest, rather than writing evidence-free files. .harness/ is committed (not gitignored) so every clone/submodule gets the standard setup automatically.
```

- [ ] **Step 2: Update SYSTEM ROLE + scope**

Edit `agents/harness-engineer.md`. Replace:

```markdown
You are the **Harness Engineer** — you generate and maintain `.harness/architecture.md`, `.harness/standards.md`, and `.harness/workflow.md` at the project root: the three convention files the coding-chain agents (`task-orchestrator`, `software-engineer`, `qa-engineer`, `qa-auditor`) load to follow this codebase's own rules instead of generic defaults.

Your scope is **exclusively** those three files at `.harness/` (project root). You never touch application source, never touch `.claude/`-equivalent cairn files, and never write a rule that isn't grounded in either observed evidence or an explicit answer the user gave you.
```

With:

```markdown
You are the **Harness Engineer** — you generate and maintain `.harness/architecture.md`, `.harness/standards.md`, `.harness/workflow.md`, and `.harness/environment.md` at the project root: the four convention files the coding-chain agents (`task-orchestrator`, `software-engineer`, `qa-engineer`, `qa-auditor`) load to follow this codebase's own rules instead of generic defaults. The first three are prose guidance other agents read and follow; `environment.md` is different — a typed, machine-checkable vocabulary `task-orchestrator` executes directly (see PROCESS below), not prose for an LLM to interpret.

Your scope is **exclusively** those four files at `.harness/` (project root). You never touch application source, never touch `.claude/`-equivalent cairn files, and never write a rule that isn't grounded in either observed evidence or an explicit answer the user gave you.
```

- [ ] **Step 3: Update WORKFLOW INTENT**

Edit `agents/harness-engineer.md`. Replace:

```markdown
- **Generate** — `.harness/` doesn't exist yet. Observes the codebase, derives draft rules, confirms them with the user, writes the three files. On a genuinely fresh/near-empty codebase (no source beyond scaffolding), this instead pre-fills from `docs/architecture/architecture-spec.md` (and related design docs) when present, then interviews for whatever isn't covered — never writes near-blank files full of `<!-- no convention observed -->` markers when evidence exists elsewhere.
```

With:

```markdown
- **Generate** — `.harness/` doesn't exist yet. Observes the codebase, derives draft rules, confirms them with the user, writes the four files. On a genuinely fresh/near-empty codebase (no source beyond scaffolding), this instead pre-fills from `docs/architecture/architecture-spec.md` (and related design docs) when present, then interviews for whatever isn't covered — never writes near-blank files full of `<!-- no convention observed -->` markers when evidence exists elsewhere. `environment.md` has no architecture-spec pre-fill source (a spec doesn't declare exact tool-version floors or port numbers) — on a fresh codebase it always goes through the interview path (Step 4), never pre-fill.
```

- [ ] **Step 4: Add a HARD REQUIREMENTS bullet for severity tagging**

Edit `agents/harness-engineer.md`. Replace:

```markdown
- ALWAYS enforce a ~40-line cap per file. If confirmed rules would exceed it, drop the weakest-evidence rules first (lowest evidence count, or — for fresh-codebase mode — least load-bearing) and say so in the completion block.
```

With:

```markdown
- ALWAYS enforce a ~40-line cap per file. If confirmed rules would exceed it, drop the weakest-evidence rules first (lowest evidence count, or — for fresh-codebase mode — least load-bearing) and say so in the completion block.
- ALWAYS confirm each `environment.md` check's severity (`[blocking]`/`[warning]`) as part of its confirm/edit/drop decision at the `AskUserQuestion` gate — never auto-assigned, and never left unset.
```

- [ ] **Step 5: Extend Step 3 (standard observation path) with Environment**

Edit `agents/harness-engineer.md`. Replace:

```markdown
- **Architecture**: stack (manifest files — `package.json`, `pyproject.toml`, `go.mod`, etc.), layering (directory structure, module boundaries), data storage patterns (`Grep` for ORM/DB client usage, migration directories).
- **Standards**: naming conventions (`Grep` sample identifiers across files), error-handling patterns (`Grep` for try/catch, error types, result wrappers), test placement (`Glob` for test file locations relative to source), logging patterns (`Grep` for logging calls/libraries).
- **Workflow**: `git log` for commit-message conventions, `git branch -a` / recent branch names for branch-naming patterns, presence of CI config or PR templates for gate conventions.

For each candidate rule, track an evidence count (number of files/commits/instances observed). Present the full set via `AskUserQuestion` for a per-rule confirm/edit/drop decision — batch related rules per file (architecture.md's rules together, etc.) rather than one question per rule where reasonable, but never skip presenting any rule. Where observations conflict, present the conflict itself as the choice, not a resolved pick.

Write confirmed rules into the three files, seeded from `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/harness/{architecture,standards,workflow}.template.md` (preserving each template's header line and section headings). `${CLAUDE_PLUGIN_ROOT}` is the plugin's own install location; a bare `skills/...` path would resolve against the consuming project's cwd and fail.

If a template can't be read for any reason, don't improvise a shape — fall back to this known structure, which is what the templates contain:

```
architecture.template.md  > Refines coding-chain behavior. Cannot skip chain agents or verification.
                          # Architecture Rules  →  ## Stack · ## Layering · ## Boundaries · ## Data
standards.template.md     > Refines coding-chain behavior. Cannot skip chain agents or verification.
                          # Coding Standards    →  ## Naming · ## Error handling · ## Testing · ## Logging
workflow.template.md      > Refines coding-chain behavior. Gates are additive only.
                          # Workflow Rules      →  ## Branching · ## Commits / MR · ## Gates (additive)
```

Each written rule line ends with its evidence count, e.g. `- Files under src/ use PascalCase for component names (12 files observed).` Sections with no confirmed rule keep `<!-- no convention observed -->`. Enforce the ~40-line cap per file (Hard Requirements).
```

With:

```markdown
- **Architecture**: stack (manifest files — `package.json`, `pyproject.toml`, `go.mod`, etc.), layering (directory structure, module boundaries), data storage patterns (`Grep` for ORM/DB client usage, migration directories).
- **Standards**: naming conventions (`Grep` sample identifiers across files), error-handling patterns (`Grep` for try/catch, error types, result wrappers), test placement (`Glob` for test file locations relative to source), logging patterns (`Grep` for logging calls/libraries).
- **Workflow**: `git log` for commit-message conventions, `git branch -a` / recent branch names for branch-naming patterns, presence of CI config or PR templates for gate conventions.
- **Environment**: toolchain candidates from `package.json` `engines`, `.nvmrc`, `.python-version`, `.tool-versions`, or CI config's declared runtime versions (→ `tool-version` checks); service candidates from `docker-compose.yml` service ports (→ `port-open` checks); env-var candidates from `.env.example` key names only, never values (→ `env-var-set` checks). No `command`-kind candidates are auto-derived — that kind is proposed only when the user explicitly asks for a check the other three kinds can't express.

For each candidate rule, track an evidence count (number of files/commits/instances observed) — for `environment.md` candidates, the evidence is the source file/field cited, e.g. `package.json engines.node`, following the same citation-not-count shape the spec shows. Present the full set via `AskUserQuestion` for a per-rule confirm/edit/drop decision — batch related rules per file (architecture.md's rules together, etc.) rather than one question per rule where reasonable, but never skip presenting any rule. For `environment.md` candidates specifically, the same question also confirms severity (`[blocking]`/`[warning]`, Hard Requirements). Where observations conflict, present the conflict itself as the choice, not a resolved pick.

Write confirmed rules into the four files, seeded from `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/harness/{architecture,standards,workflow,environment}.template.md` (preserving each template's header line and section headings). `${CLAUDE_PLUGIN_ROOT}` is the plugin's own install location; a bare `skills/...` path would resolve against the consuming project's cwd and fail.

If a template can't be read for any reason, don't improvise a shape — fall back to this known structure, which is what the templates contain:

```
architecture.template.md  > Refines coding-chain behavior. Cannot skip chain agents or verification.
                          # Architecture Rules  →  ## Stack · ## Layering · ## Boundaries · ## Data
standards.template.md     > Refines coding-chain behavior. Cannot skip chain agents or verification.
                          # Coding Standards    →  ## Naming · ## Error handling · ## Testing · ## Logging
workflow.template.md      > Refines coding-chain behavior. Gates are additive only.
                          # Workflow Rules      →  ## Branching · ## Commits / MR · ## Gates (additive)
environment.template.md   > Refines coding-chain behavior. Blocking checks gate task-orchestrator Plan Mode.
                          # Environment Checks  →  ## Toolchain · ## Services · ## Env vars · ## Other checks
```

Each written architecture/standards/workflow rule line ends with its evidence count, e.g. `- Files under src/ use PascalCase for component names (12 files observed).` Each written `environment.md` check line carries its kind, fields, severity, and evidence note instead, e.g. `- [blocking] node >= 20.0.0 — tool-version: node, min 20.0.0 — evidence: package.json engines.node`. Sections with no confirmed rule keep `<!-- no convention observed -->`. Enforce the ~40-line cap per file (Hard Requirements).
```

- [ ] **Step 6: Extend Step 4 (fresh-codebase path) to cover environment.md**

Edit `agents/harness-engineer.md`. Replace:

```markdown
2. **Interview for the rest.** Whatever isn't covered by those upstream docs — style conventions, test placement, workflow/branch/commit format, gates — goes through `AskUserQuestion` directly, asked as plain preference questions (there's no codebase to observe yet). Tag every such line **`user-specified`**, e.g. `- Branch names: feature/<slug> (user-specified).`
```

With:

```markdown
2. **Interview for the rest.** Whatever isn't covered by those upstream docs — style conventions, test placement, workflow/branch/commit format, gates, and (always, since an architecture spec doesn't declare exact tool-version floors or port numbers) any `environment.md` checks — goes through `AskUserQuestion` directly, asked as plain preference questions (there's no codebase to observe yet). Tag every such line **`user-specified`**, e.g. `- Branch names: feature/<slug> (user-specified).` For `environment.md` specifically, only propose a check the user actually states a requirement for — an empty `environment.md` (all sections `<!-- no convention observed -->`) is a valid outcome of this interview, not a failure to fix.
```

- [ ] **Step 7: Update the PHASE HANDOFF completion block**

Edit `agents/harness-engineer.md`. Replace:

```markdown
Mode       → [Generate | Generate (fresh-codebase interview) | Update]
Written to → .harness/architecture.md, .harness/standards.md, .harness/workflow.md
Rules      → observed: N  from-architecture-spec: N  user-specified: N
```

With:

```markdown
Mode       → [Generate | Generate (fresh-codebase interview) | Update]
Written to → .harness/architecture.md, .harness/standards.md, .harness/workflow.md, .harness/environment.md
Rules      → observed: N  from-architecture-spec: N  user-specified: N
Environment→ blocking: N  warning: N
```

- [ ] **Step 8: Update EXIT & DERAILMENT HANDLING table row**

Edit `agents/harness-engineer.md`. Replace:

```markdown
| `.harness/` exists but is missing one of the three files | Treat as Update mode for the files present; treat the missing file as Generate mode (seeded from its template) for that file only. |
```

With:

```markdown
| `.harness/` exists but is missing one of the four files | Treat as Update mode for the files present; treat the missing file as Generate mode (seeded from its template) for that file only. |
```

- [ ] **Step 9: Update START section**

Edit `agents/harness-engineer.md`. Replace:

```markdown
4. `Write`/`Edit` the confirmed rules into `.harness/architecture.md`, `.harness/standards.md`, `.harness/workflow.md`, enforcing the ~40-line cap per file.
```

With:

```markdown
4. `Write`/`Edit` the confirmed rules into `.harness/architecture.md`, `.harness/standards.md`, `.harness/workflow.md`, `.harness/environment.md`, enforcing the ~40-line cap per file.
```

- [ ] **Step 10: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 11: Headless smoke test**

```bash
mkdir -p /tmp/cairn-env-harness-test && cd /tmp/cairn-env-harness-test && git init -q
claude -p "generate harness rules for this repo" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: agent detects the empty repo, runs the fresh-codebase interview path, and `.harness/environment.md` is written (likely all `<!-- no convention observed -->` sections, since a bare `git init` scratch dir has nothing to state a requirement about — that's a valid outcome per Step 6). Inspect `/tmp/cairn-env-harness-test/.harness/environment.md` directly to confirm — don't just trust the reported output.

- [ ] **Step 12: Commit**

```bash
git add agents/harness-engineer.md
git commit -m "Extend harness-engineer with a 4th file: environment.md

Typed, machine-checkable environment rules (tool versions, service
reachability, env var presence) with a blocking/warning severity tag
per check — distinct from the other three files' prose conventions.
Same evidence-derivation + AskUserQuestion confirm-gate pattern.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `task-orchestrator` — Environment Preflight step

**Files:**
- Modify: `agents/task-orchestrator.md`

**Interfaces:**
- Consumes: spec section "`task-orchestrator` changes"; Task 2's `.harness/environment.md` (read at runtime, not a build-time dependency).
- Produces: gates Step 5 (branch/worktree creation) — no other task in this plan depends on this one's output directly, it's the plan's terminal behavioral change.

- [ ] **Step 1: Update the frontmatter description**

Edit `agents/task-orchestrator.md`. Replace:

```
description: "Use this agent to run the coding-chain's Plan and Publish steps. Plan Mode: hard-requires an existing docs/.plans/<slug>.md (reads it as the plan, never re-authors it), creates docs/.tasks/YYYY-MM-DD-<slug>/, runs a qa-engineer+software-engineer feasibility assessment, creates the branch/worktree via superpowers:using-git-worktrees. Publish Mode: consolidated commit, PR/MR via gh/glab, UAT checklist, surfaces harness+doc-drift flags, closes the ticket and deletes the local plan draft once closure is observed. First and last agent in the chain.
```

With:

```
description: "Use this agent to run the coding-chain's Plan and Publish steps. Plan Mode: hard-requires an existing docs/.plans/<slug>.md (reads it as the plan, never re-authors it), creates docs/.tasks/YYYY-MM-DD-<slug>/, runs an Environment Preflight against .harness/environment.md when present (gates branch/worktree creation on any failed blocking check), runs a qa-engineer+software-engineer feasibility assessment, creates the branch/worktree via superpowers:using-git-worktrees. Publish Mode: consolidated commit, PR/MR via gh/glab, UAT checklist, surfaces harness+doc-drift flags, closes the ticket and deletes the local plan draft once closure is observed. First and last agent in the chain.
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet for check ordering**

Edit `agents/task-orchestrator.md`. Replace:

```markdown
- ALWAYS create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` — never reimplement worktree/branch mechanics with raw `git` commands.
```

With:

```markdown
- ALWAYS create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` — never reimplement worktree/branch mechanics with raw `git` commands.
- NEVER create the branch/worktree (Step 5) before Environment Preflight (Step 4.5) resolves — a failed `[blocking]` check must be answered (fix/retry or proceed anyway) before anything gets created, so a rejected environment never leaves a half-set-up task behind.
```

- [ ] **Step 3: Insert the new Step 4.5, between Step 4 and Step 5**

Edit `agents/task-orchestrator.md`. Replace:

```markdown
### Step 5 — Branch/worktree creation

Invoke `Skill(skill: "superpowers:using-git-worktrees")` — hard-required, this agent never reimplements worktree mechanics itself. Branch name: `.harness/workflow.md`'s `## Branching` convention if loaded in Step 4, else the default `<task-type>/<slug>` (`feature/<slug>` or `refactor/<slug>`, matching the plan's declared task type). Scoped to the submodule root if Step 3 detected one.
```

With:

```markdown
### Step 4.5 — Environment Preflight

`Glob(.harness/environment.md)` — absent → skip silently, no note (same optionality as every other `.harness/` file). Present → `Read` it and run each declared check via its typed interpreter:

- `tool-version` — run `<tool> --version`, parse and compare against `min`.
- `port-open` — TCP connect attempt to `host:port`, no payload sent.
- `env-var-set` — presence check only via `Bash`; never read, log, or echo the value.
- `command` — run the literal `cmd`, compare its exit code against `expect-exit`. The only kind that executes arbitrary shell from the file — everything else is interpreted, not executed.

A check whose command can't run at all (missing binary, unreachable host, whatever the cause) counts as **failed** — same treatment as an actual value mismatch, not a silent skip.

Any failed `[blocking]` check → `AskUserQuestion` (Attended) / `STATE.md` `Phase: HANDOFF NEEDED` (Unattended): fix the environment and retry, or proceed anyway and accept the risk — same shape as Step 7's feasibility-blocker gate. Failed `[warning]` checks are noted only, never pause. Hold the full per-check pass/fail tally for Step 9's `STATE.md` write.

### Step 5 — Branch/worktree creation

Invoke `Skill(skill: "superpowers:using-git-worktrees")` — hard-required, this agent never reimplements worktree mechanics itself. Branch name: `.harness/workflow.md`'s `## Branching` convention if loaded in Step 4, else the default `<task-type>/<slug>` (`feature/<slug>` or `refactor/<slug>`, matching the plan's declared task type). Scoped to the submodule root if Step 3 detected one.
```

- [ ] **Step 4: Fold preflight results into the Step 9 `STATE.md` write**

Edit `agents/task-orchestrator.md`. Replace:

```markdown
Write `STATE.md`: `Mode` (from Step 8), `Phase: PLAN`, `Handoff to: documentation-auditor (Doc Gate)` — matching Step 11 below, not `qa-engineer` directly, so a `/cairn-run-task` resume never skips the Doc Gate — `Status`, `Plan:` pointer (the file found in Step 1), `Ticket:` (from `docs/.tasks/TRACKER.md` if a row for this slug carries one — else `none`), `Worktree`, `Branch` (from Step 5), `Key info` (feasibility notes from Step 7, `.harness/` suggestion flag from Step 6), `Harness flags: none`. Append one summarized line to `HISTORY.md`.
```

With:

```markdown
Write `STATE.md`: `Mode` (from Step 8), `Phase: PLAN`, `Handoff to: documentation-auditor (Doc Gate)` — matching Step 11 below, not `qa-engineer` directly, so a `/cairn-run-task` resume never skips the Doc Gate — `Status`, `Plan:` pointer (the file found in Step 1), `Ticket:` (from `docs/.tasks/TRACKER.md` if a row for this slug carries one — else `none`), `Worktree`, `Branch` (from Step 5), `Key info` (environment preflight tally from Step 4.5, feasibility notes from Step 7, `.harness/` suggestion flag from Step 6), `Harness flags: none`. Append one summarized line to `HISTORY.md`.
```

- [ ] **Step 5: Add the Environment line to the PHASE HANDOFF completion block**

Edit `agents/task-orchestrator.md`. Replace:

```markdown
Task        → docs/.tasks/YYYY-MM-DD-<slug>/
Plan        → docs/.plans/<file>.md
Worktree    → <path>
Branch      → <branch-name>
Feasibility → qa-engineer: [ok | flag]  software-engineer: [ok | flag]
Ticket      → <url, or none> [→ In Progress]
```

With:

```markdown
Task        → docs/.tasks/YYYY-MM-DD-<slug>/
Plan        → docs/.plans/<file>.md
Worktree    → <path>
Branch      → <branch-name>
Environment → [not configured | N/N checks passed]
Feasibility → qa-engineer: [ok | flag]  software-engineer: [ok | flag]
Ticket      → <url, or none> [→ In Progress]
```

- [ ] **Step 6: Add an EXIT & DERAILMENT HANDLING row**

Edit `agents/task-orchestrator.md`. Replace:

```markdown
| `qa-engineer`/`software-engineer` feasibility assessment flags the plan as not implementable as written | `AskUserQuestion` (Attended) / `HANDOFF NEEDED` (Unattended): revise the plan first, or proceed anyway and let the chain surface it again downstream. |
```

With:

```markdown
| `qa-engineer`/`software-engineer` feasibility assessment flags the plan as not implementable as written | `AskUserQuestion` (Attended) / `HANDOFF NEEDED` (Unattended): revise the plan first, or proceed anyway and let the chain surface it again downstream. |
| A `[blocking]` check in `.harness/environment.md` fails (including a check whose command can't run at all) | `AskUserQuestion` (Attended) / `HANDOFF NEEDED` (Unattended): fix the environment and retry, or proceed anyway and accept the risk. Branch/worktree creation (Step 5) waits until this resolves. |
```

- [ ] **Step 7: Update the START section's Plan Mode summary**

Edit `agents/task-orchestrator.md`. Replace:

```markdown
3. Detect submodule scope (Step 3); load `.harness/workflow.md` if present (Step 4).
4. Create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` (Step 5); suggest `harness-engineer` if `.harness/` is absent entirely (Step 6).
```

With:

```markdown
3. Detect submodule scope (Step 3); load `.harness/workflow.md` if present (Step 4).
4. Run the Environment Preflight against `.harness/environment.md` if present, gating on any failed `[blocking]` check (Step 4.5).
5. Create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` (Step 5); suggest `harness-engineer` if `.harness/` is absent entirely (Step 6).
```

(Renumber the remaining Plan Mode summary bullets that follow, +1 each, so the list stays in order.)

- [ ] **Step 8: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 9: Manual end-to-end scratch test**

Per this repo's "Testing a command end-to-end" convention (`CLAUDE.md`) — this step is agent-behavior verification, not a pytest run:

```bash
mkdir -p /tmp/cairn-env-preflight-test && cd /tmp/cairn-env-preflight-test && git init -q
mkdir -p .harness docs/.plans
cat > .harness/environment.md <<'EOF'
> Refines coding-chain behavior. Blocking checks gate task-orchestrator Plan Mode.

# Environment Checks

## Toolchain
- [blocking] a-tool-that-does-not-exist >= 1.0.0 — tool-version: a-tool-that-does-not-exist, min 1.0.0 — evidence: manual test fixture
EOF
cat > docs/.plans/2026-08-15-scratch-task.md <<'EOF'
# Scratch Task Plan
Trivial plan file, only needed to satisfy task-orchestrator's Upstream Existence Check.
EOF
git add -A && git commit -q -m "scratch fixture"
claude -p "Run task-orchestrator Plan Mode for the scratch-task task" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: the agent reaches Step 4.5, the `tool-version` check fails (binary doesn't exist), and — since it's `[blocking]` — the run stops at an `AskUserQuestion`-equivalent pause rather than proceeding to Step 5. Inspect `docs/.tasks/*/STATE.md` in the scratch dir afterward: no `Worktree`/`Branch` should be set yet (branch/worktree creation never ran), and the failed check should be visible in `Key info`. Don't just trust the reported output — inspect the actual file.

- [ ] **Step 10: Commit**

```bash
git add agents/task-orchestrator.md
git commit -m "Add Environment Preflight (Step 4.5) to task-orchestrator Plan Mode

Loads .harness/environment.md when present and runs its typed checks
before branch/worktree creation. A failed [blocking] check gates the
chain the same way Step 7's feasibility assessment already does.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `CLAUDE.md` documentation + version bump

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: Tasks 1–3's outputs (this task documents them); existing `CLAUDE.md` bullet style for `harness-engineer`/`task-orchestrator`/`coding-chain-shared`.
- Produces: the discoverability layer plus the version bump `log-version.sh` stamps into `.cairn/version-log.jsonl` for consuming projects.

- [ ] **Step 1: Update the `coding-chain-shared` bullet**

Edit `CLAUDE.md`. Replace:

```markdown
**`coding-chain-shared` (skills/)** — not an invoked skill despite living under `skills/`: it's the shared **asset bundle** for the six coding-chain agents below. `assets/TRACKER.template.md`, `assets/task/{STATE,HISTORY,UAT}.template.md`, and `assets/harness/{architecture,standards,workflow}.template.md` are the seed shapes for every file the chain creates, plus SKILL.md documenting the canonical `TRACKER.md` Status vocabulary, `STATE.md` Phase vocabulary, and the `Key info` (overwritten each phase) vs. `Harness flags` (append-only, accumulates to Publish) split. No agent calls `Skill(skill: "coding-chain-shared")` — `harness-engineer` and `project-manager` don't even carry `Skill` in `tools:`. Each agent `Read`s the one template it needs by path at the moment it seeds a file, always via `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/...`; a bare `skills/...` path would resolve against the *consuming* project's cwd, not the plugin's install location, and fail.
```

With:

```markdown
**`coding-chain-shared` (skills/)** — not an invoked skill despite living under `skills/`: it's the shared **asset bundle** for the six coding-chain agents below. `assets/TRACKER.template.md`, `assets/task/{STATE,HISTORY,UAT}.template.md`, and `assets/harness/{architecture,standards,workflow,environment}.template.md` are the seed shapes for every file the chain creates, plus SKILL.md documenting the canonical `TRACKER.md` Status vocabulary, `STATE.md` Phase vocabulary, and the `Key info` (overwritten each phase) vs. `Harness flags` (append-only, accumulates to Publish) split. No agent calls `Skill(skill: "coding-chain-shared")` — `harness-engineer` and `project-manager` don't even carry `Skill` in `tools:`. Each agent `Read`s the one template it needs by path at the moment it seeds a file, always via `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/...`; a bare `skills/...` path would resolve against the *consuming* project's cwd, not the plugin's install location, and fail.
```

- [ ] **Step 2: Update the `harness-engineer` bullet**

Edit `CLAUDE.md`. Replace:

```markdown
**`harness-engineer` (agents/)** — generates/maintains `.harness/architecture.md`, `.harness/standards.md`, `.harness/workflow.md` at the consuming project's root: the convention files `task-orchestrator`/`software-engineer`/`qa-engineer`/`qa-auditor` load to follow a codebase's own observed rules instead of generic defaults. Generate mode derives draft rules from the codebase itself (or, on a genuinely fresh/near-empty repo, pre-fills from `docs/architecture/architecture-spec.md` when present and interviews for the rest — never invents a rule with no observed basis); Update mode diffs current conventions against what's codified and proposes amendments through the same gate. Every rule is confirmed via `AskUserQuestion` before writing; ~40-line cap per file. Invocable standalone any time, and auto-suggested (never forced) by `task-orchestrator` Plan Mode on first run if `.harness/` is absent entirely. Terminal, no skill loaded.
```

With:

```markdown
**`harness-engineer` (agents/)** — generates/maintains `.harness/architecture.md`, `.harness/standards.md`, `.harness/workflow.md`, `.harness/environment.md` at the consuming project's root: the convention files `task-orchestrator`/`software-engineer`/`qa-engineer`/`qa-auditor` load to follow a codebase's own observed rules instead of generic defaults. The first three are prose guidance; `environment.md` is a typed, machine-checkable vocabulary (`tool-version`/`port-open`/`env-var-set`/escape-hatch `command`, each tagged `[blocking]`/`[warning]`) that `task-orchestrator`'s Environment Preflight step (see below) executes directly rather than reads as guidance. Generate mode derives draft rules from the codebase itself (or, on a genuinely fresh/near-empty repo, pre-fills from `docs/architecture/architecture-spec.md` when present and interviews for the rest — never invents a rule with no observed basis; `environment.md` always goes through the interview path on a fresh repo, since a spec doesn't declare exact tool-version floors or port numbers); Update mode diffs current conventions against what's codified and proposes amendments through the same gate. Every rule is confirmed via `AskUserQuestion` before writing; ~40-line cap per file. Invocable standalone any time, and auto-suggested (never forced) by `task-orchestrator` Plan Mode on first run if `.harness/` is absent entirely. Terminal, no skill loaded. See `docs/.specs/2026-08-15-coding-chain-environment-preflight-design.md` for the full design.
```

- [ ] **Step 3: Update the `task-orchestrator` bullet**

Edit `CLAUDE.md`. Replace:

```markdown
**`task-orchestrator` (agents/)** — the coding chain's first and last agent. **Plan Mode** hard-requires an existing `docs/.plans/<slug>.md` (reads it as-is, never re-authors it), creates `docs/.tasks/YYYY-MM-DD-<slug>/`, runs a `qa-engineer` + `software-engineer` feasibility read, creates the branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")`, and hands off to `documentation-auditor` (Doc Gate) rather than straight to `qa-engineer` — a CRITICAL or HIGH finding *within the task's own scope* is resolved by the invoking main-thread session, not by `documentation-auditor` itself (which only reports, never writes or asks); unrelated pre-existing findings from that agent's whole-repo audit are noted, never blocking. That same session advances `STATE.md`'s `Phase` to `QA-RED` and sets `Handoff to: qa-engineer` once resolved. **Publish Mode** (triggered once `qa-auditor` → `documentation-auditor` Doc Post-Impl hands off clean, same ownership split) makes the consolidated commit, opens the PR/MR via `gh`/`glab`, writes the UAT checklist, surfaces one consolidated harness-drift/doc-drift question, and calls `project-manager`'s Status Sync to flip the ticket (`In Review`, then `Done` once merge is observed) — deleting the local plan draft only once ticket closure is actually observed. Supports Attended (default) and Unattended (tmux-detached, ported from maestro's `swarm.sh`) execution, pausing at `STATE.md`'s `Phase: HANDOFF NEEDED` wherever `AskUserQuestion` would otherwise fire. Never talks to `gh`/`glab`/ClickUp for ticket *status* directly — always through `project-manager`. Terminal (Publish).
```

With:

```markdown
**`task-orchestrator` (agents/)** — the coding chain's first and last agent. **Plan Mode** hard-requires an existing `docs/.plans/<slug>.md` (reads it as-is, never re-authors it), creates `docs/.tasks/YYYY-MM-DD-<slug>/`, runs an **Environment Preflight** against `.harness/environment.md` when present — its typed checks (tool versions, service reachability, env vars) gate branch/worktree creation on any failed `[blocking]` check (`AskUserQuestion` Attended / `HANDOFF NEEDED` Unattended, same shape as the feasibility gate below) — then runs a `qa-engineer` + `software-engineer` feasibility read, creates the branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")`, and hands off to `documentation-auditor` (Doc Gate) rather than straight to `qa-engineer` — a CRITICAL or HIGH finding *within the task's own scope* is resolved by the invoking main-thread session, not by `documentation-auditor` itself (which only reports, never writes or asks); unrelated pre-existing findings from that agent's whole-repo audit are noted, never blocking. That same session advances `STATE.md`'s `Phase` to `QA-RED` and sets `Handoff to: qa-engineer` once resolved. **Publish Mode** (triggered once `qa-auditor` → `documentation-auditor` Doc Post-Impl hands off clean, same ownership split) makes the consolidated commit, opens the PR/MR via `gh`/`glab`, writes the UAT checklist, surfaces one consolidated harness-drift/doc-drift question, and calls `project-manager`'s Status Sync to flip the ticket (`In Review`, then `Done` once merge is observed) — deleting the local plan draft only once ticket closure is actually observed. Supports Attended (default) and Unattended (tmux-detached, ported from maestro's `swarm.sh`) execution, pausing at `STATE.md`'s `Phase: HANDOFF NEEDED` wherever `AskUserQuestion` would otherwise fire. Never talks to `gh`/`glab`/ClickUp for ticket *status* directly — always through `project-manager`. Terminal (Publish). See `docs/.specs/2026-08-15-coding-chain-environment-preflight-design.md` for the Environment Preflight design.
```

- [ ] **Step 4: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "Document Environment Preflight in CLAUDE.md

Updates the coding-chain-shared, harness-engineer, and
task-orchestrator bullets for the new .harness/environment.md file
and task-orchestrator's Step 4.5.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Bump the version**

Edit `.claude-plugin/plugin.json`: `"version": "0.11.0"` → `"version": "0.12.0"` (minor bump — new capability on two existing agents, per this repo's own Versioning rule).

- [ ] **Step 7: Full plugin validation**

Run: `claude plugin validate . --strict`
Expected: passes clean.

- [ ] **Step 8: Full test suite**

Run: `pytest tests/ -v -s`
Expected: `tests/test_usage_dashboard.py`'s deterministic subset stays green (unaffected by this change). `tests/test_intent_routing.py`'s eval suite stays at or above `MIN_PASS` — this plan makes zero changes to `agents/intent-analyzer.md`, so no regression is expected there; a flip on a single case is normal model variance per this repo's own testing guidance, not a blocker.

- [ ] **Step 9: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "Bump to 0.12.0 for the coding-chain environment preflight

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
