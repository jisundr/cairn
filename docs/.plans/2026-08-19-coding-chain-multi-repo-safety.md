# Coding-Chain Multi-Repo Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `task-orchestrator` so a plan spanning the parent repo and one submodule commits and publishes correctly in both, add a non-blocking `/goal` misuse guard, and move the Chain-vs-`/goal` complexity heuristic into `plan-writing` itself so it can't be silently skipped.

**Architecture:** Three independent-but-related fixes across cairn's own agent/skill/hook definitions (no application code — these are markdown process instructions and one shell hook). `task-orchestrator`'s Plan Mode gains a three-way submodule-scope branch plus a new submodule-initialization step; its Publish Mode becomes a repo-ordered sequence (submodule commit/push/PR before parent) instead of a single-repo assumption. A new `UserPromptSubmit` hook warns when `/goal` is pointed at a raw plan file instead of a proper goal file. `plan-writing` gains a new step that applies the existing Chain-vs-Direct regression-risk heuristic before ever offering to draft a `/goal` file, replacing the version of that heuristic currently living only as `CLAUDE.md` prose.

**Tech Stack:** Bash (hook script + smoke test), Markdown (agent/skill/doc edits) — no application code, no new dependencies.

**Spec:** `docs/.specs/2026-08-19-coding-chain-multi-repo-safety-design.md`

## Global Constraints

- Scope is parent repo + exactly one submodule — no generic N-submodule support (spec Non-goals).
- The `/goal` guard is non-blocking, best-effort, `exit 0` on any failure — matches `check-setup.sh`/`log-version.sh`'s existing philosophy, never a hard block (spec Non-goals).
- `task-orchestrator`'s prior "every path in submodule → scope worktree to submodule" behavior must be preserved unchanged for a submodule-only plan (no parent paths touched) — the new dual-repo machinery only applies to the *mixed* case (both parent and submodule paths touched).
- `task-orchestrator` stays generic across arbitrary future plans/projects — never hardcode "dashboard" as a submodule name; always use the actually-detected submodule path.
- No automated pytest/smoke coverage for LLM-instruction changes (Tasks 2–4 below) — verified by code inspection plus a manual dry-run, per the spec's Testing strategy. Task 1's hook is pure deterministic shell and gets real smoke-test coverage.

---

### Task 1: `/goal` misuse guard hook

**Files:**
- Create: `hooks/scripts/goal-guard.sh`
- Modify: `hooks/hooks.json`
- Create: `tests/smoke/test_goal_guard.sh`

**Interfaces:**
- Produces: `hooks/scripts/goal-guard.sh` — reads stdin JSON's `prompt` field (Claude Code's `UserPromptSubmit` hook contract, same stdin-JSON pattern `log-version.sh` uses for `session_id`). On a match, prints `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"<message>"}}` to stdout and exits 0. On no match, or any missing dependency (no `jq`), prints nothing and exits 0.

- [ ] **Step 1: Write the failing smoke test**

```bash
# tests/smoke/test_goal_guard.sh
#!/usr/bin/env bash
# Smoke test for hooks/scripts/goal-guard.sh. Pure deterministic shell, no
# LLM involved — unlike the release-manager smoke tests in this directory
# (which invoke `claude -p` because they test LLM judgment), this feeds
# fixture stdin JSON straight to the hook script and asserts exact
# stdout/exit code per case.
#
# Usage: bash tests/smoke/test_goal_guard.sh [plugin-dir]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
HOOK="$PLUGIN_DIR/hooks/scripts/goal-guard.sh"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-goal-guard-test.XXXXXX)"
trap 'rm -rf "$SCRATCH_DIR"' EXIT

FAIL=0

run_hook() {
  # $1 = prompt text
  jq -n --arg prompt "$1" '{prompt: $prompt}' | (cd "$SCRATCH_DIR" && "$HOOK")
}

# Case 1: raw plan path, no sibling goal file -> warns, mentions no goal file exists
mkdir -p "$SCRATCH_DIR/docs/.plans"
: > "$SCRATCH_DIR/docs/.plans/2026-01-01-foo.md"
OUT1="$(run_hook '/goal docs/.plans/2026-01-01-foo.md')"
if ! echo "$OUT1" | grep -q "does not execute a plan"; then
  echo "FAIL case 1: expected explanatory warning, got: $OUT1"
  FAIL=1
fi
if ! echo "$OUT1" | grep -q "No goal file exists"; then
  echo "FAIL case 1: expected 'no goal file exists' hint, got: $OUT1"
  FAIL=1
fi

# Case 2: raw plan path, sibling goal file present -> warns, points at the sibling
: > "$SCRATCH_DIR/docs/.plans/2026-01-01-foo-goal.md"
OUT2="$(run_hook '/goal docs/.plans/2026-01-01-foo.md')"
if ! echo "$OUT2" | grep -q "2026-01-01-foo-goal.md"; then
  echo "FAIL case 2: expected the sibling goal file to be named, got: $OUT2"
  FAIL=1
fi

# Case 3: a proper goal file itself -> no warning
OUT3="$(run_hook '/goal docs/.plans/2026-01-01-foo-goal.md')"
if [ -n "$OUT3" ]; then
  echo "FAIL case 3: expected no output for a proper goal file, got: $OUT3"
  FAIL=1
fi

# Case 4: /goal with a plain condition sentence, not a path -> no warning
OUT4="$(run_hook '/goal all tests pass')"
if [ -n "$OUT4" ]; then
  echo "FAIL case 4: expected no output for a non-path condition, got: $OUT4"
  FAIL=1
fi

# Case 5: /goal pointed at an .md file outside docs/.plans/ -> no warning
OUT5="$(run_hook '/goal README.md')"
if [ -n "$OUT5" ]; then
  echo "FAIL case 5: expected no output for a path outside docs/.plans/, got: $OUT5"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_goal_guard"
  exit 0
else
  echo "FAIL: test_goal_guard"
  exit 1
fi
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `bash tests/smoke/test_goal_guard.sh`
Expected: FAIL — `hooks/scripts/goal-guard.sh: No such file or directory`

- [ ] **Step 3: Write the hook script**

```bash
# hooks/scripts/goal-guard.sh
#!/usr/bin/env bash
#
# goal-guard.sh — warns when /goal is pointed directly at a raw
# implementation plan instead of a proper goal file (the *-goal.md
# convention plan-writing itself produces). Non-blocking, best-effort:
# exits 0 in every case, same philosophy as check-setup.sh/log-version.sh.
#
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
prompt=$(printf '%s' "$input" | jq -r '.prompt // empty')
[[ -z "$prompt" ]] && exit 0

# Only match "/goal <something ending in .md>" -- any other /goal form (a
# plain condition sentence, /goal with no args, /goal clear) is expected
# usage, not the misuse this guards against.
if [[ "$prompt" =~ ^/goal[[:space:]]+([^[:space:]]+\.md)([[:space:]]|$) ]]; then
  path="${BASH_REMATCH[1]}"
else
  exit 0
fi

# Only warn for a path under docs/.plans/ that doesn't already look like a
# goal file.
case "$path" in
  docs/.plans/*-goal.md) exit 0 ;;
  docs/.plans/*.md) ;;
  *) exit 0 ;;
esac

slug=$(basename "$path" .md)
sibling="docs/.plans/${slug}-goal.md"
if [[ -f "$sibling" ]]; then
  hint=" A goal file already exists for this plan at ${sibling} -- did you mean to run /goal with that file's condition instead?"
else
  hint=" No goal file exists for this plan yet -- plan-writing can draft one, or run /cairn-run-task ${slug} to execute the plan directly."
fi

context="/goal sets a completion condition for autonomous looping -- it does not execute a plan. ${path} looks like a raw implementation plan, not a goal condition.${hint}"
jq -n --arg ctx "$context" '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$ctx}}'
```

Make it executable: `chmod +x hooks/scripts/goal-guard.sh`

- [ ] **Step 4: Register the hook**

Modify `hooks/hooks.json` — add a `UserPromptSubmit` array alongside the existing `SessionStart` one:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PLUGIN_ROOT/hooks/scripts/check-setup.sh\"",
            "statusMessage": "Checking cairn setup..."
          },
          {
            "type": "command",
            "command": "\"$CLAUDE_PLUGIN_ROOT/hooks/scripts/log-version.sh\"",
            "statusMessage": "Logging cairn version..."
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PLUGIN_ROOT/hooks/scripts/goal-guard.sh\"",
            "statusMessage": "Checking /goal usage..."
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 5: Run the smoke test to verify it passes**

Run: `bash tests/smoke/test_goal_guard.sh`
Expected: `PASS: test_goal_guard` (all 5 cases). (A 6th case, a `"` inside the path, was added later by a qa-auditor fix-cycle round-trip — it caught that the `printf` interpolation above breaks on that character; the shipped hook uses `jq -n --arg` instead. Historical note, not part of this task's original scope.)

Deliberately not added to `tests/smoke/run_all.sh` — that runner is scoped to `release-manager`'s suite specifically (its own header comment says so), and this test has no relation to `release-manager`. Run it standalone: `bash tests/smoke/test_goal_guard.sh`.

- [ ] **Step 6: Commit**

```bash
chmod +x tests/smoke/test_goal_guard.sh
git add hooks/scripts/goal-guard.sh hooks/hooks.json tests/smoke/test_goal_guard.sh
git commit -m "feat: add /goal misuse guard hook"
```

---

### Task 2: `task-orchestrator` Plan Mode — submodule detection and initialization

**Files:**
- Modify: `agents/task-orchestrator.md` (Step 3, new Step 5.5, Step 9, frontmatter description, START summary)
- Modify: `skills/coding-chain-shared/assets/task/STATE.template.md`

**Interfaces:**
- Produces: `STATE.md`'s new `Submodule: <path> | none` and `Submodule branch: <name> | none` fields — Task 3 (Publish Mode) consumes these to decide whether to run its new per-repo publish steps.

- [ ] **Step 1: Redefine Step 3 — Submodule scope detection**

In `agents/task-orchestrator.md`, replace:

```markdown
### Step 3 — Submodule scope detection

Read the plan's Files section. If every listed path sits inside a submodule directory (`Bash git submodule status` to identify submodule roots), scope the worktree/branch to that submodule instead of the parent repo — record this in `STATE.md`'s `Worktree` field (the submodule-relative path).
```

with:

```markdown
### Step 3 — Submodule scope detection

Read the plan's Files section. Run `Bash git submodule status` to identify submodule roots, then check which of those roots any listed path falls under, and whether any listed path falls **outside** every submodule root (i.e. in the parent repo proper).

- **No path falls inside any submodule root** → `Submodule: none`. Proceed exactly as before this change.
- **Every path falls inside exactly one submodule root, and no path falls outside it** → unchanged from this agent's prior behavior: scope the worktree/branch to that submodule instead of the parent repo (record the submodule-relative path in `STATE.md`'s `Worktree` field, per the existing convention). `Submodule: none` for `STATE.md` purposes — Publish Mode operates single-repo, entirely inside the submodule, since nothing in the parent repo changed. Step 5.5 does not apply in this case.
- **Paths fall both inside exactly one submodule root and outside it (in the parent repo)** — the mixed case this agent supports: parent-repo and submodule-repo paths both touched (see `docs/.specs/2026-08-19-coding-chain-multi-repo-safety-design.md` §A for the full design). Worktree/branch scope stays the parent repo (Step 5, unchanged placement). Record the touched submodule's path for Step 5.5 and `STATE.md`'s new `Submodule` field (Step 9).
- **Paths fall inside more than one distinct submodule root** → out of this agent's supported scope (parent + exactly one submodule). Set `Submodule: none`, and note `[warning] plan touches multiple submodules — not auto-handled, submodule-side commits/PRs must be created manually` in `Key info` at Step 9. Do not attempt Step 5.5.
```

- [ ] **Step 2: Add new Step 5.5 — Submodule initialization**

In `agents/task-orchestrator.md`, immediately after Step 5 ("Branch/worktree creation") and before Step 6 (".harness/ absence suggestion"), insert:

```markdown
### Step 5.5 — Submodule initialization (mixed-scope plans only)

Only runs when Step 3 recorded a touched submodule in the **mixed** case (parent paths and exactly one submodule's paths both touched). Skip entirely otherwise — including the submodule-only case, where Step 5 already scoped the worktree to the submodule directly.

Inside the worktree Step 5 just created: `Bash git submodule update --init <submodule-path>` to populate the submodule — a fresh `git worktree add` does not carry submodule content into the new worktree, so without this step `<submodule-path>` is an empty directory. Then `Bash cd <submodule-path> && git checkout -b <branch-name>`, using the exact same branch name Step 5 chose for the parent, so both repos carry matching branches for this one task.
```

- [ ] **Step 3: Update Step 9 — Write STATE.md**

In `agents/task-orchestrator.md`'s Step 9, find:

```
`Worktree`, `Branch` (from Step 5), `Key info`
```

Replace with:

```
`Worktree`, `Branch` (from Step 5), `Submodule`, `Submodule branch` (from Step 3/5.5 — `none`/`none` if no submodule was touched, or if the plan touches only submodule paths with no parent paths, per Step 3's second bullet), `Key info`
```

- [ ] **Step 4: Update the frontmatter description**

In `agents/task-orchestrator.md`'s YAML frontmatter `description` field, find:

```
creates the branch/worktree via superpowers:using-git-worktrees.
```

Replace with:

```
creates the branch/worktree via superpowers:using-git-worktrees, plus submodule initialization for a plan touching both the parent repo and one submodule.
```

- [ ] **Step 5: Update the START summary**

In `agents/task-orchestrator.md`'s `## START` section, Plan Mode numbered list, find:

```
5. Create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` (Step 5); suggest `harness-engineer` if `.harness/` is absent entirely (Step 6).
```

Replace with:

```
5. Create branch/worktree via `Skill(skill: "superpowers:using-git-worktrees")` (Step 5); initialize the touched submodule inside it for a mixed-scope plan (Step 5.5); suggest `harness-engineer` if `.harness/` is absent entirely (Step 6).
```

- [ ] **Step 6: Add the STATE.md template fields**

In `skills/coding-chain-shared/assets/task/STATE.template.md`, find:

```
Worktree: <path>
Branch: <branch-name>
Key info: <whatever the next agent needs right now>
```

Replace with:

```
Worktree: <path>
Branch: <branch-name>
Submodule: none
Submodule branch: none
Key info: <whatever the next agent needs right now>
```

- [ ] **Step 7: Verify manually**

Read `agents/task-orchestrator.md` back and confirm: Step 3's four bullets are mutually exclusive and cover every case (none / submodule-only / mixed / multiple-submodules); Step 5.5 sits between Step 5 and Step 6 with no duplicate step numbers; Step 9's field list reads correctly as prose; the frontmatter description and START summary both mention the new behavior without contradicting Step 3/5.5's actual wording. Read `skills/coding-chain-shared/assets/task/STATE.template.md` back and confirm the two new lines default to `none`, matching `Harness flags`' existing "seeded as none" convention.

- [ ] **Step 8: Commit**

```bash
git add agents/task-orchestrator.md skills/coding-chain-shared/assets/task/STATE.template.md
git commit -m "feat: task-orchestrator Plan Mode submodule detection and init"
```

---

### Task 3: `task-orchestrator` Publish Mode — per-repo commit/push/PR sequence

**Files:**
- Modify: `agents/task-orchestrator.md` (Steps 1, 4–9, frontmatter description, START summary, PHASE HANDOFF Publish-terminal block)

**Interfaces:**
- Consumes: `STATE.md`'s `Submodule`/`Submodule branch` fields (Task 2).

- [ ] **Step 1: Update Publish Mode Step 1 — Read state**

In `agents/task-orchestrator.md`'s Publish Mode Step 1, find:

```
`Read` `STATE.md` for `Worktree`, `Branch`, `Plan`, `Ticket`, and `Harness flags`.
```

Replace with:

```
`Read` `STATE.md` for `Worktree`, `Branch`, `Submodule`, `Submodule branch`, `Plan`, `Ticket`, and `Harness flags`.
```

- [ ] **Step 2: Replace Steps 4–6 with the repo-ordered publish sequence**

In `agents/task-orchestrator.md`, replace the three sections "### Step 4 — Remote host detection", "### Step 5 — Consolidated commit", and "### Step 6 — PR/MR creation" (their full original text) with:

```markdown
### Step 4 — Remote host detection

Run once per repo in play. Always for the parent: `Bash git remote get-url origin` from the worktree root — host from the URL, `github.com` → `gh`, `gitlab.com` (or a custom GitLab host) → `glab`; `origin` wins on multi-remote signals. If `STATE.md`'s `Submodule` field is not `none`, run the same detection again from inside `<submodule-path>` — its remote can differ from the parent's.

### Step 5 — Submodule publish (only if `Submodule` is not `none`)

From inside `<submodule-path>`: stage and commit everything there (plain conventional-commit message — `.harness/workflow.md` conventions belong to the parent repo, not necessarily the submodule, so this commit doesn't read that section). Never `--no-verify` on a hook failure — stop and report instead (EXIT & DERAILMENT HANDLING). `Bash git push -u origin <submodule-branch>`. Create the PR/MR via the CLI detected for the submodule in Step 4. Record the resulting URL — this is what Step 6's parent PR body links.

Skip this step entirely when `Submodule: none` — proceed straight to Step 6.

### Step 6 — Parent publish

Back in the parent worktree root (if Step 5 ran, `cd` back out of the submodule first). Stage and commit everything, including the task folder's final state — it was working scratch while the chain ran, and this commit is what makes it permanent history once merged. When Step 5 ran, this commit now correctly captures the submodule's new pushed commit via `git add <submodule-path>` — the submodule pointer only updates to a commit that already exists, which Step 5 guaranteed by committing and pushing first. Commit message format follows `.harness/workflow.md`'s `## Commits / MR` conventions if loaded, else a plain conventional-commit default. Never `--no-verify` on a hook failure — stop and report instead.

Create the parent PR/MR via the CLI detected for the parent in Step 4. Body includes the UAT checklist (Step 2) at minimum, the usage report (Step 2.5) when it produced a table, plus whatever else `.harness/workflow.md` requires — and, when Step 5 ran, one additional line: `Submodule PR: <url from Step 5>`. Record the resulting URL.
```

- [ ] **Step 3: Update Step 7 — Ticket sync (In Review)**

Find:

```markdown
### Step 7 — Ticket sync (In Review)

If ticket sync is active for this slug: invoke `project-manager`'s Status Sync entry point with `slug` + target status `In Review`, now that the PR/MR exists.
```

Replace with:

```markdown
### Step 7 — Ticket sync (In Review)

If ticket sync is active for this slug: invoke `project-manager`'s Status Sync entry point with `slug` + target status `In Review`. When `Submodule` is not `none`, this fires only once **both** Step 5 and Step 6 have produced their PR/MR URLs — not after Step 5 alone.
```

- [ ] **Step 4: Update Step 8 — Ticket sync (Done) and plan cleanup**

Find:

```markdown
### Step 8 — Ticket sync (Done) and plan cleanup

If ticket sync is active: note a follow-up check (not a blocking wait) to invoke `project-manager`'s Status Sync with target status `Done` once the PR/MR is observed merged/closed — this may happen in a later invocation, not necessarily this same Publish Mode run. Once ticket closure is actually observed (immediately if it coincides with this run, or on that later invocation otherwise): delete `docs/.plans/<slug>.md` — the ticket is now the permanent record. When no ticket sync is configured, never delete the plan file automatically.
```

Replace with:

```markdown
### Step 8 — Ticket sync (Done) and plan cleanup

If ticket sync is active: note a follow-up check (not a blocking wait) to invoke `project-manager`'s Status Sync with target status `Done` once the PR/MR is observed merged/closed — this may happen in a later invocation, not necessarily this same Publish Mode run. When `Submodule` is not `none`, "observed merged/closed" means both the submodule and parent PRs — this may span two separate later invocations, not necessarily the same one. Once ticket closure is actually observed for every PR/MR in play (immediately if it coincides with this run, or on a later invocation otherwise): delete `docs/.plans/<slug>.md` — the ticket is now the permanent record. When no ticket sync is configured, never delete the plan file automatically.
```

- [ ] **Step 5: Update Step 9 — Update STATE.md**

Find:

```markdown
### Step 9 — Update STATE.md

Update `STATE.md` to `Phase: PUBLISH`, `Handoff to: none (terminal)`, PR/MR URL in `Key info`. Append the final `HISTORY.md` line — same `<ISO-8601 UTC> — PUBLISH — <note>` format as every other phase line.
```

Replace with:

```markdown
### Step 9 — Update STATE.md

Update `STATE.md` to `Phase: PUBLISH`, `Handoff to: none (terminal)`. `Key info` holds the PR/MR URL(s): a single URL as before when `Submodule: none`, or `PR (<submodule-name>) : <url> · PR (parent): <url>` — using the submodule's actual directory name, never a hardcoded name — when a submodule was involved. Append the final `HISTORY.md` line — same `<ISO-8601 UTC> — PUBLISH — <note>` format as every other phase line.
```

- [ ] **Step 6: Update the Publish Mode PHASE HANDOFF terminal block**

Find, inside the ` ```` ` fenced block under "**Publish Mode — terminal:**":

```
PR/MR   → <url>
```

Replace with:

```
PR/MR   → <url> [or, when a submodule was published: PR (<submodule-name>) → <url>, PR (parent) → <url>, each on its own line]
```

- [ ] **Step 7: Update the frontmatter description**

In `agents/task-orchestrator.md`'s YAML frontmatter `description` field, find:

```
Publish Mode: consolidated commit, PR/MR via gh/glab, UAT checklist,
```

Replace with:

```
Publish Mode: consolidated commit (or, for a plan touching both the parent repo and one submodule, a per-repo commit/push/PR sequence, submodule first), PR/MR via gh/glab, UAT checklist,
```

- [ ] **Step 8: Update the START summary**

In `agents/task-orchestrator.md`'s `## START` section, Publish Mode numbered list, find:

```
4. Detect the remote host (Step 4); make the consolidated commit (Step 5).
5. Create the PR/MR with the UAT checklist (Step 6); call `project-manager` Status Sync → In Review (Step 7).
6. Note the Done/plan-deletion follow-up, act on it now if closure already coincides with this run (Step 8).
7. Update `STATE.md` to `Phase: PUBLISH`, final `HISTORY.md` entry (Step 9).
8. Emit the terminal `PHASE HANDOFF` block — no further handoff, chain ends here.
```

Replace with:

```
4. Detect the remote host(s) — parent, plus the submodule if `Submodule` isn't `none` (Step 4).
5. If a submodule is in play, commit + push + open its PR/MR first (Step 5).
6. Commit + push the parent — now capturing the submodule's new commit if one was published — and open its PR/MR with the UAT checklist, linking the submodule PR when applicable (Step 6).
7. Call `project-manager` Status Sync → In Review, once every PR/MR in play exists (Step 7).
8. Note the Done/plan-deletion follow-up, act on it now if closure already coincides with this run — waiting on every PR/MR in play (Step 8).
9. Update `STATE.md` to `Phase: PUBLISH`, final `HISTORY.md` entry, recording one or two PR/MR URLs (Step 9).
10. Emit the terminal `PHASE HANDOFF` block — no further handoff, chain ends here.
```

- [ ] **Step 9: Fix the HARD REQUIREMENTS conflict and dangling "consolidated commit" wording**

In `agents/task-orchestrator.md`'s `## HARD REQUIREMENTS (NON-NEGOTIABLE)` section, find:

```
- ALWAYS detect the remote host from `origin` only (`git remote get-url origin`) — never publish to multiple remotes even if more than one is configured.
- NEVER bypass a failing git hook with `--no-verify` on the consolidated commit — surface it as a blocking `TERMINATED`-style stop instead.
```

Replace with:

```
- ALWAYS detect the remote host from each in-play repo's own `origin` only (`git remote get-url origin`) — never publish to multiple remotes *of the same repo* even if more than one is configured. A mixed-scope plan's parent and submodule are two different repos with two different `origin`s — publishing to both is the Step 4–6 sequence, not a violation of this rule.
- NEVER bypass a failing git hook with `--no-verify` on any publish commit (submodule or parent) — surface it as a blocking `TERMINATED`-style stop instead.
```

In the `## EXIT & DERAILMENT HANDLING` table, find the row:

```
| Pre-commit hook fails on the consolidated commit | `TERMINATED: pre-commit hook failed. Resolve the reported issue and retry — never bypassed with --no-verify.` |
```

Replace with:

```
| Pre-commit hook fails on any publish commit (submodule or parent) | `TERMINATED: pre-commit hook failed. Resolve the reported issue and retry — never bypassed with --no-verify.` |
```

- [ ] **Step 10: Verify manually**

Read `agents/task-orchestrator.md` back and confirm: Steps 4–9 read as a coherent sequence with no leftover references to the old single-commit/single-PR wording; the PHASE HANDOFF block and START summary both match the new step content; `grep -n "consolidated commit" agents/task-orchestrator.md` shows it only in the (still-correct) submodule-`none` framing inside Step 6's own prose, not as an unconditional claim anywhere else — Step 9 of this task removed the two dangling unconditional references.

- [ ] **Step 11: Commit**

```bash
git add agents/task-orchestrator.md
git commit -m "feat: task-orchestrator Publish Mode per-repo commit/push/PR sequence"
```

---

### Task 4: `plan-writing` complexity-routing

**Files:**
- Modify: `skills/plan-writing/SKILL.md` (new Step 0 in Override 2)
- Modify: `CLAUDE.md` (Chain-flow-sequence heuristic paragraph)

**Interfaces:** None (markdown instructions only, no code).

- [ ] **Step 1: Add Step 0 to Override 2**

In `skills/plan-writing/SKILL.md`, under "## Override 2: optional goal-file authoring", immediately before the existing "1. **Offer.**" line, insert:

```markdown
0. **Complexity check.** Read the plan's `### Task N:` blocks and their **Files** sections. If any task's `Modify: <path>` entry changes an *existing* file's current behavior (not just an appended paragraph/bullet — an edit to existing agent process steps, an existing skill's methodology, or similar), present via `AskUserQuestion`: *"This plan changes existing behavior — recommend running it through the coding chain (`task-orchestrator`) instead of a `/goal` loop, for independent verification. Route through Chain flow, or continue with `/goal`-file drafting?"* — citing which task/file drove the recommendation. This is a judgment call reading the plan, not a mechanical count of `Modify:` lines — the same kind of distinction `qa-auditor` already draws between an added/modified line and a pre-existing one.
   - **Chain flow chosen:** skip the rest of this section entirely — a `/goal` file has no role once Chain flow is running its own Attended/Unattended machinery. Hand off to `task-orchestrator` Plan Mode with the plan's slug instead of the `executing-plans` hand-off in Step 8 below.
   - **Continue with `/goal` chosen, or the plan is purely additive** (every task is `Create:`, or `Modify:` is append-only with no behavior change) — no question needed in the additive case, proceed straight to Step 1 below, unchanged.
```

- [ ] **Step 2: Point CLAUDE.md at the new step instead of restating it**

In `/Users/jaysondelosreyes/cairn/CLAUDE.md`, find the paragraph beginning:

```
Once `plan-writing`'s architectural path has produced `docs/.plans/<slug>.md` — the `brainstorm-first` path only; `proceed-directly` never invokes `plan-writing` and has no plan file to read, so it goes straight to Direct flow below without this step — the invoking session runs one more judgment call before dispatching either `task-orchestrator` Plan Mode or Direct flow: recommend Chain flow, or Direct flow run under `task-orchestrator` Lightweight Start. Read the plan's `### Task N:` blocks and their **Files** sections: if any task's `Modify: <path>` entry changes an *existing* file's current behavior (not just an appended paragraph/bullet — an edit to existing agent process steps, an existing skill's methodology, or similar), the plan carries regression risk → recommend **Chain flow**. If every task is `Create:` (new files) or purely additive `Modify:` (append-only, no behavior change), recommend **Direct flow with `task-orchestrator` Lightweight Start**. This is a judgment call made reading the plan, not a mechanical count of `Modify:` lines — the same kind of distinction `qa-auditor` already draws between an added/modified line and a pre-existing one. Present the recommendation via one `AskUserQuestion` — which task/file drove the call, or confirmation that nothing modifies existing behavior — never silently pick either flow. On a Direct-flow recommendation, the "run Lightweight Start first?" ask below stays exactly what it already is (suggested, never forced) — only its framing changes, since this recommendation is specifically about keeping worktree isolation on a small plan, not a signal to skip the ask. See `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md` for the full design.
```

Replace it with:

```
Once `plan-writing`'s architectural path has produced `docs/.plans/<slug>.md` — the `brainstorm-first` path only; `proceed-directly` never invokes `plan-writing` and has no plan file to read, so it goes straight to Direct flow below without this step — the Chain-vs-Direct regression-risk heuristic has already been applied by `plan-writing` itself (its Override 2 Step 0, `skills/plan-writing/SKILL.md`), which recommends Chain flow when the plan changes existing behavior, or falls through toward the existing `/goal`-file offer (and, downstream of that, the "run Lightweight Start first?" ask below, unchanged — suggested, never forced) when the plan is purely additive. This paragraph previously restated that heuristic inline; it now lives in exactly one place, `plan-writing`'s own Step 0, so a session writing a plan can't silently skip it. See `docs/.specs/2026-08-18-chain-direct-heuristic-and-backoff-monitoring-design.md` for the original heuristic design and `docs/.specs/2026-08-19-coding-chain-multi-repo-safety-design.md` for why it moved.
```

- [ ] **Step 3: Update CLAUDE.md's hooks section to name the new hook**

In `/Users/jaysondelosreyes/cairn/CLAUDE.md`, find the `**hooks/hooks.json**` paragraph, beginning:

```
**`hooks/hooks.json`** — `SessionStart` runs two scripts every session: `check-setup.sh` (fast structural sanity check on `agents/intent-analyzer.md`'s frontmatter — silent on success, non-blocking) and `log-version.sh`.
```

and ending:

```
Both scripts are read-only/append-only and exit 0 even on failure — a hook here should never break a session.
```

Replace the opening sentence and the closing sentence (leaving the middle of the paragraph, about `log-version.sh`'s `.cairn/` gating, unchanged) so the paragraph reads:

```
**`hooks/hooks.json`** — `SessionStart` runs two scripts every session: `check-setup.sh` (fast structural sanity check on `agents/intent-analyzer.md`'s frontmatter — silent on success, non-blocking) and `log-version.sh`.
```

(unchanged middle sentences about `log-version.sh`'s gating), then append a new sentence before the final one:

```
`UserPromptSubmit` runs a third script, `goal-guard.sh` — it warns (via `additionalContext`, never blocking) when `/goal` is pointed at a raw plan file under `docs/.plans/` instead of a proper `*-goal.md` file; it depends on `jq` and silently does nothing if `jq` isn't on `PATH`.
```

and change the final sentence from "Both scripts are read-only/append-only" to "All three scripts are read-only/append-only".

- [ ] **Step 4: Update CLAUDE.md's plan-writing description to reflect two cairn-original steps**

In `/Users/jaysondelosreyes/cairn/CLAUDE.md`'s `**spec-writing and plan-writing (skills/)**` paragraph, find:

```
`plan-writing` also runs one additional cairn-original step of its own after `superpowers:writing-plans` completes its flow: an optional offer to draft a `/goal` completion condition for the plan just written, pre-filled from the plan's own acceptance-criteria sections, written to `docs/.plans/YYYY-MM-DD-<feature-name>-goal.md` beside the plan — `/goal` is a built-in Claude Code slash command, not a marketplace skill, so this is a persisted-file-plus-manual-command hand-back, never an auto-invocation. See `docs/.specs/2026-08-18-goal-file-plan-writing-design.md`.
```

Replace with:

```
`plan-writing` also runs two additional cairn-original steps of its own after `superpowers:writing-plans` completes its flow. First, a complexity check applies the Chain-vs-Direct regression-risk heuristic to the plan just written — a plan that changes existing behavior gets routed straight to `task-orchestrator` Plan Mode, skipping the `/goal` offer below entirely. Only when the plan is purely additive (or the user explicitly chooses to stay on the `/goal` path) does the second step run: an optional offer to draft a `/goal` completion condition for the plan, pre-filled from the plan's own acceptance-criteria sections, written to `docs/.plans/YYYY-MM-DD-<feature-name>-goal.md` beside the plan — `/goal` is a built-in Claude Code slash command, not a marketplace skill, so this is a persisted-file-plus-manual-command hand-back, never an auto-invocation. See `docs/.specs/2026-08-18-goal-file-plan-writing-design.md` for the original goal-file design and `docs/.specs/2026-08-19-coding-chain-multi-repo-safety-design.md` §C for the complexity-check step added on top of it.
```

- [ ] **Step 5: Update plan-writing's own frontmatter and intro**

In `skills/plan-writing/SKILL.md`'s YAML frontmatter `description` field, find:

```
and adding an optional final step that drafts a /goal completion condition for the plan.
```

Replace with:

```
and adding two steps after that: a complexity check that can route a plan changing existing behavior to task-orchestrator instead, and — only when it doesn't — an optional step that drafts a /goal completion condition for the plan.
```

In the body's intro paragraph (right below the `# Plan Writing (cairn path override)` heading), find:

```
Thin wrapper around `superpowers:writing-plans`. Does not reimplement or duplicate that skill's methodology — invokes it directly and changes exactly one thing about where the plan is saved, and adds one optional step: drafting a `/goal` completion condition for the plan after it's written.
```

Replace with:

```
Thin wrapper around `superpowers:writing-plans`. Does not reimplement or duplicate that skill's methodology — invokes it directly and changes exactly one thing about where the plan is saved, and adds two steps after that: a complexity check that can route a plan changing existing behavior to `task-orchestrator` instead, and — only when it doesn't — an optional step that drafts a `/goal` completion condition for the plan after it's written.
```

- [ ] **Step 6: Verify manually**

Read `skills/plan-writing/SKILL.md` back and confirm Step 0 sits before the renumbered-in-place Steps 1–8 (their own numbers are unchanged, since Step 0 is a new zero-indexed entry, not a renumbering), that its two bullets are mutually exclusive, and that the frontmatter/intro now match Step 0's existence. Read `CLAUDE.md` back and confirm: the Chain-flow-sequence paragraph no longer restates the `Modify:`/`Create:` heuristic text (only points at it); the hooks paragraph names all three scripts and the `UserPromptSubmit` event; the plan-writing paragraph describes two steps, not one.

- [ ] **Step 7: Commit**

```bash
git add skills/plan-writing/SKILL.md CLAUDE.md
git commit -m "feat: move Chain-vs-goal complexity heuristic into plan-writing"
```

---

## Self-Review Notes

**Spec coverage:** Spec Section A (Plan Mode half) → Task 2. Spec Section A (Publish Mode half) → Task 3. Spec Section B → Task 1. Spec Section C → Task 4. Spec's "Plan Mode Step 10 needs no change" decision → correctly untouched by any task above.

**Placeholder scan:** none — every step has exact file paths, exact before/after text, or runnable code.

**Type consistency:** `Submodule`/`Submodule branch` are introduced once (Task 2, STATE.md template + Step 9 prose) and consumed unchanged by Task 3 (Publish Mode Steps 1, 4–9). The submodule-only case (Step 3's second bullet) is defined once in Task 2 and referenced, not redefined, everywhere else it matters (Task 2 Step 5.5's skip condition, Task 3's Step 9 wording).

**Task independence:** Task 1 has no dependency on 2–4. Task 3 depends on Task 2's `STATE.md` fields existing (noted in Task 3's Interfaces). Task 4 depends on nothing above — could run first or last with no functional difference; placed last because it's the "steering" piece that ties back to using Chain flow at all.
