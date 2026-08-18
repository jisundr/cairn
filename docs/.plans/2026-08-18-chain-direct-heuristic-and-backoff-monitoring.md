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
Once `plan-writing`'s architectural path has produced `docs/.plans/<slug>.md` — the `brainstorm-first` path only; `proceed-directly` never invokes `plan-writing` and has no plan file to read, so it goes straight to Direct flow below without this step — the invoking session runs one more judgment call before dispatching either `task-orchestrator` Plan Mode or Direct flow: recommend Chain flow, or Direct flow run under `task-orchestrator` Lightweight Start. Read the plan's `### Task N:` blocks and their **Files** sections: if any task's `Modify: <path>` entry changes an *existing* file's current behavior (not just an appended paragraph/bullet — an edit to existing agent process steps, an existing skill's methodology, or similar), the plan carries regression risk → recommend **Chain flow**. If every task is `Create:` (new files) or purely additive `Modify:` (append-only, no behavior change), recommend **Direct flow with `task-orchestrator` Lightweight Start**. This is a judgment call made reading the plan, not a mechanical count of `Modify:` lines — the same kind of distinction `qa-auditor` already draws between an added/modified line and a pre-existing one. Present the recommendation via one `AskUserQuestion` — which task/file drove the call, or confirmation that nothing modifies existing behavior — never silently pick either flow. On a Direct-flow recommendation, the "run Lightweight Start first?" ask below stays exactly what it already is (suggested, never forced) — only its framing changes, since this recommendation is specifically about keeping worktree isolation on a small plan, not a signal to skip the ask. See `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md` for the full design.
```

- [ ] **Step 1.5: Amend the two flow bullets the heuristic can redirect between**

The `- **Direct flow**` bullet currently opens "(`User Choice: proceed-directly`, task type `bug-fix`/`decision`)" and the `- **Chain flow**` bullet opens "(`User Choice: brainstorm-first`, once `spec-writing` → `plan-writing`'s architectural path has produced `docs/.plans/<slug>.md` ...)" — an unconditional mapping the new paragraph above them now makes conditional. Update both opening clauses so the routing table and the heuristic paragraph agree:

In the `- **Chain flow**` bullet, change the opening to:

```markdown
- **Chain flow** (`User Choice: brainstorm-first`, once `spec-writing` → `plan-writing`'s architectural path has produced `docs/.plans/<slug>.md` and the regression-risk heuristic above recommends Chain — the bounded path implements inline during brainstorming and never reaches the chain):
```

In the `- **Direct flow**` bullet, change the opening to:

```markdown
- **Direct flow** (`User Choice: proceed-directly`, task type `bug-fix`/`decision` — or `brainstorm-first` where the regression-risk heuristic above recommends Direct instead of Chain):
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 3: Read-back self-review against the two bullets it sits above**

This is a `CLAUDE.md` prose change, not a command file — there is no `/cairn:<command>` to invoke headlessly against it (`--plugin-dir` loads `agents/`/`commands/`/`skills/`/`hooks/`, never a target repo's own `CLAUDE.md`; a scratch dir has no `CLAUDE.md` of its own to carry the new paragraph even if it did). Verify instead by reading the inserted paragraph back against its two immediate neighbors:

1. Read `CLAUDE.md`'s new paragraph plus the `- **Direct flow**` and `- **Chain flow**` bullets immediately below it, in order, as a reader encountering them for the first time would.
2. Confirm the new paragraph's opening clause names the `brainstorm-first` path specifically (not "either flow") and explicitly says `proceed-directly` skips this step — re-check this against the `- **Direct flow**` bullet's own opening clause (`User Choice: proceed-directly`) to confirm they don't contradict, and confirm both bullets' Step 1.5 amendments actually acknowledge the heuristic can redirect a `brainstorm-first` plan either way (not just describe the heuristic paragraph in isolation).
3. Confirm every flow name used in the new paragraph (`Chain flow`, `Direct flow`, `task-orchestrator Lightweight Start`) matches a name already defined elsewhere in `CLAUDE.md` — grep for each one and confirm at least one prior use exists. No new undefined term should appear.
4. Confirm the "Lightweight Start ask" sentence matches what the `- **Direct flow**` bullet already says about that ask (`AskUserQuestion`, suggested never forced) rather than describing new behavior for it.

Expected: all four checks pass by inspection. If any fails, fix the inserted paragraph directly and re-check — this is not a scripted pass/fail, it's the same kind of read-back `documentation-auditor` already performs, done here by the implementer before commit rather than caught later.

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
- Modify: `README.md` (`/cairn-run-task` bullet)
- Modify: `CLAUDE.md` ("Two entry points reach Chain flow" paragraph)

**Interfaces:**
- Consumes: spec "Part 2 — Backoff monitoring loop"; the existing `## Input resolution`, `## Attended vs. unattended`, `**Monitor.**` paragraph (line 46), and `**Stale detection.**` paragraph (line 48) sections as the exact insertion/rewrite points.
- Produces: a new no-target invocation mode for `/cairn-run-task`, intended to be run under the built-in `/loop` skill (e.g. `/loop /cairn-run-task`). Writes a durable `STALLED (<timestamp>)` marker prefixed onto a stalled task's `STATE.md` `Status` field (not `Harness flags` — that field is read by `task-orchestrator` Publish Mode for its harness/doc-drift question, and a monitoring marker there would be misread as one) — Task 1's heuristic and other tasks never read this marker, it's consumed only by this task's own discovery filter.

- [ ] **Step 1: Add a no-target branch to Input resolution, and update the frontmatter/intro to stop implying a required target**

`commands/cairn-run-task.md`'s `## Input resolution` section currently lists three accepted `$ARGUMENTS` forms (bare slug, pasted path, ticket URL/ID), none of which is empty — and the frontmatter plus the file's own intro sentence both describe a required target. Change the frontmatter block:

```yaml
description: Create or resume a coding-chain task and run it (Chain flow only), or with no target, run a backoff-paced monitoring check of every active Unattended task.
argument-hint: [slug-or-path-or-ticket] [--unattended]
```

(brackets around the whole target, not just `--unattended`, since it's now optional). Then change the file's opening intro sentence (currently "Creates or resumes `docs/.tasks/YYYY-MM-DD-<feature-slug>/` and runs the Chain flow from wherever its `STATE.md` left off. Also the entry point for monitoring and stale-detecting an unattended run (see Resuming and monitoring)."):

```markdown
Creates or resumes `docs/.tasks/YYYY-MM-DD-<feature-slug>/` and runs the Chain flow from wherever its `STATE.md` left off, given a target. With no target, runs a backoff-paced monitoring check of every active Unattended task instead (see Resuming and monitoring).
```

Then insert a fourth bullet at the top of the `## Input resolution` list, before the "A bare slug" bullet:

```markdown
- Empty `$ARGUMENTS` — no target given at all. Run **Backoff loop mode** (below, under `## Resuming and monitoring`) and stop here — do not fall through to slug/path/ticket resolution, do not ask an `AskUserQuestion` about Attended-vs-unattended, and do not dispatch `task-orchestrator` Plan Mode. This is the one case Input resolution doesn't resolve to a single task.
```

- [ ] **Step 2: Add matching carve-outs to Attended vs. unattended and Invocation**

Insert one sentence at the very start of the `## Attended vs. unattended` section, before its existing "If `--unattended` is present..." line:

```markdown
(This section applies once a single target has been resolved — see Input resolution's empty-`$ARGUMENTS` case above, which never reaches here.)
```

Insert the same sentence at the very start of the `## Invocation` section, before its existing "Once resolved..." line, for the same reason — both sections otherwise read as unconditional once Input resolution stops being the only gate.

- [ ] **Step 3: Insert the backoff loop mode after the existing Monitor paragraph**

In `commands/cairn-run-task.md`, insert this new subsection directly after the `**Monitor.**` paragraph (line 46) and before the `**Stale detection.**` paragraph (line 48):

```markdown
**Backoff loop mode.** `/cairn-run-task` invoked with no target (e.g. under the built-in `/loop` skill, `/loop /cairn-run-task`) checks every active Unattended task in one pass instead of a single named target — this is the mode Input resolution's empty-`$ARGUMENTS` bullet routes to:

1. `Glob docs/.tasks/*/STATE.md`, filter to `Mode: Unattended` and `Phase` not `PUBLISH`, and exclude any task whose `Status` field already starts with `STALLED (<timestamp>)` (see Stale detection below — this marker is what makes exclusion durable across `/loop` restarts, not this loop's own transient memory; `Status` is used rather than `Harness flags` because `Harness flags` is read by `task-orchestrator` Publish Mode for its harness/doc-drift question and a monitoring marker there would be misread as one). A task at `HANDOFF NEEDED` stays in the discovery set (see item 3) — it is not excluded, only its repeat message is suppressed; a task at `PUBLISH` or already carrying the `STALLED` marker is the only kind excluded.
2. Per task, per tick: read `Phase` + count `HISTORY.md` lines matching the `<ISO-8601 UTC> — <PHASE> — <note>` line format documented in `skills/coding-chain-shared/SKILL.md` (not a raw line count of the whole file, which would also count the heading and blank separator lines), compare against the last-seen fingerprint kept in this loop's own running state (not written to any task file — read-only, same as Monitor above).
3. Unchanged → double that task's own backoff interval (start 1 min, cap 30 min); no message — except a task sitting at `HANDOFF NEEDED` whose fingerprint is genuinely unchanged still gets checked at its current interval (up to the 30-min cap) rather than being dropped, so a later phase advance past `HANDOFF NEEDED` is still observed; suppress only a repeat of the *same* pending-question message, not the check itself, and never apply item 4's `STALLED` rule to a `HANDOFF NEEDED` task regardless of tick count — a task correctly waiting on a human answer is never `STALLED`. Changed → reset that task's interval to 1 min, message the user with the new `Phase`/latest `HISTORY.md` line (plus the pending question from `Key info` and a bounded `tmux capture-pane`, per Monitor's existing rule, narrowed to first sighting in this loop if the new `Phase` is `HANDOFF NEEDED`).
4. Once a task's own backoff has been at the 30-min cap for 3 consecutive unchanged ticks — **and its `Phase` is not `PUBLISH` or `HANDOFF NEEDED`, per item 3's exception** — declare `STALLED` per Stale detection below (which writes the durable marker item 1 reads) and drop it from this tick's active set.
5. A task reaching `PUBLISH` gets one final message (PR/MR URL) and is naturally excluded from future ticks by item 1's `Phase` filter.
6. Return control to `/loop` after each pass — this command never owns the timer itself, the same pattern the built-in `/loop` skill already provides for any recurring check.

Silent on an unchanged tick across the board — the whole point of backing off. See `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md` for the full design.
```

- [ ] **Step 4: Rewrite the Stale detection paragraph's fingerprint definition**

The existing `**Stale detection.**` paragraph currently reads: "Fingerprint each check as `git rev-parse HEAD` + `git status --porcelain` (inside the worktree) + `STATE.md`'s `Phase`. If the fingerprint is unchanged across repeated checks with no phase advancement and no terminal state (`PUBLISH` or `HANDOFF NEEDED`), report `STALLED` — record it in `STATE.md`/`HISTORY.md` and stop the detached run with `tmux kill-session -t <branch>`. `STALLED` is distinct from a clean finish and from a clean pause." Replace the whole paragraph (don't just append) with:

```markdown
**Stale detection.** The backoff loop mode above supplies the "repeated checks" this relies on: 3 consecutive unchanged ticks once a task's own backoff interval has reached its 30-min cap (≈90 min of confirmed no-progress at the slowest cadence) triggers `STALLED` — the loop's cheap `Phase` + `HISTORY.md`-line-count fingerprint (backoff loop mode, item 2) is sufficient on its own; a manual single-target check may additionally confirm with `git rev-parse HEAD` + `git status --porcelain` (inside the worktree) before declaring `STALLED` if extra certainty is wanted, but the loop's own repeated-tick trigger doesn't require it. `STALLED` never fires on a task whose `Phase` is `PUBLISH` (already terminal) or `HANDOFF NEEDED` (a clean pause, not a stall — the backoff loop's item 3/4 exception is what enforces this). On `STALLED`: prepend `STALLED (<ISO-8601 UTC timestamp>) — ` to `STATE.md`'s `Status` field (the one field with no other programmatic reader, unlike `Harness flags`) and append a `HISTORY.md` line, then stop the detached run with `tmux kill-session -t <branch>`. `STALLED` is distinct from a clean finish and from a clean pause — it is not a `Phase` value (the `Phase` vocabulary in `skills/coding-chain-shared/SKILL.md` is unchanged by this), it's a marker the backoff loop's own discovery filter (item 1 above) reads to exclude an already-stalled task durably across `/loop` restarts.
```

- [ ] **Step 5: Update README.md and CLAUDE.md to mention the new mode**

`README.md`'s `/cairn-run-task` bullet and `CLAUDE.md`'s "Two entry points reach Chain flow" paragraph both currently describe `/cairn-run-task <slug-or-path-or-ticket>` as taking a required target. In `README.md`, change:

```markdown
- `/cairn-run-task [slug-or-path-or-ticket] [--unattended]` — creates or resumes a coding-chain task and runs it from wherever its `STATE.md` left off, dispatching to whichever agent the current phase hands off to. Also the entry point for monitoring an unattended (tmux-detached) run and detecting a stalled one. With no target (e.g. under `/loop /cairn-run-task`), checks every active Unattended task on a backing-off cadence instead. Chain flow only — small Direct-mode bug fixes have no task file to resume.
```

In `CLAUDE.md`, in the "Two entry points reach Chain flow" paragraph, change the `/cairn-run-task <slug-or-path-or-ticket>` clause to:

```markdown
`/cairn-run-task [slug-or-path-or-ticket]` (resolves or creates the task folder, asks Attended-vs-Unattended if not already recorded on `STATE.md`, then dispatches to whichever agent the task's current `Phase`/`Handoff to:` names — `task-orchestrator` Plan Mode for a fresh or `PLAN`-phase task, the mid-chain agent otherwise; also the entry point for the read-only monitoring pass and stale detection over an Unattended run, and, with no target, a backoff-paced check of every active Unattended task at once — see `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md`)
```

- [ ] **Step 6: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 7: Headless smoke test**

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

2026-08-18T00:00:00Z — PLAN — fixture line.
EOF
claude -p "/cairn:cairn-run-task" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: the reported output describes discovering `docs/.tasks/2026-08-18-fake-task/` (Unattended, `Phase: QA-RED`, not terminal, `Status` not already prefixed `STALLED`), reading its fingerprint (`Phase` `QA-RED` + 1 matching `HISTORY.md` line — the single `<ISO-8601 UTC> — PLAN — ...` line, not the heading or blank separator), and since this is the first tick (no prior fingerprint in this fresh invocation), either reports it as newly-seen or silently establishes baseline per the loop's own Step 3 item 2 — inspect the reported text for this reasoning rather than expecting multi-tick backoff behavior from a single headless call (that requires actual repeated `/loop` ticks, which this smoke test can't drive non-interactively).

- [ ] **Step 8: Commit**

```bash
git add commands/cairn-run-task.md README.md CLAUDE.md
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
