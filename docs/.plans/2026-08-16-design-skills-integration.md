# Design-Skill Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire three soft-optional third-party design/frontend skills (Taste Skill, Emil Kowalski skills, Anthropic Frontend Design) into `product-designer` and `software-engineer`, plus a report-only recommended-plugin check in `/cairn-doctor` — none hard-required, all skip silently when absent.

**Architecture:** `product-designer` gains a Design Quality Pass (mirrors the existing hard-required Impeccable Shape Pass, but soft-optional) for `ui-layout-spec.md`/`design-system.md`. `software-engineer` gains a Frontend Polish Pass gated to UI-facing tasks only, plus the `Skill` tool it currently lacks. `/cairn-doctor` gains two new report-only checks alongside its existing `superpowers` check. `CLAUDE.md`'s architecture narrative and the plugin version are updated to match.

**Tech Stack:** Markdown agent/skill/command prose files (no application code, no test framework — this repo has no unit tests over agent prompt behavior). Verification is structural (`grep`/`Glob` presence checks) plus headless end-to-end dispatch per `CLAUDE.md`'s "Testing a command end-to-end" convention.

**Spec:** `docs/.specs/2026-08-16-design-skills-integration-design.md`

## Global Constraints

- Taste Skill invocation: exactly `Skill(skill: "taste-skill:design-taste-frontend")` — plugin `taste-skill`, marketplace `taste-skill` (repo `Leonxlnx/taste-skill`).
- Anthropic Frontend Design invocation: exactly `Skill(skill: "frontend-design:frontend-design")` — plugin `frontend-design`, marketplace `claude-code-plugins`.
- Emil Kowalski skills presence check: exactly `Glob(.claude/skills/emil-design-eng/SKILL.md)` — never `Bash ls`/`find`/`test`, matching the existing Impeccable check's tool discipline.
- Install commands (verbatim, used in doctor suggestions):
  - Taste Skill: `/plugin marketplace add Leonxlnx/taste-skill` then `/plugin install taste-skill@taste-skill`
  - Anthropic Frontend Design: `/plugin marketplace add anthropics/claude-code` then `/plugin install frontend-design@claude-code-plugins`
  - Emil Kowalski skills: `npx skills@latest add emilkowalski/skills`
- Nothing added by this plan is hard-required. Every new check is try-and-skip-silently or `Glob`-and-skip-silently — never `ABORT`. Impeccable's existing hard-require in `agents/product-designer.md` and `skills/product-design-writing/SKILL.md` is unchanged.
- UI UX Pro Max is explicitly out of scope — do not add it anywhere in this plan.

---

## Task 1: Design Quality Pass content — `skills/product-design-writing/SKILL.md`

**Files:**
- Modify: `skills/product-design-writing/SKILL.md`

**Interfaces:**
- Produces: a `## Design Quality Pass (ui-layout-spec.md and design-system.md only)` section that `agents/product-designer.md` (Task 2) points to by name, mirroring how it already points to `## Impeccable Shape Pass (ui-layout-spec.md only)`.

- [ ] **Step 1: Update the frontmatter description to mention the new pass**

```diff
---
name: product-design-writing
-description: Discovery dimensions, artifact formats, Reference Artifact Intake, and the Impeccable Shape Pass for the 3 design documents (ux-spec, ui-layout-spec, design-system). Loaded by product-designer alongside writer-shared.
+description: Discovery dimensions, artifact formats, Reference Artifact Intake, the Impeccable Shape Pass, and the Design Quality Pass for the 3 design documents (ux-spec, ui-layout-spec, design-system). Loaded by product-designer alongside writer-shared.
---
```

- [ ] **Step 2: Update the Dependency Chain note to mention the soft-optional pass**

Old text (line 20):
```
`ui-layout-spec.md` additionally requires Impeccable to be vendored — see Impeccable Shape Pass below; this is a separate, additional gate on top of the upstream document check.
```

New text:
```
`ui-layout-spec.md` additionally requires Impeccable to be vendored — see Impeccable Shape Pass below; this is a separate, additional gate on top of the upstream document check. `ui-layout-spec.md` and `design-system.md` also run a soft-optional Design Quality Pass (Taste Skill) — see Design Quality Pass below; unlike Impeccable, nothing aborts if it's absent.
```

- [ ] **Step 3: Fix the Reference Artifact Intake ordering description**

Old text (line 364):
```
Runs after Skill Loading (and after Impeccable Shape Pass for `ui-layout-spec.md`), before Discovery Phase, when the opening context includes a `Reference Artifact: <path-or-url>` field. Skip entirely for `ux-spec.md` and when no such field is present.
```

New text:
```
Runs after Skill Loading (and after Impeccable Shape Pass and Design Quality Pass, for the document types those run on), before Discovery Phase, when the opening context includes a `Reference Artifact: <path-or-url>` field. Skip entirely for `ux-spec.md` and when no such field is present.
```

- [ ] **Step 4: Append the Design Quality Pass section**

Add after the existing `## Impeccable Shape Pass (ui-layout-spec.md only)` section (end of file, after its step 6 / "Proceed to Discovery Phase..." line):

```markdown

---

## Design Quality Pass (ui-layout-spec.md and design-system.md only)

Taste Skill is a vendored third-party design-guidance plugin, not part of cairn — cairn never ships or vendors it (see the spec's Design Quality Pass section for the full rationale). Unlike the Impeccable Shape Pass, this is **soft-optional**: nothing aborts if Taste Skill isn't installed.

Runs after Skill Loading, after the Impeccable Shape Pass when producing `ui-layout-spec.md`, before Reference Artifact Intake and Discovery Phase, when producing `ui-layout-spec.md` or `design-system.md`. Skip entirely for `ux-spec.md`.

1. Attempt `Skill(skill: "taste-skill:design-taste-frontend")` once.
2. **If the invocation fails** (plugin not installed) — skip silently and proceed to the next step (Reference Artifact Intake, or Discovery Phase directly). Do NOT `ABORT`, do NOT tell the user anything beyond the existing `Flags` line at COMPLETION.
3. **If it succeeds** — treat its design-direction output purely as **pre-filled input** to the upcoming Discovery Phase, same treatment as the Impeccable Shape Pass's `shape` output and Reference Artifact Intake's pre-fills (propose the pre-filled answer per discovery dimension, ask the user to confirm or correct, never assume silently). Taste Skill's own stated scope is landing pages, portfolios, and redesigns — not dashboards, data tables, or multi-step product UI; apply its direction only where it actually fits the artifact being produced, otherwise note the mismatch in your own reasoning and proceed without it.
4. Proceed to Reference Artifact Intake (if a `Reference Artifact:` field is present) or Discovery Phase directly.
```

- [ ] **Step 5: Verify structurally**

Run: `grep -n "Design Quality Pass" skills/product-design-writing/SKILL.md`
Expected: 4 matches (frontmatter description, dependency-chain note, Reference Artifact Intake note, and the new section heading + its body references).

- [ ] **Step 6: Commit**

```bash
git add skills/product-design-writing/SKILL.md
git commit -m "Add soft-optional Design Quality Pass content to product-design-writing skill"
```

---

## Task 2: Wire Design Quality Pass into `agents/product-designer.md`

**Files:**
- Modify: `agents/product-designer.md`

**Interfaces:**
- Consumes: `## Design Quality Pass (ui-layout-spec.md and design-system.md only)` from Task 1.

- [ ] **Step 1: Update the frontmatter `description` field**

Old text (line 3, end of the Impeccable sentence):
```
UI Layout Specification requires Impeccable to be vendored in the project (.claude/skills/impeccable) — aborts that run if absent; invokes it once for pre-fill input into its own discovery, not as a second interview. Invoke when requirements are documented and the user wants to define user interaction and interface structure."
```

New text:
```
UI Layout Specification requires Impeccable to be vendored in the project (.claude/skills/impeccable) — aborts that run if absent; invokes it once for pre-fill input into its own discovery, not as a second interview. UI Layout Specification and Design System also run a soft-optional Design Quality Pass (Taste Skill, if the plugin is installed) — skips silently if absent, never aborts. Invoke when requirements are documented and the user wants to define user interaction and interface structure."
```

- [ ] **Step 2: Add a HARD REQUIREMENTS bullet directly after the existing Impeccable bullet**

Old text (line 56-57 region — insert after the `Bash` bullet, before the closing `---`):
```
- Impeccable is hard-required for `ui-layout-spec.md` only (see IMPECCABLE SHAPE PASS below) — `ux-spec.md` and `design-system.md` are unaffected by its presence or absence.
- `Bash` is granted for one purpose only: running Impeccable's own required setup scripts (e.g. `node .claude/skills/impeccable/scripts/context.mjs`) when producing `ui-layout-spec.md` — never for general shell use. This explicitly includes the Impeccable existence check itself: checking whether `.claude/skills/impeccable/SKILL.md` exists MUST use `Glob`, never `Bash ls`/`find`/`test` — `Bash` only runs Impeccable's setup scripts, and only after `Glob` has already confirmed Impeccable is present. Do not substitute `Read` or any other tool for `Glob`, and do not assume `Glob` is unavailable without actually attempting the call — if it genuinely errors, report the exact error rather than silently switching tools.
```

New text (adds one bullet after the `Bash` bullet):
```
- Impeccable is hard-required for `ui-layout-spec.md` only (see IMPECCABLE SHAPE PASS below) — `ux-spec.md` and `design-system.md` are unaffected by its presence or absence.
- `Bash` is granted for one purpose only: running Impeccable's own required setup scripts (e.g. `node .claude/skills/impeccable/scripts/context.mjs`) when producing `ui-layout-spec.md` — never for general shell use. This explicitly includes the Impeccable existence check itself: checking whether `.claude/skills/impeccable/SKILL.md` exists MUST use `Glob`, never `Bash ls`/`find`/`test` — `Bash` only runs Impeccable's setup scripts, and only after `Glob` has already confirmed Impeccable is present. Do not substitute `Read` or any other tool for `Glob`, and do not assume `Glob` is unavailable without actually attempting the call — if it genuinely errors, report the exact error rather than silently switching tools.
- Taste Skill (Design Quality Pass, see below) is soft-optional for `ui-layout-spec.md` and `design-system.md` — `ux-spec.md` is unaffected. Never `ABORT` on its absence; a failed `Skill(skill: "taste-skill:design-taste-frontend")` invocation just means skip the pass and continue.
```

- [ ] **Step 3: Insert the new `## DESIGN QUALITY PASS` section**

Add immediately after the existing `## IMPECCABLE SHAPE PASS (ui-layout-spec.md ONLY)` section and before `## REFERENCE ARTIFACT INTAKE (ui-layout-spec.md AND design-system.md ONLY)`:

```markdown
## DESIGN QUALITY PASS (ui-layout-spec.md AND design-system.md ONLY)

Runs after Skill Loading (and after Impeccable Shape Pass, when producing `ui-layout-spec.md`), before Reference Artifact Intake and Discovery Phase, when producing `ui-layout-spec.md` or `design-system.md`. Full procedure defined in `skills/product-design-writing/SKILL.md` → Design Quality Pass. Do NOT run this step for `ux-spec.md`.

Unlike the Impeccable Shape Pass, this is soft-optional: attempt `Skill(skill: "taste-skill:design-taste-frontend")`; if it fails, skip silently and continue — never `ABORT`.

---
```

- [ ] **Step 4: Update the START section's step ordering**

Old text (steps 3-4):
```
3. For `ui-layout-spec.md` only: run **Impeccable Shape Pass** — but only after step 2's `Skill(skill: "product-design-writing")` call has actually completed. Never jump ahead to the Impeccable existence check before Skill Loading finishes.
4. For `ui-layout-spec.md`/`design-system.md`: run **Reference Artifact Intake** if a `Reference Artifact:` field is present.
5. Run **Discovery Phase** → **Draft Phase** (Write tool, invoking `Skill(skill: "mermaid-diagrams")` first if producing `ux-spec.md`).
6. Apply **Final Review Phase**, then emit **COMPLETION**.
```

New text (renumbered, one step inserted):
```
3. For `ui-layout-spec.md` only: run **Impeccable Shape Pass** — but only after step 2's `Skill(skill: "product-design-writing")` call has actually completed. Never jump ahead to the Impeccable existence check before Skill Loading finishes.
4. For `ui-layout-spec.md`/`design-system.md`: run **Design Quality Pass** (soft-optional — skip silently if Taste Skill isn't installed).
5. For `ui-layout-spec.md`/`design-system.md`: run **Reference Artifact Intake** if a `Reference Artifact:` field is present.
6. Run **Discovery Phase** → **Draft Phase** (Write tool, invoking `Skill(skill: "mermaid-diagrams")` first if producing `ux-spec.md`).
7. Apply **Final Review Phase**, then emit **COMPLETION**.
```

- [ ] **Step 5: Update the COMPLETION `Flags` line**

Old text:
```
  Flags   → [Impeccable pre-fill applied | Reference Artifact used | none]
```

New text:
```
  Flags   → [Impeccable pre-fill applied | Taste Skill pre-fill applied | Reference Artifact used | none]
```

- [ ] **Step 6: Verify structurally**

Run: `grep -n "DESIGN QUALITY PASS\|Taste Skill\|taste-skill:design-taste-frontend" agents/product-designer.md`
Expected: matches in frontmatter description, HARD REQUIREMENTS, the new section heading, START step 4, and the COMPLETION Flags line — 5+ matches, none of them adjacent to the word `ABORT`.

Run: `grep -c "ABORT" agents/product-designer.md`
Expected: same count as before this task (Taste Skill introduces zero new `ABORT` occurrences) — confirm by checking the only `ABORT` mentions remaining are the pre-existing Impeccable one in EXIT & DERAILMENT HANDLING.

- [ ] **Step 7: Commit**

```bash
git add agents/product-designer.md
git commit -m "Wire soft-optional Design Quality Pass into product-designer"
```

---

## Task 3: Add `Skill` tool and Frontend Polish Pass to `agents/software-engineer.md`

**Files:**
- Modify: `agents/software-engineer.md`

**Interfaces:**
- Consumes: nothing from earlier tasks (independent of Tasks 1-2).
- Produces: a `Frontend Polish Pass` step referenced by Task 4's doctor check narrative and Task 5's `CLAUDE.md` update.

- [ ] **Step 1: Add `Skill` to the frontmatter `tools:` line**

Old text (line 4):
```
tools: Read, Glob, Grep, Bash, Write, Edit
```

New text:
```
tools: Read, Glob, Grep, Bash, Write, Edit, Skill
```

- [ ] **Step 2: Update the frontmatter `description` field**

Old text (line 3, first sentence):
```
description: "Use this agent to implement code in the coding chain — stack-agnostic, no per-stack guide skills, following whatever conventions exist in the repo plus .harness/architecture.md and standards.md when present. Two working modes: Chain (from qa-engineer's failing tests, TDD green phase, hands off to qa-auditor) and Direct (small bug-fix/decision requests with no task file, works on the current branch, no automated commit/PR — hands off to qa-engineer post-hoc). Plus a read-only Feasibility Assessment (plan path passed directly in opening context, before STATE.md exists) for task-orchestrator Plan Mode Step 7.
```

New text:
```
description: "Use this agent to implement code in the coding chain — stack-agnostic, no per-stack guide skills, following whatever conventions exist in the repo plus .harness/architecture.md and standards.md when present. Two working modes: Chain (from qa-engineer's failing tests, TDD green phase, hands off to qa-auditor) and Direct (small bug-fix/decision requests with no task file, works on the current branch, no automated commit/PR — hands off to qa-engineer post-hoc). UI-facing tasks in either mode run a soft-optional Frontend Polish Pass (Anthropic Frontend Design, Taste Skill, Emil Kowalski skills — whichever are installed) before implementation. Plus a read-only Feasibility Assessment (plan path passed directly in opening context, before STATE.md exists) for task-orchestrator Plan Mode Step 7.
```

- [ ] **Step 3: Add a HARD REQUIREMENTS bullet**

Add after the existing `MAY emit one optional HARNESS FLAG:` bullet and before the `Feasibility Assessment mode: NEVER read STATE.md...` bullet:

```
- Frontend Polish Pass (Step 3.5) is soft-optional and gated to UI-facing tasks only — never runs in Feasibility Assessment mode, never aborts on a missing skill. Each of its three checks (Anthropic Frontend Design, Taste Skill, Emil Kowalski skills) is independent; any subset may be present.
```

- [ ] **Step 4: Insert the new `### Step 3.5 — Frontend Polish Pass` section**

Add immediately after the existing `### Step 3 — .harness/ load (Chain and Direct modes)` section and before `### Step 4 — Direct mode: load context`:

```markdown
### Step 3.5 — Frontend Polish Pass (Chain and Direct modes, UI-facing tasks only)

Determine once, before Step 5, whether this task is UI-facing — never re-evaluate mid-task:

- **Chain mode:** the plan (`docs/.plans/<slug>.md`, already read in Step 2) describes UI/frontend/component/visual/interaction work, or names `docs/design/ui-layout-spec.md` / `docs/design/design-system.md` as source material.
- **Direct mode:** the opening request's wording is UI-facing, or the files it names/implies match UI file types (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, `.scss`, template/markup files).

If not UI-facing, skip this step entirely and proceed to Step 5.

If UI-facing, run each of the following independently — none blocks the others, all skip silently on failure/absence:

1. Attempt `Skill(skill: "frontend-design:frontend-design")` (Anthropic Frontend Design). On failure, skip silently.
2. Attempt `Skill(skill: "taste-skill:design-taste-frontend")` (Taste Skill). On failure, skip silently. Apply its direction only where its own stated scope fits (landing/portfolio/marketing-style UI, not dashboards/data tables/multi-step product flows) — judgment call, not a hard filter.
3. `Glob(.claude/skills/emil-design-eng/SKILL.md)`. If present, `Read` it, and `Read` any of its 9 sibling skills (`animate`, `review-animations`, `improve-animations`, `find-animation-opportunities`, `animation-vocabulary`, `apple-design`, `pick-ui-library`, `prototype`, `ask-sonner`, all vendored alongside it under `.claude/skills/`) relevant to the specific work at hand — e.g. `animate` when building a new animation, `review-animations` as a self-check once animation code is written. If absent, skip silently.

If none of the three are present, this step is a no-op — proceed to Step 5 exactly as if it hadn't been UI-facing. Never emit a `HARNESS FLAG:` for a missing skill here — that mechanism is for undocumented codebase conventions, not third-party skill availability.
```

- [ ] **Step 5: Update both PHASE HANDOFF blocks' `Flags` lines**

Old text (Chain mode block):
```
Result
  Status  → ✅ COMPLETE
  Flags   → [HARNESS FLAG: <note> | none]

PHASE HANDOFF → qa-auditor
```

New text:
```
Result
  Status  → ✅ COMPLETE
  Flags   → [HARNESS FLAG: <note> | none]
  Frontend Polish → [n of 3 applied | not UI-facing, skipped]

PHASE HANDOFF → qa-auditor
```

Old text (Direct mode block):
```
Result
  Status  → ✅ COMPLETE
  Flags   → [HARNESS FLAG: <note> | none]

PHASE HANDOFF → qa-engineer
```

New text:
```
Result
  Status  → ✅ COMPLETE
  Flags   → [HARNESS FLAG: <note> | none]
  Frontend Polish → [n of 3 applied | not UI-facing, skipped]

PHASE HANDOFF → qa-engineer
```

(The `TEST FIX REQUEST` block keeps its existing `Result` shape unchanged — it fires before Step 5/implementation review, not after a Frontend Polish Pass outcome worth reporting.)

- [ ] **Step 6: Update the START section**

Old text (steps 3-4):
```
3. `Glob`-check `.harness/architecture.md` and `standards.md`, read if present (Step 3).
4. Implement — green phase (Step 5, Chain) or scoped fix (Step 5, Direct). Raise a `TEST FIX REQUEST` instead of forcing a bad test, if warranted.
```

New text:
```
3. `Glob`-check `.harness/architecture.md` and `standards.md`, read if present (Step 3).
4. If the task is UI-facing, run the **Frontend Polish Pass** (Step 3.5) — soft-optional, skip silently on any missing skill; skip the whole step if not UI-facing.
5. Implement — green phase (Step 5, Chain) or scoped fix (Step 5, Direct). Raise a `TEST FIX REQUEST` instead of forcing a bad test, if warranted.
6. Emit an optional `HARNESS FLAG:` note if warranted (Step 6).
7. Chain mode only: update `STATE.md` — appending any `HARNESS FLAG:` to `Harness flags`, not `Key info` — and append `HISTORY.md` (Step 7).
8. Emit the mode-appropriate **PHASE HANDOFF** block.
```

- [ ] **Step 7: Verify structurally**

Run: `grep -n "Skill" agents/software-engineer.md | head -1`
Expected: first match is the frontmatter `tools:` line, confirming `Skill` was added there.

Run: `grep -n "Frontend Polish Pass\|frontend-design:frontend-design\|taste-skill:design-taste-frontend\|emil-design-eng" agents/software-engineer.md`
Expected: matches in description, HARD REQUIREMENTS, the new Step 3.5 section, both PHASE HANDOFF blocks, and START — no `ABORT` adjacent to any of them.

- [ ] **Step 8: Commit**

```bash
git add agents/software-engineer.md
git commit -m "Add Skill tool and soft-optional Frontend Polish Pass to software-engineer"
```

---

## Task 4: Extend `/cairn-doctor` with two new recommended-plugin checks

**Files:**
- Modify: `commands/cairn-doctor.md`

**Interfaces:**
- Consumes: the install-command strings from Global Constraints (must match verbatim).

- [ ] **Step 1: Insert two new numbered steps after the existing Step 2 (`superpowers` plugin), renumbering everything after**

Old text (full current numbering, Steps 2-6):
```
2. **`superpowers` plugin.** `idea-explorer` hard-requires it (loads `superpowers:brainstorming` directly, no fallback). Check via `claude plugin list --json`: is `superpowers@claude-plugins-official` present, `enabled: true`, and scoped to this project (`scope == "user"` or `projectPath` matches cwd)?
   - Installed and enabled → report `idea-explorer` fully functional.
   - Not installed/enabled → report `idea-explorer` will abort if dispatched. Suggest the install commands as text — don't run them; installing a plugin on the user's behalf needs their explicit action, not a doctor auto-fix.

3. **CLAUDE.md entrypoint wiring.** If the project has a root `CLAUDE.md`, check for a line that is *exactly* `<!-- cairn:start -->` (the whole line, nothing else on it — not just the text appearing somewhere, e.g. inside a code span in prose describing this mechanism).
   - Present → report wired.
   - Absent → report not wired. This is informational, not a problem — mention `/cairn-setup` if they want it, don't suggest anything's broken.
   - No `CLAUDE.md` at all → report not applicable.

4. **`.cairn/` self-ignoring.** Only relevant if `.cairn/` exists in the project (created by `/cairn-dashboard` or the `log-version.sh` hook).
   - `.cairn/.gitignore` exists and contains `*` → report it's correctly self-ignored.
   - Missing or wrong content → write a `.cairn/.gitignore` containing a single `*`, report that you fixed it. This never touches the project's own root `.gitignore` — `.cairn/` ignores itself.
   - `.cairn/` doesn't exist: nothing to do here.

5. **Stale dashboard lockfile.** If `.cairn/usage-dashboard.pid` exists, check whether the PID in it is still alive.
   - Alive → report the dashboard is running, with its URL.
   - Dead → remove the stale lockfile, report that you cleaned it up (otherwise `/cairn-dashboard` would think one's already running when it isn't).

6. **Summary.** One short report covering all five checks and what (if anything) was changed.
```

New text:
```
2. **`superpowers` plugin.** `idea-explorer` hard-requires it (loads `superpowers:brainstorming` directly, no fallback). Check via `claude plugin list --json`: is `superpowers@claude-plugins-official` present, `enabled: true`, and scoped to this project (`scope == "user"` or `projectPath` matches cwd)?
   - Installed and enabled → report `idea-explorer` fully functional.
   - Not installed/enabled → report `idea-explorer` will abort if dispatched. Suggest the install commands as text — don't run them; installing a plugin on the user's behalf needs their explicit action, not a doctor auto-fix.

3. **Taste Skill / Anthropic Frontend Design plugins.** `product-designer`'s Design Quality Pass and `software-engineer`'s Frontend Polish Pass both use these when present — neither is required, this check is purely informational. Check via `claude plugin list --json`: is `taste-skill@taste-skill` present/`enabled: true`? Is `frontend-design@claude-code-plugins` present/`enabled: true`?
   - Both installed and enabled → report both passes have full access to them.
   - Either missing → report which one, note which pass(es) lose that input (never an abort — both passes are soft-optional), and suggest the real install commands as text, never run them:
     - Taste Skill: `/plugin marketplace add Leonxlnx/taste-skill` then `/plugin install taste-skill@taste-skill`
     - Anthropic Frontend Design: `/plugin marketplace add anthropics/claude-code` then `/plugin install frontend-design@claude-code-plugins`

4. **Emil Kowalski skills.** `software-engineer`'s Frontend Polish Pass uses these when vendored — not required. Check via `Glob(.claude/skills/emil-design-eng/SKILL.md)` in the current project.
   - Present → report the Frontend Polish Pass has access to it.
   - Absent → report it's not vendored here and suggest `npx skills@latest add emilkowalski/skills` as text, never run it.

5. **CLAUDE.md entrypoint wiring.** If the project has a root `CLAUDE.md`, check for a line that is *exactly* `<!-- cairn:start -->` (the whole line, nothing else on it — not just the text appearing somewhere, e.g. inside a code span in prose describing this mechanism).
   - Present → report wired.
   - Absent → report not wired. This is informational, not a problem — mention `/cairn-setup` if they want it, don't suggest anything's broken.
   - No `CLAUDE.md` at all → report not applicable.

6. **`.cairn/` self-ignoring.** Only relevant if `.cairn/` exists in the project (created by `/cairn-dashboard` or the `log-version.sh` hook).
   - `.cairn/.gitignore` exists and contains `*` → report it's correctly self-ignored.
   - Missing or wrong content → write a `.cairn/.gitignore` containing a single `*`, report that you fixed it. This never touches the project's own root `.gitignore` — `.cairn/` ignores itself.
   - `.cairn/` doesn't exist: nothing to do here.

7. **Stale dashboard lockfile.** If `.cairn/usage-dashboard.pid` exists, check whether the PID in it is still alive.
   - Alive → report the dashboard is running, with its URL.
   - Dead → remove the stale lockfile, report that you cleaned it up (otherwise `/cairn-dashboard` would think one's already running when it isn't).

8. **Summary.** One short report covering all seven checks and what (if anything) was changed.
```

- [ ] **Step 2: Verify structurally**

Run: `grep -n "^[0-9]\." commands/cairn-doctor.md`
Expected: 8 numbered top-level steps, sequential 1-8, no gaps or duplicates.

Run: `grep -n "taste-skill@taste-skill\|frontend-design@claude-code-plugins\|emil-design-eng" commands/cairn-doctor.md`
Expected: at least 3 matches, all inside the new Steps 3-4.

- [ ] **Step 3: Commit**

```bash
git add commands/cairn-doctor.md
git commit -m "Add recommended-plugin checks for Taste Skill, Anthropic Frontend Design, Emil Kowalski skills to cairn-doctor"
```

---

## Task 5: Update `CLAUDE.md` architecture narrative

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: final behavior from Tasks 1-4 (must describe what actually landed, not what was planned).

- [ ] **Step 1: Update the `product-designer` paragraph**

Find the sentence (in the `**`product-designer`** (agents/)` paragraph):
```
UI Layout Specification hard-requires Impeccable (a vendored third-party design tool, never shipped by cairn — same "hard-required, never reimplemented" pattern as `idea-explorer`/`superpowers`) to be present in the consuming project; aborts that one doc type if absent, invokes it once for pre-fill input into its own discovery rather than a second interview.
```

Insert immediately after it (same paragraph):
```
UI Layout Specification and Design System also run a soft-optional Design Quality Pass (Taste Skill, a vendored third-party plugin) — unlike Impeccable, a missing Taste Skill install never aborts the run, the pass just skips.
```

- [ ] **Step 2: Update the `software-engineer` paragraph**

Find the sentence:
```
Stack-agnostic — no per-stack guide skill: infers conventions from the repo itself plus `.harness/architecture.md`/`standards.md` when present.
```

Insert immediately after it (same paragraph):
```
UI-facing tasks in either mode run a soft-optional Frontend Polish Pass (Anthropic Frontend Design, Taste Skill, and vendored Emil Kowalski skills, whichever are present) before implementation begins — same skip-silently-if-absent treatment as `product-designer`'s Design Quality Pass, gated to tasks the plan/request/touched-files actually identify as UI work.
```

- [ ] **Step 3: Update the `/cairn-doctor` paragraph**

Find the sentence:
```
**`/cairn-doctor`** — on-demand health check: plugin version (via `claude plugin update`), whether `superpowers` (an `idea-explorer` hard requirement) is installed and enabled, `CLAUDE.md` wiring status, `.cairn/.gitignore` presence/content, and stale dashboard lockfile cleanup.
```

Replace with:
```
**`/cairn-doctor`** — on-demand health check: plugin version (via `claude plugin update`), whether `superpowers` (an `idea-explorer` hard requirement) is installed and enabled, whether Taste Skill and Anthropic Frontend Design (soft-optional inputs to `product-designer`'s Design Quality Pass and `software-engineer`'s Frontend Polish Pass) are installed, whether Emil Kowalski skills are vendored in the current project, `CLAUDE.md` wiring status, `.cairn/.gitignore` presence/content, and stale dashboard lockfile cleanup.
```

- [ ] **Step 4: Verify structurally**

Run: `grep -c "Design Quality Pass\|Frontend Polish Pass" CLAUDE.md`
Expected: at least 3 (one in product-designer paragraph, one in software-engineer paragraph, and the doctor paragraph references both by implication via "soft-optional inputs").

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "Document Design Quality Pass, Frontend Polish Pass, and doctor checks in CLAUDE.md"
```

---

## Task 6: Version bump

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Bump the version (minor — new feature, per `CLAUDE.md`'s Versioning section)**

Old text:
```json
  "version": "0.12.0",
```

New text:
```json
  "version": "0.13.0",
```

- [ ] **Step 2: Verify**

Run: `claude plugin validate . --strict`
Expected: passes (same check CI runs on every push).

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "Bump to 0.13.0 for the design-skill integration"
```

---

## Task 7: End-to-end verification

**Files:**
- None modified — this task only runs commands and inspects output, per `CLAUDE.md`'s "Testing a command end-to-end" convention (no unit test framework covers agent-prompt behavior in this repo).

- [ ] **Step 1: Set up a clean scratch project with none of the three skills present**

```bash
mkdir -p /tmp/cairn-design-skill-probe && cd /tmp/cairn-design-skill-probe && git init -q
```

- [ ] **Step 2: Run `/cairn-doctor` headless and confirm the two new checks report "not installed" without erroring**

```bash
claude -p "/cairn:cairn-doctor" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```

Expected: output mentions Taste Skill and Anthropic Frontend Design as not installed, Emil Kowalski skills as not vendored, suggests the three install commands as text, and the command completes without error (no `ABORT`, no crash).

- [ ] **Step 3: Confirm the absent-skill path in `software-engineer` doesn't error on a UI-facing Direct-mode request**

```bash
mkdir -p src && printf 'export function Button() { return null }\n' > src/Button.tsx
claude -p "Fix the Button component in src/Button.tsx to accept a label prop" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```

Expected: the run completes (Direct mode, UI-facing — Frontend Polish Pass triggers, all three checks fail/absent, skip silently), no `ABORT`, no tool error surfaced about `Skill` or `Glob` calls failing ungracefully.

- [ ] **Step 4: Confirm the present-detection path for the `Glob`-based check (Emil Kowalski) actually fires**

```bash
mkdir -p .claude/skills/emil-design-eng && printf -- '---\nname: emil-design-eng\ndescription: stub for verification\n---\nstub\n' > .claude/skills/emil-design-eng/SKILL.md
claude -p "/cairn:cairn-doctor" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```

Expected: this run's output now reports Emil Kowalski skills as vendored/present, distinct from Step 2's "not vendored" report — confirming the `Glob` check actually distinguishes presence from absence rather than always reporting one state.

- [ ] **Step 5: Clean up the scratch project**

```bash
rm -rf /tmp/cairn-design-skill-probe
```

- [ ] **Step 6: Report the verification results** (no commit — this task produces no repo changes)
