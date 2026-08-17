# Sanitized Feedback-to-Issue Mechanism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a consuming project report cairn bugs back to `jisundr/cairn`'s issue board, via a sanitized local draft the user always reviews before anything is pushed — never automatic.

**Architecture:** A shared skill (`skills/feedback-context/SKILL.md`) documents the trigger definition, the drafting discipline, and the fixed draft field list — the single source of truth both entry points follow. `commands/cairn-feedback.md` is the explicit entry point (invokes the skill for its discipline rather than duplicating it). All 16 `agents/*.md` files and `commands/cairn-doctor.md` get one soft-optional addition each, mirroring the already-shipped `graphify-context` integration's shape exactly.

**Tech Stack:** Markdown command/skill/agent-definition files (no code execution) — same category as every other `commands/*.md`/`skills/*/SKILL.md` file in this plugin.

**Spec:** `docs/.specs/2026-08-17-feedback-mechanism-design.md`

## Global Constraints

- Never automated: the local draft always stops for human review before push is even discussed; the `gh issue create` offer is re-confirmed every single time, never a standing permission.
- Draft field list is fixed and exhaustive: cairn version, agent/command/skill involved (if known), what happened, a generic repro description. Never file contents, absolute paths, env var values, or repo-specific identifiers.
- `.cairn/feedback/` is gated on `/cairn-setup` having run, same check `/cairn-dashboard` already uses (`<!-- cairn:start -->` marker in the project's root `CLAUDE.md`).
- Trigger definition for agent-initiated suggestions: fires only on an error that doesn't match any row already in that agent's own `EXIT & DERAILMENT HANDLING` table — never for the consuming codebase's own bugs, never for a documented `TERMINATED`/`HANDOFF NEEDED`/declined-question state.
- File naming: `.cairn/feedback/YYYYMMDD-HHmmss-<slug>.md` (matches `codebase-auditor`'s existing `YYYYMMDD-HHmmss-{project-name}.md` convention).

---

## Task 1: `skills/feedback-context/SKILL.md` (new)

**Files:**
- Create: `skills/feedback-context/SKILL.md`

**Interfaces:**
- Produces: the shared drafting discipline, trigger definition, and draft field list — the single source both `commands/cairn-feedback.md` (Task 2) and all 16 agent files (Task 3) reference/follow. No other task's code depends on a function signature here (this is a skill file, prose only) — but Task 2 and Task 3's exact wording must match this file's documented convention, not invent their own.

- [ ] **Step 1: Write the skill file**

Create `skills/feedback-context/SKILL.md` with this exact content:

```markdown
---
name: feedback-context
description: Shared trigger definition, drafting discipline, and sanitized draft field list for reporting cairn bugs back to jisundr/cairn's issue board. Loaded by any agent when it hits something that looks like a cairn-side defect (not the consuming codebase's bug), and by commands/cairn-feedback.md as its drafting discipline. Never auto-drafts — every draft stops for human review before push is even discussed.
---

# Feedback Context — shared feedback-drafting discipline

Not a user-invoked skill despite living under `skills/` in the same sense as `commands/cairn-feedback.md` — this is the shared discipline both the explicit command and any agent's soft-optional suggestion follow, so the two entry points never drift into two different draft formats.

## Trigger definition (when an agent should suggest filing feedback)

**Fires:** an unhandled exception/crash in cairn's own tooling — a Python traceback from `scripts/usage_dashboard.py`, a malformed template render, a `Skill()` invocation failing in a way the calling agent's own `EXIT & DERAILMENT HANDLING` table doesn't already name as a documented state.

**Never fires:** the consuming codebase's own bugs (that's what the agent is there to work on), or any state the agent's `EXIT & DERAILMENT HANDLING` table already documents (a `TERMINATED`, a `HANDOFF NEEDED`, a declined `AskUserQuestion` — cairn working as designed, not a defect).

## The suggestion (agent-initiated path)

One line, plain text, alongside the agent's normal error report — never a hard gate, never auto-drafts unasked:

> "This looks like it might be a cairn bug, not something in this project — want to file feedback? I can draft a local sanitized file for you to review first."

On yes, follow the Draft/Review/Push flow below.

## Draft/Review/Push flow (shared by every entry point)

1. **Gate.** Check the project's root `CLAUDE.md` for the exact line `<!-- cairn:start -->` (whole line, not just the text appearing in prose). Absent → refuse, point at `/cairn-setup`. Same check `/cairn-dashboard` already uses.
2. **Gather.** If not already known from context: what happened, which agent/command/skill was involved, cairn version (from `.claude-plugin/plugin.json` or the latest entry in `.cairn/version-log.jsonl`).
3. **Draft.** Write `.cairn/feedback/YYYYMMDD-HHmmss-<slug>.md` (slug: short kebab-case, ad hoc from the issue description) containing ONLY the fixed field list below — nothing else, ever.
4. **Stop.** Show the full drafted content to the user. Ask them to review/redact before anything about pushing is discussed. This is a hard stop, not a formality — never proceed to step 5 without an explicit go-ahead on this exact draft.
5. **Offer push.** On explicit confirmation: if `gh auth status` succeeds, offer `gh issue create --repo jisundr/cairn --title <title> --body-file <path>` — ask before running it, every time, never standing permission. If `gh` is unavailable/unauthenticated, or the user declines running it, fall back to: point at `https://github.com/jisundr/cairn/issues/new` and the local file path for the user to copy-paste themselves.

## Draft field list (fixed, exhaustive)

- cairn version
- Which agent/command/skill was involved (if known)
- What happened (the error text or unexpected behavior, as reported)
- A generic repro description, in terms of cairn's own flow (e.g. "ran `/cairn-dashboard`", "task-orchestrator Plan Mode step 7") — never the consuming project's actual file paths, code, or business logic

Nothing outside this list. No file contents, no absolute paths, no env var values, no repo-specific identifiers (names, URLs, internal terminology from the consuming project).

## Error handling

If this skill fails to load for some reason, the calling agent/command falls through to its normal error report exactly as if the skill didn't exist — same soft-optional discipline as every other "attempt X, skip silently" pattern in cairn (e.g. `graphify-context`). Never blocks or aborts the calling agent's own run.
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

- [ ] **Step 3: Commit**

```bash
git add skills/feedback-context/SKILL.md
git commit -m "feat: add feedback-context shared skill"
```

---

## Task 2: `commands/cairn-feedback.md` (new)

**Files:**
- Create: `commands/cairn-feedback.md`

**Interfaces:**
- Consumes: `Skill(skill: "feedback-context")` (Task 1) for the drafting discipline, field list, and gate/draft/push flow — this command does NOT duplicate that content, it invokes the skill and follows it.

- [ ] **Step 1: Write the command file**

Create `commands/cairn-feedback.md`. Model its frontmatter/structure on `commands/cairn-doctor.md`'s existing shape (a `description:` frontmatter field, a `## Your task` body):

```markdown
---
description: "File sanitized feedback about a cairn bug to jisundr/cairn's issue board. Drafts a local file first — always reviewed by you before anything is pushed, never automatic."
---

## Your task

1. Invoke `Skill(skill: "feedback-context")` — it documents the gate check, the gather/draft/review/push flow, and the fixed draft field list. Follow it exactly; this command does not have its own separate drafting rules.
2. If the user's invocation already described the issue (e.g. `/cairn:cairn-feedback the dashboard crashed on start`), treat that as the "what happened" input for the skill's Gather step. Otherwise ask what happened first.
3. Follow the skill's Draft/Review/Push flow (Gate → Gather → Draft → Stop → Offer push) exactly as documented. Do not skip the Stop step under any circumstance, even if the user seems eager to push immediately — the review gate is not optional.
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

- [ ] **Step 3: Commit**

```bash
git add commands/cairn-feedback.md
git commit -m "feat: add /cairn-feedback command"
```

---

## Task 3: Wire `feedback-context` into all 16 `agents/*.md` files

**Files:**
- Modify: `agents/codebase-auditor.md`
- Modify: `agents/competitor-analyst.md`
- Modify: `agents/documentation-auditor.md`
- Modify: `agents/documentation-engineer.md`
- Modify: `agents/harness-engineer.md`
- Modify: `agents/idea-explorer.md`
- Modify: `agents/intent-analyzer.md`
- Modify: `agents/market-researcher.md`
- Modify: `agents/product-designer.md`
- Modify: `agents/project-manager.md`
- Modify: `agents/qa-auditor.md`
- Modify: `agents/qa-engineer.md`
- Modify: `agents/requirements-engineer.md`
- Modify: `agents/software-engineer.md`
- Modify: `agents/solution-architect.md`
- Modify: `agents/task-orchestrator.md`

**Interfaces:**
- Consumes: `Skill(skill: "feedback-context")` (Task 1).

This is one batched task — all 16 edits are the identical shape (same row, same insertion rule), a single dispatch reviewing all 16 as one unit rather than 16 separate task cycles.

- [ ] **Step 1: Add `Skill` to the 3 agents missing it from `tools:` frontmatter**

Three of the 16 files do not currently have `Skill` in their frontmatter `tools:` list (verified by grep before writing this plan): `agents/documentation-engineer.md`, `agents/intent-analyzer.md`, `agents/project-manager.md`. In each of these three files' YAML frontmatter, append `, Skill` to the end of the existing `tools:` line (preserving whatever's already there). Example: `tools: Read, AskUserQuestion` becomes `tools: Read, AskUserQuestion, Skill`. The other 13 files already have `Skill` in their `tools:` list — do not modify their frontmatter.

- [ ] **Step 2: Add the EXIT & DERAILMENT row to all 16 files**

In each of the 16 files, find the `## EXIT & DERAILMENT HANDLING` heading (every file already has one — verified before writing this plan) and the markdown table immediately following it. Add this exact row as the LAST row of that table (after its current last row, before the next heading or end of section):

```markdown
| An error that doesn't match any other row in this table (looks like a cairn-side defect, not this codebase's) | Attempt `Skill(skill: "feedback-context")`; if it succeeds, surface its one-line suggestion alongside the normal error report. Never blocks — falls through to the normal error report either way. |
```

Do not reorder or modify any existing row. Do not add this row anywhere except as the new last row of the existing table.

- [ ] **Step 3: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

- [ ] **Step 4: Commit**

```bash
git add agents/codebase-auditor.md agents/competitor-analyst.md agents/documentation-auditor.md agents/documentation-engineer.md agents/harness-engineer.md agents/idea-explorer.md agents/intent-analyzer.md agents/market-researcher.md agents/product-designer.md agents/project-manager.md agents/qa-auditor.md agents/qa-engineer.md agents/requirements-engineer.md agents/software-engineer.md agents/solution-architect.md agents/task-orchestrator.md
git commit -m "feat: wire feedback-context into all 16 agents' EXIT & DERAILMENT handling"
```

---

## Task 4: `commands/cairn-doctor.md` — new step

**Files:**
- Modify: `commands/cairn-doctor.md`

**Interfaces:**
- Consumes: `Skill(skill: "feedback-context")` (Task 1).

- [ ] **Step 1: Read the current file**

`Read commands/cairn-doctor.md` in full first — this task's exact anchor depends on its current numbered-step structure (currently 8 steps: 7 checks + 1 summary).

- [ ] **Step 2: Insert a new step before the Summary step, renumber**

Insert a new step 8 (pushing the current step 8 "Summary" to step 9), between the existing step 7 (`Stale dashboard lockfile`) and the Summary step:

```markdown
8. **Unexpected check failure.** If any of Steps 1–7 hit something that doesn't fit its own documented pass/fail/missing states above (an actual crash mid-check, not one of the states already listed) — attempt `Skill(skill: "feedback-context")` and surface its suggestion. Never blocks the rest of the checks; include in the final summary.
```

Update the old step 8 heading to `9. **Summary.**` and its body text from "covering all seven checks" to "covering all eight checks" (now includes the new step).

- [ ] **Step 3: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

- [ ] **Step 4: Commit**

```bash
git add commands/cairn-doctor.md
git commit -m "feat: add unexpected-check-failure feedback suggestion to /cairn-doctor"
```

---

## Task 5: Version bump

**Files:**
- Modify: `.claude-plugin/plugin.json`

**Interfaces:**
- None — closes out the feature.

- [ ] **Step 1: Bump the plugin version**

Bump `"version"` in `.claude-plugin/plugin.json` from its current value to the next minor version (new feature, per `CLAUDE.md`'s Versioning section — read the file first to get the exact current value, don't assume it from this plan).

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

Run: `pytest tests/test_usage_dashboard.py -v`
Expected: all PASS (this task doesn't touch that file, but confirming no regression)

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version for feedback mechanism feature"
```

---

## Manual verification (not unit-testable — command/skill/agent-definition files)

Per `CLAUDE.md`'s Testing section, run headless against a scratch directory:

```bash
cd /some/scratch/dir
git init   # if not already a repo, and if /cairn-setup hasn't run there yet
claude -p "/cairn:cairn-feedback the dashboard crashed on start" --plugin-dir /path/to/cairn --permission-mode bypassPermissions --output-format text
```

Confirm: without `/cairn-setup` having run, the command refuses and points at `/cairn-setup`. After running `/cairn-setup`, the command gathers context, drafts `.cairn/feedback/YYYYMMDD-HHmmss-<slug>.md` containing only the fixed field list, stops and shows it for review, and only after explicit confirmation offers the `gh issue create` command (or the copy-paste fallback if `gh` isn't authenticated). Spot-check 2–3 of the 16 agents' new `EXIT & DERAILMENT` rows by simulating an unmatched error and confirming the suggestion fires — the row's text is identical across all 16 files, so this is a wiring/formatting check, not a per-agent design check.
