# Graphify Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Graphify as a soft-optional, shared code-graph capability to 8 cairn agents (`codebase-auditor`, `qa-auditor`, `solution-architect`, `documentation-auditor`, `harness-engineer`, `software-engineer`, `qa-engineer`, `task-orchestrator`) via a new thin skill, `graphify-context`, that documents the detection contract and query guidance — never reimplementing Graphify itself.

**Architecture:** `graphify-context` (new skill, always loads — it ships with the plugin) teaches the calling agent how to attempt `Skill(skill: "graphify")` (the actual third-party tool) and what to do with it if it succeeds; every calling agent falls back to its own existing `Read`/`Glob`/`Grep` approach if that attempt fails. Each of the 8 agents gains exactly one integration point matching its own documented weak spot or natural query moment, `CLAUDE.md`'s architecture narrative is updated to match, and the plugin version is bumped.

**Tech Stack:** Markdown agent/skill prose files (no application code, no test framework — this repo has no unit tests over agent prompt behavior). Verification is structural (`grep`/`Glob` presence checks) plus headless end-to-end dispatch per `CLAUDE.md`'s "Testing a command end-to-end" convention.

**Spec:** `docs/.specs/2026-08-16-graphify-integration-design.md`

## Global Constraints

- cairn's own skill invocation: exactly `Skill(skill: "graphify-context")` — always loads, it ships with the plugin, never soft-optional itself.
- The third-party tool invocation: exactly `Skill(skill: "graphify")` — Graphify registers globally at `~/.claude/skills/graphify/SKILL.md`, so detection is a `Skill` call, never a `Glob`.
- Detection contract everywhere: attempt `Skill(skill: "graphify")` once; on failure, skip silently and fall back to the calling agent's existing approach. Never `ABORT`. Never emit a `HARNESS FLAG:` for its absence — that mechanism is for undocumented codebase conventions, not third-party skill availability.
- Nothing added by this plan is hard-required. Every new integration point is try-and-skip-silently.
- `Skill` must be added to the `tools:` frontmatter of `codebase-auditor`, `qa-auditor`, `documentation-auditor`, and `harness-engineer` (none currently carry it). `solution-architect`, `software-engineer`, `qa-engineer`, and `task-orchestrator` already have `Skill` — no frontmatter change needed for those four.
- Version bump target: `0.13.0` → `0.14.0` (minor, per `CLAUDE.md`'s Versioning section — new feature).

---

## Task 1: Create the `graphify-context` skill

**Files:**
- Create: `skills/graphify-context/SKILL.md`

**Interfaces:**
- Produces: the `graphify-context` skill, invoked via `Skill(skill: "graphify-context")` by all 8 agents in Tasks 2-9.

- [ ] **Step 1: Write the skill file**

```markdown
---
name: graphify-context
description: Detection contract and query guidance for Graphify, a soft-optional third-party code-graph tool. Loaded by 8 cairn agents (codebase-auditor, qa-auditor, solution-architect, documentation-auditor, harness-engineer, software-engineer, qa-engineer, task-orchestrator) at the point they'd otherwise reach straight for Read/Glob/Grep. Never reimplements Graphify itself — documents how to detect it, when a graph query beats a plain file read, and the discipline for treating its output as advisory, not fact.
---

# Graphify Context — shared detection and query guidance

Graphify (`Graphify-Labs/graphify`) is a vendored third-party code-graph tool, never shipped or reimplemented by cairn — same "hard-required, never reimplemented" family as `superpowers`/`marketing-skills`, except here the requirement level is **soft**: every agent that loads this skill degrades silently to its own existing `Read`/`Glob`/`Grep` approach if Graphify isn't installed. See `docs/.specs/2026-08-16-graphify-integration-design.md` for the full rationale and scope decision.

## Detection contract

Graphify registers globally at `~/.claude/skills/graphify/SKILL.md` — not project-vendored, unlike Impeccable or the Emil Kowalski skills, so the check is a `Skill` invocation, never a `Glob`.

1. Attempt `Skill(skill: "graphify")` once.
2. **If it fails** (not installed) — skip silently, proceed with the calling agent's normal `Read`/`Glob`/`Grep` approach. Never `ABORT`, never emit a `HARNESS FLAG:` for its absence — a missing third-party skill is expected steady-state, not a fault.
3. **If it succeeds** — use it per the guidance below for the rest of the calling step, then return control to the agent's normal flow.

## When to prefer a graph query over grep/Read

Prefer a graph query for a **relationship** question: symbol lookup, call-chain or blast-radius analysis, cross-file dependency mapping, or doc-to-code traceability (Graphify indexes docs/configs alongside code, not just source). Prefer `Read` directly for anything that isn't a relationship question — a graph query is not a substitute for reading a file's actual content when the task is about that file.

## Non-goal / discipline

Graph output is advisory context, never a citable fact on its own. Before presenting any graph-sourced finding, confirm it against the real `file:line` it points to — the same discipline `codebase-auditor` already applies to its own grep-level dead-code guesses (its Step 5: "label `INFO` unless corroborated"). An agent that cites a graph relationship without having read the actual file it names is not following this skill correctly.
```

- [ ] **Step 2: Verify structurally**

Run: `grep -c "^---$" skills/graphify-context/SKILL.md`
Expected: `2` (opening and closing frontmatter delimiters).

Run: `head -3 skills/graphify-context/SKILL.md`
Expected: `---`, `name: graphify-context`, `description: ...` — confirms valid frontmatter shape matching every other skill in the repo.

- [ ] **Step 3: Commit**

```bash
git add skills/graphify-context/SKILL.md
git commit -m "Add graphify-context skill: shared detection contract and query guidance"
```

---

## Task 2: Wire Graphify into `agents/codebase-auditor.md`

**Files:**
- Modify: `agents/codebase-auditor.md`

**Interfaces:**
- Consumes: `Skill(skill: "graphify-context")` from Task 1.

- [ ] **Step 1: Update frontmatter `description` and `tools`**

Old text (lines 3-4):
```
description: "Use this agent to produce a point-in-time health snapshot of a codebase — dependency risk, tooling-reported lint/typecheck/audit issues, TODO/FIXME debt, secret-shaped values, and structural oddities — written to one timestamped report. Read-mostly: the only file it writes is its own audit report, never source. Invoke before a refactor, periodically for a health check, or whenever asked to assess/audit codebase quality or risk. Distinct from `documentation-auditor` (validates existing docs, never writes) — this agent analyzes source and produces a new artifact from what it finds."
tools: Read, Glob, Grep, Bash, Write
```

New text:
```
description: "Use this agent to produce a point-in-time health snapshot of a codebase — dependency risk, tooling-reported lint/typecheck/audit issues, TODO/FIXME debt, secret-shaped values, and structural oddities — written to one timestamped report. Read-mostly: the only file it writes is its own audit report, never source. The Step 5 dead-code pass runs a soft-optional Graphify query before falling back to grep cross-reference — skips silently if Graphify isn't installed. Invoke before a refactor, periodically for a health check, or whenever asked to assess/audit codebase quality or risk. Distinct from `documentation-auditor` (validates existing docs, never writes) — this agent analyzes source and produces a new artifact from what it finds."
tools: Read, Glob, Grep, Bash, Write, Skill
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet**

Old text:
```
- ALWAYS write to a new timestamped file — never overwrite a prior audit. On a same-second filename collision, append `-2`, `-3`, etc.
- NEVER hand off to another agent automatically — terminal. A prose "next step" suggestion is fine; invoking one is not.
```

New text:
```
- ALWAYS write to a new timestamped file — never overwrite a prior audit. On a same-second filename collision, append `-2`, `-3`, etc.
- Graphify (Step 5 dead-code pass) is soft-optional — see `Skill(skill: "graphify-context")`. Never `ABORT` on its absence; a failed `Skill(skill: "graphify")` invocation just means fall back to the existing grep cross-reference.
- NEVER hand off to another agent automatically — terminal. A prose "next step" suggestion is fine; invoking one is not.
```

- [ ] **Step 3: Rewrite Step 5 (Dead-code / smell pass)**

Old text:
```
### Step 5 — Dead-code / smell pass (best-effort)

Note obviously unreferenced files or exports where discoverable via `Grep` cross-reference (e.g. a named export with zero import hits repo-wide). This is inherently incomplete without language-aware tooling — label findings from this step `INFO` unless corroborated by a Step 3 tool, and say so rather than presenting grep-level guesses as certain.
```

New text:
```
### Step 5 — Dead-code / smell pass (best-effort)

First, invoke `Skill(skill: "graphify-context")` for the detection contract, then attempt `Skill(skill: "graphify")` per that contract. If it succeeds, query the graph for unreferenced symbols/exports — a graph-corroborated finding is promoted to `LOW`/`MEDIUM` per Step 6 (same corroboration treatment a Step 3 tool hit already gets). If it fails, skip silently and fall back to the grep-only approach below.

Note obviously unreferenced files or exports where discoverable via `Grep` cross-reference (e.g. a named export with zero import hits repo-wide). This is inherently incomplete without language-aware tooling — label findings from this step `INFO` unless corroborated by a Step 3 tool or a successful Graphify query, and say so rather than presenting grep-level guesses as certain.
```

- [ ] **Step 4: Update the Step 6 severity table's `LOW` row**

Old text:
```
| **LOW** | Debt markers (TODO/FIXME), minor lint warnings, stale-looking files |
```

New text:
```
| **LOW** | Debt markers (TODO/FIXME), minor lint warnings, stale-looking files, Graphify-corroborated dead code |
```

- [ ] **Step 5: Verify structurally**

Run: `grep -n "graphify" agents/codebase-auditor.md`
Expected: matches in the frontmatter description, `tools:` line, HARD REQUIREMENTS, Step 5 (twice), and the Step 6 table `LOW` row — 5+ matches total, none adjacent to `ABORT`.

- [ ] **Step 6: Commit**

```bash
git add agents/codebase-auditor.md
git commit -m "Wire soft-optional Graphify query into codebase-auditor's dead-code pass"
```

---

## Task 3: Wire Graphify into `agents/qa-auditor.md`

**Files:**
- Modify: `agents/qa-auditor.md`

**Interfaces:**
- Consumes: `Skill(skill: "graphify-context")` from Task 1.

- [ ] **Step 1: Update frontmatter `description` and `tools`**

Old text (lines 3-4, first paragraph of description and the `tools:` line):
```
description: "Use this agent for the independent post-implementation re-verification in the coding chain, after software-engineer completes. Reruns scoped tests (task-affected files only), best-effort coverage report (never gated), code quality review, and conditional security/perf/dependency checks. Loads .harness/architecture.md + standards.md and raises a HIGH finding for task-introduced violations only (pre-existing violations untouched). Routes fix requests: test issues to qa-engineer, implementation bugs and HIGH+ findings to software-engineer.
```
```
tools: Read, Glob, Grep, Bash, Write, Edit
```

New text:
```
description: "Use this agent for the independent post-implementation re-verification in the coding chain, after software-engineer completes. Reruns scoped tests (task-affected files only), best-effort coverage report (never gated), code quality review, and conditional security/perf/dependency checks. A soft-optional Graphify blast-radius query supplements task-affected scoping with downstream impact a git diff alone doesn't show. Loads .harness/architecture.md + standards.md and raises a HIGH finding for task-introduced violations only (pre-existing violations untouched). Routes fix requests: test issues to qa-engineer, implementation bugs and HIGH+ findings to software-engineer.
```
```
tools: Read, Glob, Grep, Bash, Write, Edit, Skill
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet**

Old text:
```
- ALWAYS `Glob`-check for `.harness/architecture.md` and `.harness/standards.md`; `Read` and apply both when present, skip silently when `.harness/` is absent entirely.
- `.harness/` violations: raise a `HIGH` finding, routed to `software-engineer`, **only** for a violation on a line `git diff` (against the task's base commit) shows as added or modified by this task. NEVER flag a pre-existing violation — whether in an untouched file or on an untouched line inside an otherwise-edited file — leave it untouched, note it at most as `INFO`.
```

New text:
```
- ALWAYS `Glob`-check for `.harness/architecture.md` and `.harness/standards.md`; `Read` and apply both when present, skip silently when `.harness/` is absent entirely.
- Graphify blast-radius supplement (Step 1.5) is soft-optional — see `Skill(skill: "graphify-context")`. Never `ABORT` on its absence; a failed `Skill(skill: "graphify")` invocation just means proceed with git-diff-based scoping alone. A blast-radius hit outside the task's changed lines is never promoted past `INFO`.
- `.harness/` violations: raise a `HIGH` finding, routed to `software-engineer`, **only** for a violation on a line `git diff` (against the task's base commit) shows as added or modified by this task. NEVER flag a pre-existing violation — whether in an untouched file or on an untouched line inside an otherwise-edited file — leave it untouched, note it at most as `INFO`.
```

- [ ] **Step 3: Insert Step 1.5**

Old text:
```
### Step 1 — Load context

`Read` `STATE.md` for `Worktree` and `Plan:`. `cd` into the worktree. `Read` `docs/.plans/<slug>.md` for scope. `Read` the files `software-engineer`'s handoff named as changed — this defines what "task-affected" means for every check below.

### Step 2 — Scoped test rerun
```

New text:
```
### Step 1 — Load context

`Read` `STATE.md` for `Worktree` and `Plan:`. `cd` into the worktree. `Read` `docs/.plans/<slug>.md` for scope. `Read` the files `software-engineer`'s handoff named as changed — this defines what "task-affected" means for every check below.

### Step 1.5 — Graphify blast-radius supplement (soft-optional)

Invoke `Skill(skill: "graphify-context")` for the detection contract, then attempt `Skill(skill: "graphify")` per that contract. If it fails, skip silently and proceed to Step 2 with Step 1's git-diff-based scope as-is. If it succeeds, query the graph for what calls/imports the task-affected symbols — this supplements the "task-affected" understanding with downstream impact a diff alone doesn't show. This is context only: it never expands what Step 6 treats as HIGH-eligible (still only lines `git diff` shows as added/modified by this task) — a blast-radius hit outside that scope is noted as `INFO` at most, same as any other out-of-scope observation.

### Step 2 — Scoped test rerun
```

- [ ] **Step 4: Update START**

Old text:
```
1. Read `STATE.md` for `Worktree` and `Plan:`, `cd` into the worktree, read the plan and the files `software-engineer` named as changed (Step 1).
2. Rerun scoped tests, task-affected files only (Step 2).
3. Run best-effort coverage (Step 3).
4. Run the code quality review (Step 4).
5. Run any triggered conditional checks — security, performance, dependency (Step 5).
6. `Glob`-check `.harness/architecture.md` and `standards.md`, apply if present, checking for task-introduced violations only (Step 6).
7. Emit an optional `HARNESS FLAG:` note if warranted (Step 7).
8. Classify findings and decide the route: clean, test bug, or implementation/`HIGH`+ finding (Step 8).
9. Update `STATE.md` and append `HISTORY.md` (Step 9).
10. Emit the outcome-appropriate **PHASE HANDOFF** block.
```

New text:
```
1. Read `STATE.md` for `Worktree` and `Plan:`, `cd` into the worktree, read the plan and the files `software-engineer` named as changed (Step 1).
2. Attempt the Graphify blast-radius supplement — soft-optional, skip silently if unavailable (Step 1.5).
3. Rerun scoped tests, task-affected files only (Step 2).
4. Run best-effort coverage (Step 3).
5. Run the code quality review (Step 4).
6. Run any triggered conditional checks — security, performance, dependency (Step 5).
7. `Glob`-check `.harness/architecture.md` and `standards.md`, apply if present, checking for task-introduced violations only (Step 6).
8. Emit an optional `HARNESS FLAG:` note if warranted (Step 7).
9. Classify findings and decide the route: clean, test bug, or implementation/`HIGH`+ finding (Step 8).
10. Update `STATE.md` and append `HISTORY.md` (Step 9).
11. Emit the outcome-appropriate **PHASE HANDOFF** block.
```

- [ ] **Step 5: Verify structurally**

Run: `grep -n "graphify\|Step 1.5" agents/qa-auditor.md`
Expected: matches in frontmatter description, `tools:` line, HARD REQUIREMENTS, the new Step 1.5 section (heading + body), and START — 6+ matches.

- [ ] **Step 6: Commit**

```bash
git add agents/qa-auditor.md
git commit -m "Wire soft-optional Graphify blast-radius supplement into qa-auditor"
```

---

## Task 4: Wire Graphify into `agents/solution-architect.md`

**Files:**
- Modify: `agents/solution-architect.md`

**Interfaces:**
- Consumes: `Skill(skill: "graphify-context")` from Task 1.

- [ ] **Step 1: Update frontmatter `description`** (tools already includes `Skill` — no change)

Old text:
```
description: "Use this agent to produce ONE technical artifact per invocation — Architecture Specification, Database Schema, API Specification, or an ADR — scoped to a specific project. Upstream documents must exist before downstream ones (prd+user-flows → architecture-spec → db-schema/api-spec). ADRs are standalone, no upstream required, immutable content after write (status-only updates). Invoke when requirements (and optionally design docs) are ready and the user wants to define system structure, data storage, or service contracts."
```

New text:
```
description: "Use this agent to produce ONE technical artifact per invocation — Architecture Specification, Database Schema, API Specification, or an ADR — scoped to a specific project. Upstream documents must exist before downstream ones (prd+user-flows → architecture-spec → db-schema/api-spec). ADRs are standalone, no upstream required, immutable content after write (status-only updates). Non-ADR document types run a soft-optional Graphify structural pre-scan before Discovery Phase — skips silently if Graphify isn't installed. Invoke when requirements (and optionally design docs) are ready and the user wants to define system structure, data storage, or service contracts."
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet**

Old text:
```
- Output paths: `docs/architecture/` (Architecture Specification), `docs/backend/` (Database Schema, API Specification), `docs/adr/` (ADR, always) — never any other location.

---
```

New text:
```
- Output paths: `docs/architecture/` (Architecture Specification), `docs/backend/` (Database Schema, API Specification), `docs/adr/` (ADR, always) — never any other location.
- Graphify structural pre-scan (non-ADR document types) is soft-optional — see `Skill(skill: "graphify-context")`. Never `ABORT` on its absence; a failed `Skill(skill: "graphify")` invocation just means proceed to Discovery Phase with `Glob`/`Read` exploration alone.

---
```

- [ ] **Step 3: Insert the new pre-scan section**

Old text:
```
## UPSTREAM EXISTENCE CHECK, SKILL LOADING

Apply `skills/writer-shared/SKILL.md`'s Upstream Existence Check, additionally reading any recommended-but-optional upstream that exists (per `skills/solution-architecture-writing/SKILL.md`'s Dependency Chain) before proceeding. Skill Loading: invoke `Skill(skill: "writer-shared")` once at the start of every run, then invoke `Skill(skill: "solution-architecture-writing")` for the target document type's discovery dimensions, artifact format, and technical standards. For `architecture-spec.md` and `db-schema.md` (and ADRs), also invoke `Skill(skill: "mermaid-diagrams")` during Draft Phase — not for `api-spec.md`.

---

## DISCOVERY, DRAFT PHASE, FINAL REVIEW
```

New text:
```
## UPSTREAM EXISTENCE CHECK, SKILL LOADING

Apply `skills/writer-shared/SKILL.md`'s Upstream Existence Check, additionally reading any recommended-but-optional upstream that exists (per `skills/solution-architecture-writing/SKILL.md`'s Dependency Chain) before proceeding. Skill Loading: invoke `Skill(skill: "writer-shared")` once at the start of every run, then invoke `Skill(skill: "solution-architecture-writing")` for the target document type's discovery dimensions, artifact format, and technical standards. For `architecture-spec.md` and `db-schema.md` (and ADRs), also invoke `Skill(skill: "mermaid-diagrams")` during Draft Phase — not for `api-spec.md`.

---

## GRAPHIFY STRUCTURAL PRE-SCAN (non-ADR document types)

Runs after Upstream Existence Check and Skill Loading, before Discovery Phase, for `architecture-spec.md`, `db-schema.md`, and `api-spec.md`. Skip entirely in ADR Mode — an ADR records a decision, not a scan of existing structure.

Invoke `Skill(skill: "graphify-context")` for the detection contract, then attempt `Skill(skill: "graphify")` per that contract. If it fails, skip silently and proceed to Discovery Phase with `Glob`/`Read` exploration as today. If it succeeds, query the graph for the existing dependency structure relevant to the target document type — module/service boundaries for `architecture-spec.md`, existing data-access patterns for `db-schema.md`, existing endpoint/handler structure for `api-spec.md` — and use it as additional pre-discovery context, the same way an upstream document's content already informs Discovery Phase.

---

## DISCOVERY, DRAFT PHASE, FINAL REVIEW
```

- [ ] **Step 4: Update START**

Old text:
```
3. Non-ADR: run **Upstream Existence Check** → invoke `Skill(skill: "solution-architecture-writing")` for the target document type → **Discovery Phase** → **Draft Phase** (Write tool, invoking `Skill(skill: "mermaid-diagrams")` first unless producing `api-spec.md`).
```

New text:
```
3. Non-ADR: run **Upstream Existence Check** → invoke `Skill(skill: "solution-architecture-writing")` for the target document type → attempt the **Graphify Structural Pre-Scan** (soft-optional, skip silently if unavailable) → **Discovery Phase** → **Draft Phase** (Write tool, invoking `Skill(skill: "mermaid-diagrams")` first unless producing `api-spec.md`).
```

- [ ] **Step 5: Verify structurally**

Run: `grep -n "graphify\|GRAPHIFY" agents/solution-architect.md`
Expected: matches in frontmatter description, HARD REQUIREMENTS, the new section (heading + body, twice for `Skill(skill: "graphify")`/`Skill(skill: "graphify-context")`), and START — 5+ matches.

- [ ] **Step 6: Commit**

```bash
git add agents/solution-architect.md
git commit -m "Wire soft-optional Graphify structural pre-scan into solution-architect"
```

---

## Task 5: Wire Graphify into `agents/documentation-auditor.md`

**Files:**
- Modify: `agents/documentation-auditor.md`

**Interfaces:**
- Consumes: `Skill(skill: "graphify-context")` from Task 1.

- [ ] **Step 1: Update frontmatter `description` and `tools`**

Old text (lines 3-4):
```
description: "Use this agent to validate project documentation — README, setup docs, API docs, developer guides, and requirements/design/architecture artifacts — for accuracy, completeness, consistency, and cross-artifact traceability. Read-only; reports findings, does not fix them. Invoke after writing or updating any documentation, or on request to audit current doc state (e.g. 'does the README still match the code', 'check the PRD and user stories are consistent')."
tools: Read, Glob, Grep
```

New text:
```
description: "Use this agent to validate project documentation — README, setup docs, API docs, developer guides, and requirements/design/architecture artifacts — for accuracy, completeness, consistency, and cross-artifact traceability. A soft-optional Graphify query corroborates symbol/doc cross-references during the source-accuracy and cross-artifact checks — skips silently, Grep-only, if Graphify isn't installed. Read-only; reports findings, does not fix them. Invoke after writing or updating any documentation, or on request to audit current doc state (e.g. 'does the README still match the code', 'check the PRD and user stories are consistent')."
tools: Read, Glob, Grep, Skill
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet**

Old text:
```
- The full AUDIT REPORT (finding counts table + all `DOC-###` detail blocks) MUST be emitted as user-visible text — in every run, regardless of outcome.
- Draft Mode artifacts (carrying a `**Draft**` callout) get completeness/coverage findings downgraded to non-blocking `INFO` advisories — never silently dropped.

---
```

New text:
```
- The full AUDIT REPORT (finding counts table + all `DOC-###` detail blocks) MUST be emitted as user-visible text — in every run, regardless of outcome.
- Draft Mode artifacts (carrying a `**Draft**` callout) get completeness/coverage findings downgraded to non-blocking `INFO` advisories — never silently dropped.
- The Graphify-assisted cross-reference check is soft-optional — see `Skill(skill: "graphify-context")`. Never `ABORT` on its absence; a failed `Skill(skill: "graphify")` invocation just means every check runs `Grep`-only, exactly as documented.

---
```

- [ ] **Step 3: Insert a new section before VALIDATION CHECKS**

Old text:
```
This downgrade applies only to the specific artifact carrying the `**Draft**` marker — no effect on other documents in the same audit run.

---

## VALIDATION CHECKS
```

New text:
```
This downgrade applies only to the specific artifact carrying the `**Draft**` marker — no effect on other documents in the same audit run.

---

## GRAPHIFY-ASSISTED CROSS-REFERENCE CHECK (soft-optional)

Before running **VALIDATION CHECKS**, invoke `Skill(skill: "graphify-context")` for the detection contract, then attempt `Skill(skill: "graphify")` per that contract. If it fails, skip silently — every check below runs exactly as documented, `Grep`-only. If it succeeds, use it to corroborate symbol/doc cross-references during Check 3 (Accuracy Against Source) and Check 7 (Cross-Artifact Consistency) — a graph-confirmed broken reference is reported with the same severity the check already assigns; Graphify never changes a severity tier, only strengthens the evidence behind a finding `Grep` alone would have to guess at.

---

## VALIDATION CHECKS
```

- [ ] **Step 4: Update START**

Old text:
```
1. Check opening context for `REVIEW FOCUS: <path>` → if present, run **FOCUSED REVIEW MODE**, then STOP.
2. Glob all documentation files (`README.md`, `SETUP.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/**/*.md`, `agents/*.md`, `.claude/agents/*.md`).
3. Check each document for **DRAFT MODE ARTIFACT AWARENESS** — note which qualify for the completeness/coverage downgrade.
4. Run **CHECK 1–7** in order (skip 2 if no `agents/` or `.claude/agents/`; skip 7 unless 2+ requirements/design/architecture artifacts exist).
5. Classify all findings by severity, applying the Draft Mode downgrade to qualifying documents' Check 1/4/7 completeness-type findings.
6. Emit **AUDIT REPORT**.
7. Emit **COMPLETION** (`✅ COMPLETE` or `⚠️ FINDINGS`).
```

New text:
```
1. Check opening context for `REVIEW FOCUS: <path>` → if present, run **FOCUSED REVIEW MODE**, then STOP.
2. Glob all documentation files (`README.md`, `SETUP.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/**/*.md`, `agents/*.md`, `.claude/agents/*.md`).
3. Check each document for **DRAFT MODE ARTIFACT AWARENESS** — note which qualify for the completeness/coverage downgrade.
4. Attempt the **Graphify-Assisted Cross-Reference Check** — soft-optional, skip silently if unavailable.
5. Run **CHECK 1–7** in order (skip 2 if no `agents/` or `.claude/agents/`; skip 7 unless 2+ requirements/design/architecture artifacts exist).
6. Classify all findings by severity, applying the Draft Mode downgrade to qualifying documents' Check 1/4/7 completeness-type findings.
7. Emit **AUDIT REPORT**.
8. Emit **COMPLETION** (`✅ COMPLETE` or `⚠️ FINDINGS`).
```

- [ ] **Step 5: Verify structurally**

Run: `grep -n "graphify\|GRAPHIFY" agents/documentation-auditor.md`
Expected: matches in frontmatter description, `tools:` line, HARD REQUIREMENTS, the new section (heading + body), and START — 6+ matches.

- [ ] **Step 6: Commit**

```bash
git add agents/documentation-auditor.md
git commit -m "Wire soft-optional Graphify cross-reference check into documentation-auditor"
```

---

## Task 6: Wire Graphify into `agents/harness-engineer.md`

**Files:**
- Modify: `agents/harness-engineer.md`

**Interfaces:**
- Consumes: `Skill(skill: "graphify-context")` from Task 1.

- [ ] **Step 1: Update frontmatter `description` and `tools`**

Old text (lines 3-4, first sentence of description shown; `tools:` line):
```
description: "Use this agent to generate or update the .harness/ convention files (architecture.md, standards.md, workflow.md, environment.md) for the current codebase — deriving draft rules from the project's own observed conventions instead of hand-authoring them from a blank template. environment.md is a typed, machine-checkable vocabulary (tool versions, service reachability, env var presence) that task-orchestrator's Environment Preflight step executes before a task starts, distinct from the other three files' prose guidance. On a fresh/near-empty codebase, falls back to pre-filling from docs/architecture/architecture-spec.md when present, then interviewing for the rest, rather than writing evidence-free files. .harness/ is committed (not gitignored) so every clone/submodule gets the standard setup automatically.
```
```
tools: Read, Glob, Grep, Bash, AskUserQuestion, Write, Edit
```

New text:
```
description: "Use this agent to generate or update the .harness/ convention files (architecture.md, standards.md, workflow.md, environment.md) for the current codebase — deriving draft rules from the project's own observed conventions instead of hand-authoring them from a blank template. The standard observation path (Step 3) runs a soft-optional Graphify query as an additional evidence source before falling back to Glob/Grep/Bash alone. environment.md is a typed, machine-checkable vocabulary (tool versions, service reachability, env var presence) that task-orchestrator's Environment Preflight step executes before a task starts, distinct from the other three files' prose guidance. On a fresh/near-empty codebase, falls back to pre-filling from docs/architecture/architecture-spec.md when present, then interviewing for the rest, rather than writing evidence-free files. .harness/ is committed (not gitignored) so every clone/submodule gets the standard setup automatically.
```
```
tools: Read, Glob, Grep, Bash, AskUserQuestion, Write, Edit, Skill
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet**

Old text:
```
- ALWAYS confirm each `environment.md` check's severity (`[blocking]`/`[warning]`) as part of its confirm/edit/drop decision at the `AskUserQuestion` gate — never auto-assigned, and never left unset.
- Must run in the main thread, never as a dispatched background subagent — the confirm gate depends on live `AskUserQuestion`, which a background subagent cannot use.
```

New text:
```
- ALWAYS confirm each `environment.md` check's severity (`[blocking]`/`[warning]`) as part of its confirm/edit/drop decision at the `AskUserQuestion` gate — never auto-assigned, and never left unset.
- The Graphify-assisted observation pass (Step 3) is soft-optional — see `Skill(skill: "graphify-context")`. Never `ABORT` on its absence; a failed `Skill(skill: "graphify")` invocation just means observe the codebase via `Glob`/`Grep`/`Bash` alone, as today.
- Must run in the main thread, never as a dispatched background subagent — the confirm gate depends on live `AskUserQuestion`, which a background subagent cannot use.
```

- [ ] **Step 3: Insert Graphify guidance at the top of Step 3**

Old text:
```
### Step 3 — Generate mode: standard observation path

Observe the codebase directly:

- **Architecture**: stack (manifest files — `package.json`, `pyproject.toml`, `go.mod`, etc.), layering (directory structure, module boundaries), data storage patterns (`Grep` for ORM/DB client usage, migration directories).
```

New text:
```
### Step 3 — Generate mode: standard observation path

Invoke `Skill(skill: "graphify-context")` for the detection contract, then attempt `Skill(skill: "graphify")` per that contract. If it fails, skip silently and observe the codebase directly via `Glob`/`Grep`/`Bash` as below. If it succeeds, use it as an additional evidence source for Architecture (layering, module boundaries, data storage patterns) and Standards (naming, error-handling patterns) observations below — a Graphify-corroborated observation still needs its own evidence count/citation like any other, per the Write step's citation rule.

Observe the codebase directly:

- **Architecture**: stack (manifest files — `package.json`, `pyproject.toml`, `go.mod`, etc.), layering (directory structure, module boundaries), data storage patterns (`Grep` for ORM/DB client usage, migration directories).
```

- [ ] **Step 4: Verify structurally**

Run: `grep -n "graphify" agents/harness-engineer.md`
Expected: matches in frontmatter description, `tools:` line, HARD REQUIREMENTS, and Step 3 (twice) — 5+ matches.

- [ ] **Step 5: Commit**

```bash
git add agents/harness-engineer.md
git commit -m "Wire soft-optional Graphify observation source into harness-engineer"
```

---

## Task 7: Wire Graphify into `agents/software-engineer.md`

**Files:**
- Modify: `agents/software-engineer.md`

**Interfaces:**
- Consumes: `Skill(skill: "graphify-context")` from Task 1. `Skill` already in `tools:` frontmatter — no change.

- [ ] **Step 1: Update frontmatter `description`**

Old text (first paragraph, from `tools: Read, Glob, Grep, Bash, Write, Edit, Skill` down through the description):
```
description: "Use this agent to implement code in the coding chain — stack-agnostic, no per-stack guide skills, following whatever conventions exist in the repo plus .harness/architecture.md and standards.md when present. Two working modes: Chain (from qa-engineer's failing tests, TDD green phase, hands off to qa-auditor) and Direct (small bug-fix/decision requests with no task file, works on the current branch, no automated commit/PR — hands off to qa-engineer post-hoc). UI-facing tasks in either mode run a soft-optional Frontend Polish Pass (Anthropic Frontend Design, Taste Skill, Emil Kowalski skills — whichever are installed) before implementation. Plus a read-only Feasibility Assessment (plan path passed directly in opening context, before STATE.md exists) for task-orchestrator Plan Mode Step 7.
```

New text:
```
description: "Use this agent to implement code in the coding chain — stack-agnostic, no per-stack guide skills, following whatever conventions exist in the repo plus .harness/architecture.md and standards.md when present. Two working modes: Chain (from qa-engineer's failing tests, TDD green phase, hands off to qa-auditor) and Direct (small bug-fix/decision requests with no task file, works on the current branch, no automated commit/PR — hands off to qa-engineer post-hoc). UI-facing tasks in either mode run a soft-optional Frontend Polish Pass (Anthropic Frontend Design, Taste Skill, Emil Kowalski skills — whichever are installed) before implementation. Both modes, regardless of UI-facing status, also run a soft-optional Graphify pass for general code navigation during implementation. Plus a read-only Feasibility Assessment (plan path passed directly in opening context, before STATE.md exists) for task-orchestrator Plan Mode Step 7.
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet**

Old text:
```
- Frontend Polish Pass (Step 3.5) is soft-optional and gated to UI-facing tasks only — never runs in Feasibility Assessment mode, never aborts on a missing skill. Each of its three checks (Anthropic Frontend Design, Taste Skill, Emil Kowalski skills) is independent; any subset may be present.
- Feasibility Assessment mode: NEVER read `STATE.md` or look for a task folder/worktree — neither exists yet at that point in Plan Mode. The plan path arrives in the opening context. Write nothing, edit nothing, run nothing.
```

New text:
```
- Frontend Polish Pass (Step 3.5) is soft-optional and gated to UI-facing tasks only — never runs in Feasibility Assessment mode, never aborts on a missing skill. Each of its three checks (Anthropic Frontend Design, Taste Skill, Emil Kowalski skills) is independent; any subset may be present.
- Graphify context (Step 3.6) is soft-optional and ungated (Chain and Direct modes, any task) — see `Skill(skill: "graphify-context")`. Never `ABORT` on its absence; a failed `Skill(skill: "graphify")` invocation just means navigate via `Read`/`Glob`/`Grep` alone, as today. Never runs in Feasibility Assessment mode.
- Feasibility Assessment mode: NEVER read `STATE.md` or look for a task folder/worktree — neither exists yet at that point in Plan Mode. The plan path arrives in the opening context. Write nothing, edit nothing, run nothing.
```

- [ ] **Step 3: Insert Step 3.6 after Step 3.5**

Old text:
```
If none of the three are present, this step is a no-op — proceed to the next step (Step 4 in Direct mode, Step 5 in Chain mode) exactly as if it hadn't been UI-facing. Never emit a `HARNESS FLAG:` for a missing skill here — that mechanism is for undocumented codebase conventions, not third-party skill availability.

### Step 4 — Direct mode: load context
```

New text:
```
If none of the three are present, this step is a no-op — proceed to the next step (Step 4 in Direct mode, Step 5 in Chain mode) exactly as if it hadn't been UI-facing. Never emit a `HARNESS FLAG:` for a missing skill here — that mechanism is for undocumented codebase conventions, not third-party skill availability.

### Step 3.6 — Graphify context (Chain and Direct modes, general navigation)

Invoke `Skill(skill: "graphify-context")` for the detection contract, then attempt `Skill(skill: "graphify")` per that contract. If it fails, skip silently — navigate the codebase via `Read`/`Glob`/`Grep` exactly as today. If it succeeds, prefer it for relationship questions during implementation (Step 5) — what calls a function about to change, what a symbol's dependents are — per `graphify-context`'s query guidance; still `Read` the actual file before changing it, never edit based on a graph query alone.

Unlike Step 3.5, this runs regardless of whether the task is UI-facing.

### Step 4 — Direct mode: load context
```

- [ ] **Step 4: Update START**

Old text:
```
4. If the task is UI-facing, run the **Frontend Polish Pass** (Step 3.5) — soft-optional, skip silently on any missing skill; skip the whole step if not UI-facing.
5. Implement — green phase (Step 5, Chain) or scoped fix (Step 5, Direct). Raise a `TEST FIX REQUEST` instead of forcing a bad test, if warranted.
6. Emit an optional `HARNESS FLAG:` note if warranted (Step 6).
7. Chain mode only: update `STATE.md` — appending any `HARNESS FLAG:` to `Harness flags`, not `Key info` — and append `HISTORY.md` (Step 7).
8. Emit the mode-appropriate **PHASE HANDOFF** block.
```

New text:
```
4. If the task is UI-facing, run the **Frontend Polish Pass** (Step 3.5) — soft-optional, skip silently on any missing skill; skip the whole step if not UI-facing.
5. Attempt **Graphify context** (Step 3.6) — soft-optional, skip silently if unavailable; runs regardless of UI-facing status.
6. Implement — green phase (Step 5, Chain) or scoped fix (Step 5, Direct). Raise a `TEST FIX REQUEST` instead of forcing a bad test, if warranted.
7. Emit an optional `HARNESS FLAG:` note if warranted (Step 6).
8. Chain mode only: update `STATE.md` — appending any `HARNESS FLAG:` to `Harness flags`, not `Key info` — and append `HISTORY.md` (Step 7).
9. Emit the mode-appropriate **PHASE HANDOFF** block.
```

- [ ] **Step 5: Verify structurally**

Run: `grep -n "graphify\|Step 3.6" agents/software-engineer.md`
Expected: matches in frontmatter description, HARD REQUIREMENTS, the new Step 3.6 section (heading + body), and START — 6+ matches.

- [ ] **Step 6: Commit**

```bash
git add agents/software-engineer.md
git commit -m "Wire soft-optional Graphify navigation pass into software-engineer"
```

---

## Task 8: Wire Graphify into `agents/qa-engineer.md`

**Files:**
- Modify: `agents/qa-engineer.md`

**Interfaces:**
- Consumes: `Skill(skill: "graphify-context")` from Task 1. `Skill` already in `tools:` frontmatter — no change.

- [ ] **Step 1: Update frontmatter `description`**

Old text:
```
description: "Use this agent to write tests in the coding chain — pre-implementation (TDD red phase, hard-requires superpowers:test-driven-development) when handed off from task-orchestrator, or post-implementation in Direct Mode when handed off from software-engineer. Also runs a read-only Feasibility Assessment (plan path passed directly in opening context, before STATE.md exists) for task-orchestrator Plan Mode Step 7, and re-enters as Chain mode on a qa-auditor route-back or a software-engineer TEST FIX REQUEST regardless of STATE.md's recorded Phase. Detects test framework/commands from the repo itself, with .harness/standards.md's Testing section overriding the guess when present.
```

New text:
```
description: "Use this agent to write tests in the coding chain — pre-implementation (TDD red phase, hard-requires superpowers:test-driven-development) when handed off from task-orchestrator, or post-implementation in Direct Mode when handed off from software-engineer. Also runs a read-only Feasibility Assessment (plan path passed directly in opening context, before STATE.md exists) for task-orchestrator Plan Mode Step 7, and re-enters as Chain mode on a qa-auditor route-back or a software-engineer TEST FIX REQUEST regardless of STATE.md's recorded Phase. Detects test framework/commands from the repo itself, with .harness/standards.md's Testing section overriding the guess when present. A soft-optional Graphify pass informs which code paths need coverage before tests are written.
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet**

Old text:
```
- ALWAYS detect the test framework/commands from the repo itself first (existing test files and their conventions, package-manifest test scripts, CI config). `.harness/standards.md`'s `## Testing` section, when present, overrides the inferred guess — `Glob`-check for it, skip silently if `.harness/` is absent.
- Chain mode: ALWAYS confirm each newly written test fails, **and fails for the right reason** (missing or incomplete implementation) — a test that fails from a typo, bad setup, or wrong assertion is a test bug, not a red phase. Fix the test, don't move on.
```

New text:
```
- ALWAYS detect the test framework/commands from the repo itself first (existing test files and their conventions, package-manifest test scripts, CI config). `.harness/standards.md`'s `## Testing` section, when present, overrides the inferred guess — `Glob`-check for it, skip silently if `.harness/` is absent.
- The Graphify context pass (Step 3.5) is soft-optional — see `Skill(skill: "graphify-context")`. Never `ABORT` on its absence; a failed `Skill(skill: "graphify")` invocation just means understand the code-under-test via `Read`/`Grep` alone, as today.
- Chain mode: ALWAYS confirm each newly written test fails, **and fails for the right reason** (missing or incomplete implementation) — a test that fails from a typo, bad setup, or wrong assertion is a test bug, not a red phase. Fix the test, don't move on.
```

- [ ] **Step 3: Insert Step 3.5 between Step 3 and Step 4**

Old text:
```
### Step 3 — Framework/command detection (Chain and Direct modes)

Inspect the repo itself first: existing test files and their naming/location convention, package-manifest test scripts (`package.json`, `pyproject.toml`, etc.), CI config (`.github/workflows/`, etc.). `Glob(.harness/standards.md)` — if present, `Read` it; its `## Testing` section overrides the inferred guess when the two disagree. Skip silently if `.harness/` is absent entirely.

### Step 4 — Chain mode: write the red phase
```

New text:
```
### Step 3 — Framework/command detection (Chain and Direct modes)

Inspect the repo itself first: existing test files and their naming/location convention, package-manifest test scripts (`package.json`, `pyproject.toml`, etc.), CI config (`.github/workflows/`, etc.). `Glob(.harness/standards.md)` — if present, `Read` it; its `## Testing` section overrides the inferred guess when the two disagree. Skip silently if `.harness/` is absent entirely.

### Step 3.5 — Graphify context (Chain and Direct modes, soft-optional)

Invoke `Skill(skill: "graphify-context")` for the detection contract, then attempt `Skill(skill: "graphify")` per that contract. If it fails, skip silently and understand the code-under-test via `Read`/`Grep` alone, as today. If it succeeds, query the graph for what functions/paths the plan's scope (Chain) or the changed files (Direct) actually exercise — call chains, dependents — to inform which behaviors the tests written in Step 4/5 need to cover, before writing them.

### Step 4 — Chain mode: write the red phase
```

- [ ] **Step 4: Update START**

Old text:
```
4. Detect the test framework/commands, checking `.harness/standards.md` if present (Step 3).
5. Write and run tests per mode — red phase (Step 4), post-hoc (Step 5), or, on a fix-cycle re-entry, correct the specific test named by `qa-auditor`/`software-engineer` and rerun it.
6. Run best-effort coverage (Step 6).
7. Emit an optional `HARNESS FLAG:` note if warranted (Step 7).
8. Chain mode only: update `STATE.md` — appending any `HARNESS FLAG:` to `Harness flags`, not `Key info` — and append `HISTORY.md` (Step 8).
9. Emit the mode-appropriate **PHASE HANDOFF** block.
```

New text:
```
4. Detect the test framework/commands, checking `.harness/standards.md` if present (Step 3).
5. Attempt **Graphify context** (Step 3.5) — soft-optional, skip silently if unavailable.
6. Write and run tests per mode — red phase (Step 4), post-hoc (Step 5), or, on a fix-cycle re-entry, correct the specific test named by `qa-auditor`/`software-engineer` and rerun it.
7. Run best-effort coverage (Step 6).
8. Emit an optional `HARNESS FLAG:` note if warranted (Step 7).
9. Chain mode only: update `STATE.md` — appending any `HARNESS FLAG:` to `Harness flags`, not `Key info` — and append `HISTORY.md` (Step 8).
10. Emit the mode-appropriate **PHASE HANDOFF** block.
```

- [ ] **Step 5: Verify structurally**

Run: `grep -n "graphify\|Step 3.5" agents/qa-engineer.md`
Expected: matches in frontmatter description, HARD REQUIREMENTS, the new Step 3.5 section (heading + body), and START — 6+ matches.

- [ ] **Step 6: Commit**

```bash
git add agents/qa-engineer.md
git commit -m "Wire soft-optional Graphify context pass into qa-engineer"
```

---

## Task 9: Wire Graphify into `agents/task-orchestrator.md`

**Files:**
- Modify: `agents/task-orchestrator.md`

**Interfaces:**
- Consumes: `Skill(skill: "graphify-context")` from Task 1. `Skill` already in `tools:` frontmatter — no change.

- [ ] **Step 1: Update frontmatter `description`**

Old text:
```
description: "Use this agent to run the coding-chain's Plan and Publish steps. Plan Mode: hard-requires an existing docs/.plans/<slug>.md (reads it as the plan, never re-authors it), creates docs/.tasks/YYYY-MM-DD-<slug>/, runs an Environment Preflight against .harness/environment.md when present (gates branch/worktree creation on any failed blocking check), runs a qa-engineer+software-engineer feasibility assessment, creates the branch/worktree via superpowers:using-git-worktrees. Publish Mode: consolidated commit, PR/MR via gh/glab, UAT checklist, surfaces harness+doc-drift flags, closes the ticket and deletes the local plan draft once closure is observed. First and last agent in the chain.
```

New text:
```
description: "Use this agent to run the coding-chain's Plan and Publish steps. Plan Mode: hard-requires an existing docs/.plans/<slug>.md (reads it as the plan, never re-authors it), creates docs/.tasks/YYYY-MM-DD-<slug>/, runs an Environment Preflight against .harness/environment.md when present (gates branch/worktree creation on any failed blocking check), runs a qa-engineer+software-engineer feasibility assessment supplemented by a soft-optional Graphify scope query, creates the branch/worktree via superpowers:using-git-worktrees. Publish Mode: consolidated commit, PR/MR via gh/glab, UAT checklist, surfaces harness+doc-drift flags, closes the ticket and deletes the local plan draft once closure is observed. First and last agent in the chain.
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet**

Old text:
```
- ALWAYS create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` — never reimplement worktree/branch mechanics with raw `git` commands.
- NEVER create the branch/worktree (Step 5) before Environment Preflight (Step 4.5) resolves — a failed `[blocking]` check must be answered (fix/retry or proceed anyway) before anything gets created, so a rejected environment never leaves a half-set-up task behind.
```

New text:
```
- ALWAYS create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` — never reimplement worktree/branch mechanics with raw `git` commands.
- The Graphify scope supplement (Step 7) is soft-optional — see `Skill(skill: "graphify-context")`. Never `ABORT` on its absence; a failed `Skill(skill: "graphify")` invocation just means the feasibility read proceeds on `qa-engineer`/`software-engineer` verdicts alone, as today.
- NEVER create the branch/worktree (Step 5) before Environment Preflight (Step 4.5) resolves — a failed `[blocking]` check must be answered (fix/retry or proceed anyway) before anything gets created, so a rejected environment never leaves a half-set-up task behind.
```

- [ ] **Step 3: Update Step 7 (Feasibility assessment)**

Old text:
```
### Step 7 — Feasibility assessment

Invoke `qa-engineer` and `software-engineer` at their **Feasibility Assessment mode** — each independently assesses test/implementation feasibility against the plan.
```

New text:
```
### Step 7 — Feasibility assessment

Invoke `Skill(skill: "graphify-context")` for the detection contract, then attempt `Skill(skill: "graphify")` per that contract. If it fails, skip silently — the feasibility read proceeds exactly as below, `qa-engineer`/`software-engineer` verdicts only. If it succeeds, query the graph for the plan's declared scope (what the named files/modules call, are called by, or depend on) and hold that as supplementary context for Step 9's `Key info` — this is a `task-orchestrator`-side supplement, not a change to what `qa-engineer`/`software-engineer` themselves read.

Invoke `qa-engineer` and `software-engineer` at their **Feasibility Assessment mode** — each independently assesses test/implementation feasibility against the plan.
```

- [ ] **Step 4: Update Step 9's `Key info` description**

Old text:
```
Write `STATE.md`: `Mode` (from Step 8), `Phase: PLAN`, `Handoff to: documentation-auditor (Doc Gate)` — matching Step 11 below, not `qa-engineer` directly, so a `/cairn-run-task` resume never skips the Doc Gate — `Status`, `Plan:` pointer (the file found in Step 1), `Ticket:` (from `docs/.tasks/TRACKER.md` if a row for this slug carries one — else `none`), `Worktree`, `Branch` (from Step 5), `Key info` (environment preflight tally from Step 4.5, feasibility notes from Step 7, `.harness/` suggestion flag from Step 6), `Harness flags: none`. Append one summarized line to `HISTORY.md`.
```

New text:
```
Write `STATE.md`: `Mode` (from Step 8), `Phase: PLAN`, `Handoff to: documentation-auditor (Doc Gate)` — matching Step 11 below, not `qa-engineer` directly, so a `/cairn-run-task` resume never skips the Doc Gate — `Status`, `Plan:` pointer (the file found in Step 1), `Ticket:` (from `docs/.tasks/TRACKER.md` if a row for this slug carries one — else `none`), `Worktree`, `Branch` (from Step 5), `Key info` (environment preflight tally from Step 4.5, feasibility notes and Graphify scope supplement from Step 7, `.harness/` suggestion flag from Step 6), `Harness flags: none`. Append one summarized line to `HISTORY.md`.
```

- [ ] **Step 5: Update START (Plan Mode item 6)**

Old text:
```
6. Invoke `qa-engineer` + `software-engineer` at their Feasibility Assessment mode, passing the plan path directly in opening context — `STATE.md` doesn't exist yet, and neither agent writes anything at this point (Step 7).
```

New text:
```
6. Attempt the Graphify scope supplement (soft-optional, skip silently if unavailable), then invoke `qa-engineer` + `software-engineer` at their Feasibility Assessment mode, passing the plan path directly in opening context — `STATE.md` doesn't exist yet, and neither agent writes anything at this point (Step 7).
```

- [ ] **Step 6: Verify structurally**

Run: `grep -n "graphify" agents/task-orchestrator.md`
Expected: matches in frontmatter description, HARD REQUIREMENTS, Step 7 (twice), Step 9's `Key info` description, and START item 6 — 6+ matches.

- [ ] **Step 7: Commit**

```bash
git add agents/task-orchestrator.md
git commit -m "Wire soft-optional Graphify scope supplement into task-orchestrator's feasibility step"
```

---

## Task 10: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: final behavior from Tasks 1-9 (must describe what actually landed).

- [ ] **Step 1: Add a `graphify-context` skill paragraph after the `coding-chain-shared` paragraph**

Old text:
```
**`coding-chain-shared` (skills/)** — not an invoked skill despite living under `skills/`: it's the shared **asset bundle** for the six coding-chain agents below. `assets/TRACKER.template.md`, `assets/task/{STATE,HISTORY,UAT}.template.md`, and `assets/harness/{architecture,standards,workflow,environment}.template.md` are the seed shapes for every file the chain creates, plus SKILL.md documenting the canonical `TRACKER.md` Status vocabulary, `STATE.md` Phase vocabulary, and the `Key info` (overwritten each phase) vs. `Harness flags` (append-only, accumulates to Publish) split. No agent calls `Skill(skill: "coding-chain-shared")` — `harness-engineer` and `project-manager` don't even carry `Skill` in `tools:`. Each agent `Read`s the one template it needs by path at the moment it seeds a file, always via `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/...`; a bare `skills/...` path would resolve against the *consuming* project's cwd, not the plugin's install location, and fail.
```

New text:
```
**`coding-chain-shared` (skills/)** — not an invoked skill despite living under `skills/`: it's the shared **asset bundle** for the six coding-chain agents below. `assets/TRACKER.template.md`, `assets/task/{STATE,HISTORY,UAT}.template.md`, and `assets/harness/{architecture,standards,workflow,environment}.template.md` are the seed shapes for every file the chain creates, plus SKILL.md documenting the canonical `TRACKER.md` Status vocabulary, `STATE.md` Phase vocabulary, and the `Key info` (overwritten each phase) vs. `Harness flags` (append-only, accumulates to Publish) split. No agent calls `Skill(skill: "coding-chain-shared")` — `harness-engineer` and `project-manager` don't even carry `Skill` in `tools:`. Each agent `Read`s the one template it needs by path at the moment it seeds a file, always via `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/...`; a bare `skills/...` path would resolve against the *consuming* project's cwd, not the plugin's install location, and fail.

**`graphify-context` (skills/)** — shared detection contract and query guidance for Graphify (`Graphify-Labs/graphify`), a vendored third-party code-graph tool never shipped or reimplemented by cairn. Soft-optional, not hard-required: `Skill(skill: "graphify-context")` always loads (it ships with the plugin); the guidance it documents then has the calling agent attempt `Skill(skill: "graphify")` itself, skipping silently and falling back to that agent's own `Read`/`Glob`/`Grep` approach if Graphify isn't installed. Loaded by eight agents at the point they'd otherwise reach straight for a plain file read: `codebase-auditor` (dead-code corroboration), `qa-auditor` (blast-radius supplement), `solution-architect` (structural pre-scan, non-ADR types), `documentation-auditor` (cross-reference corroboration), `harness-engineer` (Generate mode evidence source), `software-engineer` (general navigation, both modes), `qa-engineer` (code-under-test understanding), and `task-orchestrator` (Plan Mode feasibility scope). See `docs/.specs/2026-08-16-graphify-integration-design.md` for the full design and the tool-selection investigation.
```

- [ ] **Step 2: Update the `solution-architect` paragraph**

Old text:
```
**`solution-architect` (agents/)** — produces one technical artifact per invocation (Architecture Specification, Database Schema, API Specification, or an ADR), dependency-ordered (prd+user-flows → architecture-spec → db-schema/api-spec). ADRs are standalone, immutable after write (status-only updates). Terminal. Invokes `Skill(skill: "writer-shared")` then `Skill(skill: "solution-architecture-writing")` (plus `Skill(skill: "mermaid-diagrams")` for `architecture-spec.md`/`db-schema.md`/ADRs, not `api-spec.md`).
```

New text:
```
**`solution-architect` (agents/)** — produces one technical artifact per invocation (Architecture Specification, Database Schema, API Specification, or an ADR), dependency-ordered (prd+user-flows → architecture-spec → db-schema/api-spec). ADRs are standalone, immutable after write (status-only updates). Non-ADR document types run a soft-optional Graphify structural pre-scan before Discovery Phase (see `graphify-context`) — skips silently if Graphify isn't installed. Terminal. Invokes `Skill(skill: "writer-shared")` then `Skill(skill: "solution-architecture-writing")` (plus `Skill(skill: "mermaid-diagrams")` for `architecture-spec.md`/`db-schema.md`/ADRs, not `api-spec.md`).
```

- [ ] **Step 3: Update the `documentation-auditor` paragraph**

Old text:
```
**`documentation-auditor` (agents/)** — read-only validator across README/setup/API docs and requirements/design/architecture artifacts: existence, agent-roster accuracy (adapted for cairn's README bullet-list format), source accuracy, completeness, internal consistency, style, and cross-artifact traceability (e.g. every PRD `FR-###` must trace to a user story). Reports findings only — never auto-invokes a writer agent to fix them. Dispatched manually or by Claude, never automatically after a write.
```

New text:
```
**`documentation-auditor` (agents/)** — read-only validator across README/setup/API docs and requirements/design/architecture artifacts: existence, agent-roster accuracy (adapted for cairn's README bullet-list format), source accuracy, completeness, internal consistency, style, and cross-artifact traceability (e.g. every PRD `FR-###` must trace to a user story) — corroborated by a soft-optional Graphify query during the source-accuracy and cross-artifact checks when installed. Reports findings only — never auto-invokes a writer agent to fix them. Dispatched manually or by Claude, never automatically after a write.
```

- [ ] **Step 4: Update the `codebase-auditor` paragraph**

Old text:
```
**`codebase-auditor` (agents/)** — read-mostly (writes only its own report) snapshot of codebase health: best-effort tooling (`npm audit`/`outdated`, `tsc`, `eslint`, `pip-audit`, `mypy`, `ruff`, whatever the detected manifests justify — skipped silently, never failed, if unavailable), TODO/FIXME debt and secret-shaped-value grep sweeps (never reproduces a found secret's value, `file:line` only), and a grep-level dead-code pass labelled `INFO` unless corroborated by tooling. Writes one timestamped `docs/codebase-audit/YYYYMMDD-HHmmss-{project-name}.md`, no Update Mode. Distinct from `documentation-auditor`: that one is pure read-only and validates existing docs; this one analyzes source and produces a new artifact. Terminal, no skill loaded — ported from maestro's `codebase-auditor`, dropping its submodule-profiling interview, `codegraph` MCP dependency, and adaptive folder-splitting output (all YAGNI for cairn's single-file-snapshot convention).
```

New text:
```
**`codebase-auditor` (agents/)** — read-mostly (writes only its own report) snapshot of codebase health: best-effort tooling (`npm audit`/`outdated`, `tsc`, `eslint`, `pip-audit`, `mypy`, `ruff`, whatever the detected manifests justify — skipped silently, never failed, if unavailable), TODO/FIXME debt and secret-shaped-value grep sweeps (never reproduces a found secret's value, `file:line` only), and a grep-level dead-code pass labelled `INFO` unless corroborated by tooling or a soft-optional Graphify query (promotes to `LOW`/`MEDIUM` when it succeeds). Writes one timestamped `docs/codebase-audit/YYYYMMDD-HHmmss-{project-name}.md`, no Update Mode. Distinct from `documentation-auditor`: that one is pure read-only and validates existing docs; this one analyzes source and produces a new artifact. Loads `graphify-context` for its Step 5 dead-code pass, otherwise no skill loaded — ported from maestro's `codebase-auditor`, dropping its submodule-profiling interview and adaptive folder-splitting output (still YAGNI for cairn's single-file-snapshot convention); its hard-required `codegraph` MCP dependency was dropped for the same reason, then later revisited soft-optionally as the Graphify integration above. Terminal.
```

- [ ] **Step 5: Update the `harness-engineer` paragraph**

Old text:
```
**`harness-engineer` (agents/)** — generates/maintains `.harness/architecture.md`, `.harness/standards.md`, `.harness/workflow.md`, `.harness/environment.md` at the consuming project's root: the convention files `task-orchestrator`/`software-engineer`/`qa-engineer`/`qa-auditor` load to follow a codebase's own observed rules instead of generic defaults. The first three are prose guidance; `environment.md` is a typed, machine-checkable vocabulary (`tool-version`/`port-open`/`env-var-set`/escape-hatch `command`, each tagged `[blocking]`/`[warning]`) that `task-orchestrator`'s Environment Preflight step (see below) executes directly rather than reads as guidance. Generate mode derives draft rules from the codebase itself (or, on a genuinely fresh/near-empty repo, pre-fills from `docs/architecture/architecture-spec.md` when present and interviews for the rest — never invents a rule with no observed basis; `environment.md` always goes through the interview path on a fresh repo, since a spec doesn't declare exact tool-version floors or port numbers); Update mode diffs current conventions against what's codified and proposes amendments through the same gate. Every rule is confirmed via `AskUserQuestion` before writing; ~40-line cap per file. Invocable standalone any time, and auto-suggested (never forced) by `task-orchestrator` Plan Mode on first run if `.harness/` is absent entirely. Terminal, no skill loaded. See `docs/.specs/2026-08-15-coding-chain-environment-preflight-design.md` for the full design.
```

New text:
```
**`harness-engineer` (agents/)** — generates/maintains `.harness/architecture.md`, `.harness/standards.md`, `.harness/workflow.md`, `.harness/environment.md` at the consuming project's root: the convention files `task-orchestrator`/`software-engineer`/`qa-engineer`/`qa-auditor` load to follow a codebase's own observed rules instead of generic defaults. The first three are prose guidance; `environment.md` is a typed, machine-checkable vocabulary (`tool-version`/`port-open`/`env-var-set`/escape-hatch `command`, each tagged `[blocking]`/`[warning]`) that `task-orchestrator`'s Environment Preflight step (see below) executes directly rather than reads as guidance. Generate mode derives draft rules from the codebase itself (or, on a genuinely fresh/near-empty repo, pre-fills from `docs/architecture/architecture-spec.md` when present and interviews for the rest — never invents a rule with no observed basis; `environment.md` always goes through the interview path on a fresh repo, since a spec doesn't declare exact tool-version floors or port numbers), supplemented by a soft-optional Graphify query as an additional evidence source; Update mode diffs current conventions against what's codified and proposes amendments through the same gate. Every rule is confirmed via `AskUserQuestion` before writing; ~40-line cap per file. Invocable standalone any time, and auto-suggested (never forced) by `task-orchestrator` Plan Mode on first run if `.harness/` is absent entirely. Terminal, loads `graphify-context` in Generate mode's standard observation path. See `docs/.specs/2026-08-15-coding-chain-environment-preflight-design.md` for the full design.
```

- [ ] **Step 6: Update the `task-orchestrator` paragraph**

Old text:
```
**`task-orchestrator` (agents/)** — the coding chain's first and last agent. **Plan Mode** hard-requires an existing `docs/.plans/<slug>.md` (reads it as-is, never re-authors it), creates `docs/.tasks/YYYY-MM-DD-<slug>/`, runs an **Environment Preflight** against `.harness/environment.md` when present — its typed checks (tool versions, service reachability, env vars) gate branch/worktree creation on any failed `[blocking]` check (`AskUserQuestion` Attended / `HANDOFF NEEDED` Unattended, same shape as the feasibility gate below) — creates the branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")`, then runs a `qa-engineer` + `software-engineer` feasibility read, and hands off to `documentation-auditor` (Doc Gate) rather than straight to `qa-engineer` — a CRITICAL or HIGH finding *within the task's own scope* is resolved by the invoking main-thread session, not by `documentation-auditor` itself (which only reports, never writes or asks); unrelated pre-existing findings from that agent's whole-repo audit are noted, never blocking. That same session advances `STATE.md`'s `Phase` to `QA-RED` and sets `Handoff to: qa-engineer` once resolved. **Publish Mode** (triggered once `qa-auditor` → `documentation-auditor` Doc Post-Impl hands off clean, same ownership split) makes the consolidated commit, opens the PR/MR via `gh`/`glab`, writes the UAT checklist, surfaces one consolidated harness-drift/doc-drift question, and calls `project-manager`'s Status Sync to flip the ticket (`In Review`, then `Done` once merge is observed) — deleting the local plan draft only once ticket closure is actually observed. Supports Attended (default) and Unattended (tmux-detached, ported from maestro's `swarm.sh`) execution, pausing at `STATE.md`'s `Phase: HANDOFF NEEDED` wherever `AskUserQuestion` would otherwise fire. Never talks to `gh`/`glab`/ClickUp for ticket *status* directly — always through `project-manager`. Terminal (Publish). See `docs/.specs/2026-08-15-coding-chain-environment-preflight-design.md` for the Environment Preflight design.
```

New text:
```
**`task-orchestrator` (agents/)** — the coding chain's first and last agent. **Plan Mode** hard-requires an existing `docs/.plans/<slug>.md` (reads it as-is, never re-authors it), creates `docs/.tasks/YYYY-MM-DD-<slug>/`, runs an **Environment Preflight** against `.harness/environment.md` when present — its typed checks (tool versions, service reachability, env vars) gate branch/worktree creation on any failed `[blocking]` check (`AskUserQuestion` Attended / `HANDOFF NEEDED` Unattended, same shape as the feasibility gate below) — creates the branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")`, then runs a `qa-engineer` + `software-engineer` feasibility read (supplemented by a soft-optional Graphify scope query), and hands off to `documentation-auditor` (Doc Gate) rather than straight to `qa-engineer` — a CRITICAL or HIGH finding *within the task's own scope* is resolved by the invoking main-thread session, not by `documentation-auditor` itself (which only reports, never writes or asks); unrelated pre-existing findings from that agent's whole-repo audit are noted, never blocking. That same session advances `STATE.md`'s `Phase` to `QA-RED` and sets `Handoff to: qa-engineer` once resolved. **Publish Mode** (triggered once `qa-auditor` → `documentation-auditor` Doc Post-Impl hands off clean, same ownership split) makes the consolidated commit, opens the PR/MR via `gh`/`glab`, writes the UAT checklist, surfaces one consolidated harness-drift/doc-drift question, and calls `project-manager`'s Status Sync to flip the ticket (`In Review`, then `Done` once merge is observed) — deleting the local plan draft only once ticket closure is actually observed. Supports Attended (default) and Unattended (tmux-detached, ported from maestro's `swarm.sh`) execution, pausing at `STATE.md`'s `Phase: HANDOFF NEEDED` wherever `AskUserQuestion` would otherwise fire. Never talks to `gh`/`glab`/ClickUp for ticket *status* directly — always through `project-manager`. Terminal (Publish). See `docs/.specs/2026-08-15-coding-chain-environment-preflight-design.md` for the Environment Preflight design.
```

- [ ] **Step 7: Update the `qa-engineer` paragraph**

Old text:
```
**`qa-engineer` (agents/)** — writes the coding chain's tests. **Chain mode**: pre-implementation TDD red phase (hard-requires `Skill(skill: "superpowers:test-driven-development")`), writing failing tests against `docs/.plans/<slug>.md`'s scope before `software-engineer` exists to satisfy them, confirming each fails for the right reason before moving on. **Direct mode**: post-implementation, writing tests against a `software-engineer` Direct Mode fix that's already landed. Detects the test framework/commands from the repo itself, overridden by `.harness/standards.md`'s `## Testing` section when present. Coverage is best-effort and reported, never gating. Never writes or edits production code. Plus a third, read-only **Feasibility Assessment mode** — `task-orchestrator` Plan Mode Step 7, before `STATE.md` exists: the plan path arrives directly in opening context, and the agent returns a testability verdict having written nothing. A `qa-auditor` route-back or a `software-engineer` `TEST FIX REQUEST` re-enters as Chain mode regardless of the recorded `Phase`. Hands off (Chain → `software-engineer`; Direct → terminal, or back to `software-engineer` if a post-hoc test reveals the fix is incomplete).
```

New text:
```
**`qa-engineer` (agents/)** — writes the coding chain's tests. **Chain mode**: pre-implementation TDD red phase (hard-requires `Skill(skill: "superpowers:test-driven-development")`), writing failing tests against `docs/.plans/<slug>.md`'s scope before `software-engineer` exists to satisfy them, confirming each fails for the right reason before moving on. **Direct mode**: post-implementation, writing tests against a `software-engineer` Direct Mode fix that's already landed. Detects the test framework/commands from the repo itself, overridden by `.harness/standards.md`'s `## Testing` section when present. A soft-optional Graphify query informs which code paths need coverage before either mode's tests are written. Coverage is best-effort and reported, never gating. Never writes or edits production code. Plus a third, read-only **Feasibility Assessment mode** — `task-orchestrator` Plan Mode Step 7, before `STATE.md` exists: the plan path arrives directly in opening context, and the agent returns a testability verdict having written nothing. A `qa-auditor` route-back or a `software-engineer` `TEST FIX REQUEST` re-enters as Chain mode regardless of the recorded `Phase`. Hands off (Chain → `software-engineer`; Direct → terminal, or back to `software-engineer` if a post-hoc test reveals the fix is incomplete).
```

- [ ] **Step 8: Update the `software-engineer` paragraph**

Old text:
```
**`software-engineer` (agents/)** — implements code in the coding chain. Stack-agnostic — no per-stack guide skill; infers conventions from the repo itself plus `.harness/architecture.md`/`standards.md` when present. UI-facing tasks in either mode run a soft-optional Frontend Polish Pass (Anthropic Frontend Design, Taste Skill, and vendored Emil Kowalski skills, whichever are present) before implementation begins — same skip-silently-if-absent treatment as `product-designer`'s Design Quality Pass, gated to tasks the plan/request/touched-files actually identify as UI work. **Chain mode**: TDD green phase, turning `qa-engineer`'s failing tests passing, raising a `TEST FIX REQUEST` back to `qa-engineer` rather than force-implementing to satisfy a test that looks wrong. **Direct mode**: a small, already-scoped bug-fix/decision implemented directly on the current branch — no worktree/branch/commit/PR automation. Never writes or edits test files in either direction. Same read-only **Feasibility Assessment mode** as `qa-engineer` for Plan Mode Step 7 (plan path in opening context, no `STATE.md`, implementability verdict only, nothing written), and the same Chain-mode-regardless-of-`Phase` rule on a fix-cycle re-entry. Runs at `opus`. Hands off (Chain → `qa-auditor`; Direct → `qa-engineer` for post-hoc tests).
```

New text:
```
**`software-engineer` (agents/)** — implements code in the coding chain. Stack-agnostic — no per-stack guide skill; infers conventions from the repo itself plus `.harness/architecture.md`/`standards.md` when present. UI-facing tasks in either mode run a soft-optional Frontend Polish Pass (Anthropic Frontend Design, Taste Skill, and vendored Emil Kowalski skills, whichever are present) before implementation begins — same skip-silently-if-absent treatment as `product-designer`'s Design Quality Pass, gated to tasks the plan/request/touched-files actually identify as UI work. Both modes also run a soft-optional Graphify pass for general code navigation, ungated by UI-facing status. **Chain mode**: TDD green phase, turning `qa-engineer`'s failing tests passing, raising a `TEST FIX REQUEST` back to `qa-engineer` rather than force-implementing to satisfy a test that looks wrong. **Direct mode**: a small, already-scoped bug-fix/decision implemented directly on the current branch — no worktree/branch/commit/PR automation. Never writes or edits test files in either direction. Same read-only **Feasibility Assessment mode** as `qa-engineer` for Plan Mode Step 7 (plan path in opening context, no `STATE.md`, implementability verdict only, nothing written), and the same Chain-mode-regardless-of-`Phase` rule on a fix-cycle re-entry. Runs at `opus`. Hands off (Chain → `qa-auditor`; Direct → `qa-engineer` for post-hoc tests).
```

- [ ] **Step 9: Update the `qa-auditor` paragraph**

Old text:
```
**`qa-auditor` (agents/)** — the coding chain's independent post-implementation re-verification step, Chain-flow only (Direct flow ends at `qa-engineer` and never reaches it). Reruns scoped tests (task-affected files only — not the full suite), a best-effort coverage report, a code-quality review, and conditional security/performance/dependency checks (triggered by a tagged concern or a new dependency, never run as a blanket default). Loads `.harness/architecture.md`/`standards.md` when present and raises a `HIGH` finding — routed to `software-engineer` — only for a violation on a line `git diff` (against the task's base commit) shows as added or modified by this task; a pre-existing violation, even inside an otherwise-edited file, is left untouched and noted `INFO` at most. Routes a broken test back to `qa-engineer`, an implementation bug or `HIGH`+ finding back to `software-engineer`; on a clean pass, hands off to `documentation-auditor` (Doc Post-Impl).
```

New text:
```
**`qa-auditor` (agents/)** — the coding chain's independent post-implementation re-verification step, Chain-flow only (Direct flow ends at `qa-engineer` and never reaches it). Reruns scoped tests (task-affected files only — not the full suite), a best-effort coverage report, a code-quality review, and conditional security/performance/dependency checks (triggered by a tagged concern or a new dependency, never run as a blanket default). A soft-optional Graphify blast-radius query supplements task-affected scoping with downstream impact a diff alone doesn't show, never promoted past `INFO` outside the task's changed lines. Loads `.harness/architecture.md`/`standards.md` when present and raises a `HIGH` finding — routed to `software-engineer` — only for a violation on a line `git diff` (against the task's base commit) shows as added or modified by this task; a pre-existing violation, even inside an otherwise-edited file, is left untouched and noted `INFO` at most. Routes a broken test back to `qa-engineer`, an implementation bug or `HIGH`+ finding back to `software-engineer`; on a clean pass, hands off to `documentation-auditor` (Doc Post-Impl).
```

- [ ] **Step 10: Verify structurally**

Run: `grep -c "Graphify\|graphify" CLAUDE.md`
Expected: at least 10 (the new `graphify-context` paragraph plus one mention in each of the 8 agent paragraphs, counting the codebase-auditor paragraph's two mentions).

- [ ] **Step 11: Commit**

```bash
git add CLAUDE.md
git commit -m "Document graphify-context and its 8 agent integration points in CLAUDE.md"
```

---

## Task 11: Version bump

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Bump the version (minor — new feature, per `CLAUDE.md`'s Versioning section)**

Old text:
```json
  "version": "0.13.0",
```

New text:
```json
  "version": "0.14.0",
```

- [ ] **Step 2: Verify**

Run: `claude plugin validate . --strict`
Expected: passes (same check CI runs on every push).

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "Bump to 0.14.0 for the Graphify integration"
```

---

## Task 12: End-to-end verification

**Files:**
- None modified — this task only runs commands and inspects output, per `CLAUDE.md`'s "Testing a command end-to-end" convention (no unit test framework covers agent-prompt behavior in this repo).

- [ ] **Step 1: Set up a clean scratch project with Graphify absent**

```bash
mkdir -p /tmp/cairn-graphify-probe && cd /tmp/cairn-graphify-probe && git init -q
mkdir -p src && printf 'export function add(a, b) { return a + b }\n' > src/math.js
```

- [ ] **Step 2: Confirm `codebase-auditor` completes without error when Graphify is absent**

```bash
claude -p "/cairn:cairn-doctor" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```

Expected: `/cairn-doctor` still completes normally (this run is a smoke test that the plugin as a whole still validates and loads cleanly after the Task 1-11 edits — `/cairn-doctor` itself has no Graphify-specific check added by this plan).

```bash
claude -p "Audit this codebase for dead code and quality issues" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```

Expected: dispatches `codebase-auditor`, completes without error or `ABORT`, writes `docs/codebase-audit/YYYYMMDD-HHmmss-*.md`. Since Graphify isn't installed in this scratch environment, the report's dead-code findings should read as ordinary grep-level `INFO` — no crash from the `Skill(skill: "graphify-context")` / `Skill(skill: "graphify")` attempt.

- [ ] **Step 3: Confirm `documentation-auditor` completes without error when Graphify is absent**

```bash
claude -p "Audit the documentation in this project" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```

Expected: dispatches `documentation-auditor`, completes without error, emits an `AUDIT REPORT` and `COMPLETION` block — confirms the new Graphify-Assisted Cross-Reference Check step skips silently rather than blocking the run.

- [ ] **Step 4: Confirm `harness-engineer` completes without error when Graphify is absent**

```bash
claude -p "Generate harness rules for this repo" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```

Expected: dispatches `harness-engineer` Generate mode, reaches the `AskUserQuestion` confirm gate (or reports it would, in non-interactive `-p` mode) without erroring on the Graphify attempt in Step 3.

- [ ] **Step 5: Verify no `ABORT` text appears anywhere in the 8 modified agent files for a Graphify-related trigger**

```bash
cd /Users/jaysondelosreyes/cairn
grep -B2 -A2 -i "graphify" agents/codebase-auditor.md agents/qa-auditor.md agents/solution-architect.md agents/documentation-auditor.md agents/harness-engineer.md agents/software-engineer.md agents/qa-engineer.md agents/task-orchestrator.md | grep -i "ABORT"
```

Expected: no output — confirms none of the 8 Graphify integration points are ever paired with `ABORT` language.

- [ ] **Step 6: Clean up the scratch project**

```bash
rm -rf /tmp/cairn-graphify-probe
```

- [ ] **Step 7: Report the verification results** (no commit — this task produces no repo changes)
