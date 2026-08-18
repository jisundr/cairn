# Chain-vs-Direct Heuristic + Backoff Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a regression-risk-based Chain-vs-Direct routing heuristic to `CLAUDE.md`'s Chain-flow-entry documentation, and a backoff-paced `/loop` mode to `/cairn-run-task`'s Monitor/Stale-detection sections, so Unattended runs get checked on a decaying cadence instead of only when a human remembers to look.

**Architecture:** Two documentation-only changes, no new agent/command/skill files. `CLAUDE.md`'s existing Coding-chain sequence paragraph gains one new judgment-call step (the heuristic) inserted before its Direct/Chain flow bullets. `commands/cairn-run-task.md`'s existing Monitor and Stale detection paragraphs gain a new no-target `/loop` mode that supersedes Stale detection's previously-unspecified "repeated checks" source.

**Tech Stack:** Markdown prose edits only (no code execution).

**Spec:** `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md`

## Global Constraints

- No new agent, command, or skill files — both changes are prose extensions to existing files.
- The heuristic is a judgment call presented via `AskUserQuestion`, never silent (Global Constraint from the spec's Scope decision table).
- The backoff loop never writes to a task's `STATE.md`/`HISTORY.md` except the one thing Stale detection already specifies (`STALLED`) — per-task backoff timers are transient to the running `/loop` invocation, never persisted.
- Backoff: 1 min start, doubles per unchanged tick, caps at 30 min, full reset to 1 min on any change. `STALLED` after 3 consecutive unchanged ticks once at the 30-min cap.
- Notify the user only on state change (phase advance, `HANDOFF NEEDED` newly reached, `STALLED` newly declared, `PUBLISH`/terminal reached) — silent on an unchanged tick.

---

### Task 1: Chain-vs-Direct routing heuristic in `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: spec "Part 1 — Chain-vs-Direct routing heuristic"; the existing Coding-chain sequence paragraph at `CLAUDE.md` line 69 and its Direct/Chain flow bullets at lines 71-72 as the exact insertion point.
- Produces: no new interface — this is a documented judgment call the invoking main-thread session follows, not a function/agent other tasks call into.

- [ ] **Step 1: Insert the heuristic as a new paragraph between the Coding-chain sequence intro and its Direct/Chain flow bullets**

In `CLAUDE.md`, insert this new paragraph directly after the sentence ending "...rather than inside `intent-analyzer`." (end of the paragraph at line 69) and before the `- **Direct flow**` bullet (line 71):

```markdown
Before dispatching either flow, the invoking session runs one more judgment call — recommend Chain or Direct-with-worktree — right after `spec-writing` → `plan-writing`'s architectural path has produced `docs/.plans/<slug>.md`, before dispatching anything else. Read the plan's `### Task N:` blocks and their **Files** sections: if any task's `Modify: <path>` entry changes an *existing* file's current behavior (not just an appended paragraph/bullet — an edit to existing agent process steps, an existing skill's methodology, or similar), the plan carries regression risk → recommend **Chain**. If every task is `Create:` (new files) or purely additive `Modify:` (append-only, no behavior change), recommend **Direct-with-worktree**. This is a judgment call made reading the plan, not a mechanical count of `Modify:` lines — the same kind of distinction `qa-auditor` already draws between an added/modified line and a pre-existing one. Present the recommendation via one `AskUserQuestion` — which task/file drove the call, or confirmation that nothing modifies existing behavior — never silently pick either flow. On Direct-with-worktree, the existing "run Lightweight Start first?" ask below now defaults to *yes* in the recommendation's framing, since choosing this branch specifically to keep worktree isolation is the point. See `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md` for the full design.
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 3: Headless smoke test**

```bash
mkdir -p /tmp/cairn-heuristic-test && cd /tmp/cairn-heuristic-test && git init -q
git commit --allow-empty -q -m "chore: initial commit"
mkdir -p docs/.plans
cat > docs/.plans/2026-08-18-tiny-feature.md <<'EOF'
# Tiny Feature Implementation Plan

**Goal:** Add a single new helper script.
**Spec:** none

## Global Constraints
- none

---

### Task 1: New helper script

**Files:**
- Create: `scripts/helper.py`

- [ ] **Step 1: Write it**
EOF
claude -p "/cairn:cairn-run-task docs/.plans/2026-08-18-tiny-feature.md" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: the reported output references reading the plan's Task 1 Files section, observes it's `Create:`-only (no `Modify:` of any existing file — the scratch repo has no pre-existing files to modify), and recommends Direct-with-worktree with reasoning naming that. Since this is a non-interactive headless run, the `AskUserQuestion` will surface as a stop point — inspect the reported text for the recommendation and reasoning rather than expecting it to complete dispatch unattended.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Chain-vs-Direct regression-risk routing heuristic

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Backoff monitoring loop in `commands/cairn-run-task.md`

**Files:**
- Modify: `commands/cairn-run-task.md`

**Interfaces:**
- Consumes: spec "Part 2 — Backoff monitoring loop"; the existing `**Monitor.**` paragraph (line 46) and `**Stale detection.**` paragraph (line 48) as the exact insertion points.
- Produces: a new no-target invocation mode for `/cairn-run-task`, intended to be run under the built-in `/loop` skill (e.g. `/loop /cairn-run-task`).

- [ ] **Step 1: Insert the backoff loop mode after the existing Monitor paragraph**

In `commands/cairn-run-task.md`, insert this new subsection directly after the `**Monitor.**` paragraph (line 46) and before the `**Stale detection.**` paragraph (line 48):

```markdown
**Backoff loop mode.** `/cairn-run-task` invoked with no target (e.g. under the built-in `/loop` skill, `/loop /cairn-run-task`) checks every active Unattended task in one pass instead of a single named target:

1. `Glob docs/.tasks/*/STATE.md`, filter to `Mode: Unattended` and `Phase` not already `PUBLISH` or a `HANDOFF NEEDED` this loop has already reported once.
2. Per task, per tick: read `Phase` + count `HISTORY.md` lines, compare against the last-seen fingerprint kept in this loop's own running state (not written to any task file — read-only, same as Monitor above).
3. Unchanged → double that task's own backoff interval (start 1 min, cap 30 min); no message. Changed → reset that task's interval to 1 min, message the user with the new `Phase`/latest `HISTORY.md` line (plus the pending question from `Key info` and a bounded `tmux capture-pane` if the new `Phase` is `HANDOFF NEEDED`, same as Monitor's existing rule).
4. Once a task's own backoff has been at the 30-min cap for 3 consecutive unchanged ticks, declare `STALLED` per Stale detection below and drop it from the discovery set.
5. A task reaching `PUBLISH` gets one final message (PR/MR URL) and is dropped from the discovery set.
6. Return control to `/loop` after each pass — this command never owns the timer itself, same pattern `pr-reviewer`'s Thread Watch mode uses for the built-in `/loop` skill.

Silent on an unchanged tick across the board — the whole point of backing off. See `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md` for the full design.
```

- [ ] **Step 2: Extend the Stale detection paragraph to name the backoff loop as its check source**

In `commands/cairn-run-task.md`, the `**Stale detection.**` paragraph currently ends: "`STALLED` is distinct from a clean finish and from a clean pause." Append one sentence:

```markdown
 The backoff loop mode above is what now supplies the "repeated checks" this relies on — 3 consecutive unchanged ticks once a task's own backoff interval has reached its 30-min cap (≈90 min of confirmed no-progress at the slowest cadence) is the trigger, rather than a human happening to re-invoke this command against the same target repeatedly.
```

- [ ] **Step 3: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 4: Headless smoke test**

```bash
mkdir -p /tmp/cairn-backoff-test && cd /tmp/cairn-backoff-test && git init -q
git commit --allow-empty -q -m "chore: initial commit"
mkdir -p docs/.tasks/2026-08-18-fake-task
cat > docs/.tasks/2026-08-18-fake-task/STATE.md <<'EOF'
# Task: fake-task

Mode: Unattended
Phase: QA-RED
Handoff to: software-engineer
Status: test fixture
Plan: docs/.plans/2026-08-18-fake-task.md
Ticket: none
Worktree: /tmp/cairn-backoff-test/.worktrees/feature-fake-task
Branch: feature/fake-task
Key info: none
Harness flags: none
EOF
cat > docs/.tasks/2026-08-18-fake-task/HISTORY.md <<'EOF'
# History: fake-task

- 2026-08-18T00:00:00Z PLAN: fixture line.
EOF
claude -p "/cairn:cairn-run-task" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: the reported output describes discovering `docs/.tasks/2026-08-18-fake-task/` (Unattended, `Phase: QA-RED`, not terminal), reading its fingerprint (`Phase` + 2 `HISTORY.md` lines), and since this is the first tick (no prior fingerprint in this fresh invocation), either reports it as newly-seen or silently establishes baseline per the loop's own Step 2 — inspect the reported text for this reasoning rather than expecting multi-tick backoff behavior from a single headless call (that requires actual repeated `/loop` ticks, which this smoke test can't drive non-interactively).

- [ ] **Step 5: Commit**

```bash
git add commands/cairn-run-task.md
git commit -m "docs: add backoff-paced /loop mode to cairn-run-task's Monitor/Stale detection

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Version bump + final validation

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Bump version**

Behavior change a consuming project would see reflected (new routing heuristic, new `/cairn-run-task` mode) — minor bump per this repo's own Versioning rule. Check `git show main:.claude-plugin/plugin.json` for the current version on `main` (not just this worktree's own copy, given concurrent sibling chain runs may have already bumped it), bump the minor component from whichever value is actually current, reset patch to 0.

- [ ] **Step 2: Final validation**

Run: `claude plugin validate . --strict`
Expected: passes clean.

Run: `pytest tests/ -v -s`
Expected: `tests/test_usage_dashboard.py`'s deterministic subset stays green. `tests/test_intent_routing.py`'s eval suite stays at or above `MIN_PASS` — this work makes zero changes to `agents/intent-analyzer.md`.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version for chain-direct-heuristic and backoff-monitoring feature

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
