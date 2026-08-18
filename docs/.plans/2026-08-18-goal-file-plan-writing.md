# Goal-File-in-Plan-Writing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional final step to `cairn:plan-writing` that drafts and persists a `/goal` completion condition for the just-written plan, pre-filled from the plan's own acceptance-criteria/testing sections, printing the manual `/goal <condition>` command back to the user.

**Architecture:** A second override layered onto `skills/plan-writing/SKILL.md` (alongside the existing save-path override), documented in prose as cairn-original behavior added on top of the unmodified `superpowers:writing-plans` methodology — no new agent file, no standalone ad-hoc-goal path.

**Tech Stack:** Markdown skill-definition file (no code execution).

**Spec:** `docs/.specs/2026-08-18-goal-file-plan-writing-design.md`

## Global Constraints

- No standalone agent file — the goal-file step lives entirely inside `skills/plan-writing/SKILL.md`.
- No ad-hoc (plan-less) goal path — explicitly out of scope per the spec's Scope decision.
- One goal condition per plan, never per-phase.
- The condition must be phrased as something Claude's own output can demonstrate — never something requiring the evaluator to independently run commands or read files.
- ≤4,000 characters.
- `/goal` is never auto-invoked — always a persisted file plus a printed manual command.
- `superpowers:writing-plans` itself is never modified (vendored, unmodified per the existing wrapper pattern) — the new step is documented as cairn-original behavior added after that skill's own flow completes.

---

### Task 1: Add the goal-file override to `skills/plan-writing/SKILL.md`

**Files:**
- Modify: `skills/plan-writing/SKILL.md`

**Interfaces:**
- Consumes: spec sections "Flow", "Carried-over constraints"; the existing "## The one override" section's prose style as the template for how to document a second override without touching the vendored skill's own instructions.
- Produces: the goal-file step cairn's `plan-writing` invocation now runs — nothing else in the codebase calls into this directly, it's purely a documented step in the skill's own instructions.

- [ ] **Step 1: Add a second `##` section after "The one override"**

Insert a new section, `## The second override: optional goal-file authoring`, directly after the existing `## The one override` section and before `## Why this exists`. Content (from spec "Flow", condensed to instructional prose matching this file's existing terse style):

```markdown
## The second override: optional goal-file authoring

After `superpowers:writing-plans` completes its own flow (plan written, reviewed, ready to hand off to `executing-plans`), run one more step before that hand-off: offer to draft a `/goal` completion condition for the plan just written.

`/goal` is a built-in Claude Code slash command, not a marketplace skill — it is not invocable via the `Skill` tool. This step never invokes it; it drafts and persists the condition, then prints the exact manual command for the user to run themselves.

1. **Offer.** One `AskUserQuestion`: "Draft a `/goal` completion condition for this plan too, so you can run it unattended?" On decline, proceed straight to the existing `executing-plans` hand-off — nothing else in this section applies.
2. **Pre-fill.** Read the plan's own acceptance-criteria/testing sections (the review checkpoints `writing-plans` itself just produced). Compose a candidate end-state and stated-check from them — do not re-ask what the plan already establishes.
3. **Ask what's missing**, one question at a time via `AskUserQuestion`:
   - "Anything that must NOT change or happen on the way there? Say 'none' if there aren't any." (constraints)
   - "Cap this by a turn or time limit in case it can't converge? Say 'none' to let it run until the condition is met or you cancel it." (bound)
4. **Compose** the final condition text: end-state + stated-check + constraints (if any) + bound clause (if any). Validate it's ≤4,000 characters; if over, cut non-essential detail with the user before continuing.
5. **Show verbatim** in a fenced block and get explicit approval or edits — nothing is written until the user has seen and approved the literal wording. The condition must be phrased as something Claude's own output can demonstrate (a test result, a build exit code, a file count) — never something requiring the evaluator to independently run commands or read files, since it cannot.
6. **Write** `docs/.plans/YYYY-MM-DD-<feature-name>-goal.md` (same date and feature-name as the plan file itself, sibling to it): the approved condition text, plus the end-state / stated-check / constraints / bound captured above, and the date drafted.
7. **Print** the exact manual command:
   ```
   /goal [the exact approved condition text]
   ```
   Plus a one-line note: `/goal` alone shows status, `/goal clear` cancels — once actually invoked. Also remind once, briefly: `/goal` doesn't change tool permissions — Claude still asks before tool calls your settings don't already allow; pair with auto mode for a fully unattended run.
8. Proceed to the existing hand-off to `executing-plans`, unchanged.
```

- [ ] **Step 2: Update the frontmatter `description`**

The current `description` says the skill "only redirects the implementation-plan save path" — that's no longer accurate with a second override added. Update it to:

```yaml
description: cairn's path-override wrapper for superpowers:writing-plans. Invoke instead of superpowers:writing-plans directly whenever intent-analyzer's Brainstorming Gate has fired, or when cairn:spec-writing hands off to it — runs the real methodology unchanged, redirecting the implementation-plan save path to docs/.plans/ instead of the vendor default docs/superpowers/plans/, and adding an optional final step that drafts a /goal completion condition for the plan.
```

- [ ] **Step 3: Update "Why this exists" if needed**

Read the current "## Why this exists" section — if its wording implies only the save-path change ("changes exactly one thing"), update the opening line of "## The one override" and the "Thin wrapper..." sentence at the top of the file to say "changes exactly one thing about where the plan is saved, and adds one optional step" instead of implying the whole file is single-purpose. Keep the rest of "Why this exists" as-is — the dot-prefixed-convention rationale still applies to the save-path override; the goal-file addition doesn't need its own "why" restated there since it's covered by the new section's own inline reasoning.

- [ ] **Step 4: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 5: Headless smoke test**

```bash
mkdir -p /tmp/cairn-goal-file-test && cd /tmp/cairn-goal-file-test && git init -q
git commit --allow-empty -q -m "chore: initial commit"
mkdir -p docs/.specs
cat > docs/.specs/2026-08-18-sample-feature-design.md <<'EOF'
# Design: sample feature
A trivial spec for smoke-testing the goal-file step.
EOF
claude -p "/cairn:plan-writing docs/.specs/2026-08-18-sample-feature-design.md — a tiny one-task plan for a sample feature" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: a plan gets written to `docs/.plans/2026-08-18-sample-feature.md` (or similar slug), and the reported output includes the goal-file offer question before the `executing-plans` hand-off. Since this is a non-interactive headless run, the offer will surface as a stop point — inspect the reported output to confirm the offer text and pre-fill logic ran (referencing the plan's own acceptance criteria), rather than expecting the full interactive flow to complete unattended.

- [ ] **Step 6: Commit**

```bash
git add skills/plan-writing/SKILL.md
git commit -m "Add optional goal-file authoring to cairn:plan-writing

Second override on top of the existing save-path redirect: after a
plan is written and reviewed, offers to draft a /goal completion
condition pre-filled from the plan's own acceptance criteria, writes
it beside the plan file, and prints the manual /goal command.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `CLAUDE.md` updates

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: Task 1's finished `skills/plan-writing/SKILL.md`; the existing `spec-writing`/`plan-writing` paragraph at line 33.

- [ ] **Step 1: Update the `spec-writing` and `plan-writing` paragraph**

The existing paragraph (line 33) says each wrapper "redirecting only the one save-path step." Update the `plan-writing`-specific portion of this paragraph to mention the second override. Insert this sentence immediately after the existing "Neither wrapper reimplements the underlying methodology... same 'hard-required, never reimplemented' pattern as `idea-explorer`." sentence:

```markdown
`plan-writing` also runs one additional cairn-original step of its own after `superpowers:writing-plans` completes its flow: an optional offer to draft a `/goal` completion condition for the plan just written, pre-filled from the plan's own acceptance-criteria sections, written to `docs/.plans/YYYY-MM-DD-<feature-name>-goal.md` beside the plan — `/goal` is a built-in Claude Code slash command, not a marketplace skill, so this is a persisted-file-plus-manual-command hand-back, never an auto-invocation. See `docs/.specs/2026-08-18-goal-file-plan-writing-design.md`.
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document plan-writing's goal-file authoring step in CLAUDE.md

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Version bump + final validation

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Bump version**

New behavior a consuming project would see reflected (plan-writing now offers a goal file) — minor bump per this repo's own Versioning rule. Read current `version`, bump the minor component, reset patch to 0.

- [ ] **Step 2: Final validation**

Run: `claude plugin validate . --strict`
Expected: passes clean.

Run: `pytest tests/ -v -s`
Expected: `tests/test_usage_dashboard.py`'s deterministic subset stays green. `tests/test_intent_routing.py`'s eval suite stays at or above `MIN_PASS` — this work makes zero changes to `agents/intent-analyzer.md`.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version for goal-file-in-plan-writing feature

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
