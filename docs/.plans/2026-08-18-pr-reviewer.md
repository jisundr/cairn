# PR Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port maestro's `gitlab-mr-reviewer` to cairn as `pr-reviewer`, generalized to both GitHub PRs and GitLab MRs, with the full feature set (Initial Review, Fix-Verification Round, Thread Watch, Approval-to-Merge Gate, Pushback Triage) — Thread Watch and its merge capability staying explicit opt-in only.

**Architecture:** One terminal agent (`agents/pr-reviewer.md`), built across four tasks (Initial Review core, Fix-Verification Round, Thread Watch + Approval-to-Merge Gate, then hard requirements/handoff/derailment/start assembly), plus a new `/cairn-watch-pr` command for the explicit Thread Watch entry point. GitHub finding-generation delegates directly to `Skill(skill: "code-review", ...)` (cairn agents can hold the `Skill` tool, unlike maestro's subagents — no Mid-Run Skill Handoff relay needed). GitLab finding-generation is self-implemented, mirroring `code-review`'s categories and effort levels. Host detection reuses `task-orchestrator`'s existing `git remote get-url origin` convention.

**Tech Stack:** Markdown agent-definition file (no code execution), `gh`/`glab` CLIs, `git` for diff/fetch mechanics.

**Spec:** `docs/.specs/2026-08-18-pr-reviewer-design.md`

## Global Constraints

- Draft-then-post are two separate, explicit gates in every mode — never combined.
- Mandatory auto-save to `docs/.reviews/<host>-<owner-repo>-<number>.md` the moment a draft's first version is produced, before it's presented — not itself a confirmation gate; re-saved in place on every later revision.
- Exactly one file per PR/MR, appended across rounds (never a new timestamped file per round, never truncated).
- Never checks out the target's source branch — fetch only.
- Default to plain body-text comments (file/line in the body) — never diff-anchored/inline unless the user explicitly asks, and even then confirm the exact host mechanism before attempting it.
- Thread Watch and the Approval-to-Merge Gate are explicit opt-in only — never auto-started, never auto-merges.
- Findings are reported, never auto-fixed.
- Host detection: `github.com` → `gh`, `gitlab.com`/custom GitLab host → `glab` (same convention as `task-orchestrator`).
- `agents/intent-analyzer.md` itself is never modified by this work.
- `code-review` and `/loop` are core Claude Code capabilities, not third-party plugins — no hard-required/soft-optional install-check applies to either (unlike `idea-explorer`'s `superpowers` dependency or Graphify). An actual failure to resolve either is an EXIT & DERAILMENT case, not a startup capability check.
- `Skill(skill: "code-review", ...)` must resolve Claude Code's built-in code-review capability, never the unrelated community marketplace plugin of the same name — see the EXIT & DERAILMENT table (Task 4 Step 3). No pre-invocation identity check exists; a wrong resolution that posts unconditionally is an accepted residual risk (see that same table), not one this agent can prevent before the first call.

---

### Task 1: `agents/pr-reviewer.md` — core (Input Resolution + Initial Review mode)

**Files:**
- Create: `agents/pr-reviewer.md`

**Interfaces:**
- Consumes: spec sections "Flow" (Input Resolution, Initial Review mode), "Host detection", "Finding generation"; `agents/codebase-auditor.md` for structural convention; `agents/task-orchestrator.md`'s Publish Mode Step 4 / Lightweight Finish Step 1 for the exact host-detection snippet to reuse.
- Produces: the `pr-reviewer` agent name and its Initial Review mode — independently testable (review + draft + post a GitHub or GitLab target) before Fix-Verification Round / Thread Watch exist. Later tasks append to this same file.

- [ ] **Step 1: Write frontmatter**

```yaml
---
name: pr-reviewer
description: "Use this agent to review a GitHub pull request or GitLab merge request end-to-end: resolve the target, generate findings, draft them, and post as comments only after explicit confirmation. Input is a PR/MR URL, or a branch name (+ repo if not inferrable from local origin). GitHub targets delegate finding-generation to Claude Code's built-in code-review capability (Skill(skill: \"code-review\", ...), no --comment — review-only, no posting; a separate, unrelated community marketplace plugin also happens to be named code-review, this agent must resolve the built-in one, never that plugin); GitLab targets are reviewed directly against the fetched diff, mirroring code-review's own categories (correctness, reuse/simplification/efficiency) and effort levels, since no GitLab-aware skill exists to delegate to. Re-invocable on an already-reviewed target as a Fix-Verification Round (checks whether previously-reported findings were fixed, drafts dated follow-up replies) without re-running the review. Also supports an explicit, opt-in Thread Watch mode (driven by the built-in /loop skill, one pass per tick) that monitors a target for new discussion activity until merged/closed, including an Approval-to-Merge Gate that surfaces a merge confirmation once approved — it never merges automatically.

<example>
Context: User wants a GitHub PR reviewed and findings posted as comments.
user: \"Review this PR and post the findings: https://github.com/org/repo/pull/42\"
assistant: \"I'll use pr-reviewer to resolve the PR, draft the findings via the code-review skill, and post them once you confirm.\"
<commentary>
GitHub PR URL, review + post intent. pr-reviewer delegates finding-generation to code-review directly (Skill tool available to this agent), then owns the draft/confirm/post cycle.
</commentary>
</example>

<example>
Context: User wants a GitLab MR reviewed.
user: \"Review MR !12 on gitlab.example.com/group/project\"
assistant: \"I'll use pr-reviewer — no GitLab-aware review skill exists, so it'll fetch the diff and review it directly at the same depth as a GitHub review.\"
<commentary>
GitLab target. pr-reviewer's self-implemented GitLab path mirrors code-review's categories/effort levels rather than delegating.
</commentary>
</example>

<example>
Context: User wants to check whether previously-reported findings were fixed.
user: \"Check if the fixes landed on PR #42\"
assistant: \"I'll use pr-reviewer in Fix-Verification Round mode to check the prior findings against the latest push.\"
<commentary>
Follow-up on an already-reviewed target. pr-reviewer detects its own prior findings and switches to Fix-Verification Round rather than a fresh Initial Review.
</commentary>
</example>"
tools: Read, Write, Edit, Bash, Glob, AskUserQuestion, Skill
model: sonnet
color: purple
---
```

- [ ] **Step 2: Write SYSTEM ROLE + WORKFLOW INTENT**

Model the shape on `agents/codebase-auditor.md` lines 9–25. Content requirements (spec "Summary", "Flow"):
- Produces three things: a findings/round-reply draft (iterated freely, no gate), posted comments (separate explicit gate), and (Thread Watch) recurring notifications until merged/closed.
- Three modes: Initial Review (default), Fix-Verification Round (re-invocation on an already-reviewed target), Thread Watch (explicit opt-in only).
- Terminal — no automatic handoff, except Thread Watch's coding-chain-origin merge-detected marker (see Task 3).
- Triggered by manual dispatch, `intent-analyzer` `review` category + judgment-call mapping documented in `CLAUDE.md` (Task 6), or `/cairn-watch-pr` for Thread Watch specifically (Task 5).

- [ ] **Step 3: Write HARD REQUIREMENTS**

Must include, near-verbatim from the spec (host-neutral rephrasing of maestro's originals):
- NEVER post anything before the draft is finalized — draft iteration and posting are two separate, explicit gates.
- ALWAYS save the first version of the draft to `docs/.reviews/<host>-<owner-repo>-<number>.md` in the same turn it's produced, before presenting it — mandatory, automatic, not itself a gate; re-save in place on every later revision.
- ALWAYS get a separate, explicit `AskUserQuestion` confirmation specifically for posting — a prior "yes" to draft content never implies posting permission.
- Default to plain body-text comments (file/line in the body) — never diff-anchored unless the user explicitly distinguishes "inline on the diff line" from "a comment that mentions the line."
- ALWAYS check for this agent's own prior comments on the target before posting again, to avoid duplicates on re-run.
- NEVER check out the target's source branch in the user's working tree — fetch only.
- Every `gh`/`glab` command runs from inside a git repository — both resolve target context from the local git remote.
- Exactly ONE `docs/.reviews/` file per PR/MR, appended across rounds — never a new file per round, never truncated.

- [ ] **Step 4: Write INPUT RESOLUTION (runs first, every mode)**

Follow spec "Flow" → "Input Resolution" exactly:
1. Parse input: a GitHub PR URL (`github.com/.../pull/<n>`), a GitLab MR URL (`.../-/merge_requests/<n>`), or a branch name (+ repo if not inferrable).
2. Host detection: explicit URL host wins; otherwise `Bash git remote get-url origin` — `github.com` → `gh`, `gitlab.com`/custom GitLab host → `glab` (exact convention from `agents/task-orchestrator.md`'s Publish Mode Step 4).
3. Confirm auth: `gh auth status` / `glab auth status`; stop and report if not authenticated.
4. Mode detection: explicit Thread Watch trigger language / resumed watch ledger → Thread Watch (Task 3). Otherwise fetch the target's existing comments and check for this agent's own signature pattern (a `## Finding N —` heading, or a `**Update (<date>):**` line) → Fix-Verification Round (Task 2) if found, else Initial Review (this task).
5. Fetch (never checkout) both branches fresh, every invocation: `git fetch origin <source-branch>:refs/remotes/origin/<source-branch>` and `git fetch origin <target-branch>` if not already present. Never reuse a prior run's cached SHA range.

- [ ] **Step 5: Write Initial Review mode**

Follow spec "Flow" → "Initial Review mode" exactly:
1. Reference Style Lookup — sample existing comments/notes for a matching structure; fall back to a default format (`## Finding N — <summary> _(<category>)_` / **File** / **Line** / snippet / **Suggested fix**) and say so if none found.
2. Get findings:
   - GitHub: `Skill(skill: "code-review", args: "<PR number or URL>")` — no `--comment`. Omitting it is deliberate: `--comment` makes `code-review` post inline immediately, bypassing this agent's own draft/confirm/post separation (Global Constraints, first bullet). Findings come back to this agent to draft, save, and post itself, same as the GitLab path.
   - GitLab: review directly against the fetched diff — same categories (correctness + reuse/simplification/efficiency) and effort levels as the GitHub path; no skill to delegate to.
3. Draft Phase — format findings, save the first version to `docs/.reviews/<host>-<owner-repo>-<number>.md` immediately (mandatory, before presenting it), then iterate freely with the user (cheap, local, no gate), re-saving in place on every revision.
4. Confirmation & Posting Phase (Task 4 — write a `<TODO placeholder — see Task 4>` marker comment in this step for now; Task 4 replaces it with the real shared section and removes the marker).
5. Post-completion offer: "Watch this PR/MR for new threads until merged? (Y/N)" — declining is a clean no-op; accepting starts Thread Watch (Task 3).

- [ ] **Step 6: Validate**

Run: `claude plugin validate . --strict`
Expected: passes (frontmatter valid even with the file incomplete — later tasks append sections, they don't restructure what's here).

- [ ] **Step 7: Commit**

```bash
git add agents/pr-reviewer.md
git commit -m "Add pr-reviewer agent: Input Resolution + Initial Review mode

First slice of the generalized PR/MR reviewer port. GitHub targets
delegate finding-generation to the code-review skill directly; GitLab
targets are reviewed self-implemented, mirroring the same categories
and effort levels. Fix-Verification Round, Thread Watch, and the
shared Confirmation & Posting Phase land in later tasks.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `agents/pr-reviewer.md` — Fix-Verification Round mode

**Files:**
- Modify: `agents/pr-reviewer.md`

**Interfaces:**
- Consumes: spec "Flow" → "Fix-Verification Round mode"; Task 1's Input Resolution (mode detection already routes here) and Reference Style Lookup format.
- Produces: the Fix-Verification Round section, invoked by Task 1's Input Resolution Step 4 when this agent's own signature is found on the target.

- [ ] **Step 1: Write Fix-Verification Round mode**

Insert a new `## Fix-Verification Round mode` section after `## Initial Review mode`. Follow spec exactly:
1. Re-resolve the target fresh (reuse Input Resolution, never cached state).
2. Fetch comments/discussions (paginated where the host API requires it — GitLab's `--paginate` + `jq -s 'add'`; GitHub's `gh api --paginate`), identify this agent's own prior findings and any author replies, record each finding's thread/discussion identifier, original file/line, and summary.
3. Delta-diff since the last reviewed SHA (recorded in the per-target file from the prior round) against each open finding's file/line — classify `fixed` / `partially-fixed` / `still-open` / `disputed`.
4. Pushback Triage for any `disputed` finding (Task 3 writes the full guidance section; for now, inline the three-rule summary from the spec directly in this step: verify factual pushback against the diff not memory; acknowledge scope/judgment-call pushback without relitigating; require a concrete spec to reopen a declined finding).
5. Draft dated, self-contained round replies: `**Update (<date>):** <tag> — <1-3 sentences>`, mapping FIX ASSESSMENT state to tag (`fixed`→`fix-confirmed`, `partially-fixed`→`partially-fixed`, `still-open`→`still-open`, `disputed`→`concession`/`reopened-with-spec`/`decline-acknowledged`). Same save-first-then-iterate pattern as Initial Review (first version saved immediately, re-saved in place on each revision), appended to the same per-target file.
6. Confirmation & Posting Phase (same `<TODO placeholder — see Task 4>` marker as Task 1 Step 5; Task 4 wires it up for real).

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 3: Commit**

```bash
git add agents/pr-reviewer.md
git commit -m "Add Fix-Verification Round mode to pr-reviewer

Re-invocation path that checks prior findings against the delta since
the last reviewed SHA and drafts dated round replies.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `agents/pr-reviewer.md` — Thread Watch, Approval-to-Merge Gate, Merge Termination, Pushback Triage

**Files:**
- Modify: `agents/pr-reviewer.md`

**Interfaces:**
- Consumes: spec "Flow" → "Thread Watch mode", "Approval-to-Merge Gate", "Merge Termination", "Pushback Triage"; Task 2's Fix-Verification Round logic (Thread Watch reuses it per-tick).
- Produces: the opt-in watch loop, invoked by Initial Review's post-completion offer (Task 1 Step 5.5) or by `/cairn-watch-pr` (Task 5) — Fix-Verification Round has no post-completion watch offer of its own, only Initial Review does.

- [ ] **Step 1: Write the standalone Pushback Triage section**

Replace the inline three-rule summary stubbed in Task 2 Step 1.4 with a full `## Pushback Triage` section (guidance, not a hard checklist, per spec — case-by-case judgment):
1. Factual pushback claim about code behavior — verify directly against the diff, not memory of the original finding. Concede plainly if correct; hold and explain if refuted.
2. Scope/judgment-call pushback — acknowledge and move on, don't relitigate on the first pass.
3. Reopening a declined finding needs a concrete, actionable spec from the user; plain disagreement should prompt a check-in first, not an automatic reopen.

Update Task 2's Fix-Verification Round Step 4 to reference this section instead of inlining the rules.

- [ ] **Step 2: Write Thread Watch mode**

Insert `## Thread Watch mode` (spec "Flow" → "Thread Watch mode"):
- Explicit opt-in only — triggered by the post-completion offer's "Y" answer, or `/cairn-watch-pr`, never auto-started.
- Runs via the built-in `/loop` skill (not cairn-owned), one pass per tick; this agent never sleeps/polls on its own.
- **First entry**: record Watch Origin (`coding-chain` or `review`) and Sibling PR/MRs if any; initialize a Watch Ledger section in the per-target file (Watch Origin, Sibling targets, Seen discussion/comment IDs, Approval State, Merge Prompt Shown For, Last Tick — obtain via `Bash date -u +%Y-%m-%dT%H:%M:%SZ`, never estimated).
- **Per tick**: refresh Input Resolution including current state (`open`/`merged`/`closed`) and approval status (GitHub: `gh pr view --json reviewDecision,mergeStateStatus`; GitLab: `glab api projects/:id/merge_requests/<iid>/approvals --repo <group/project>`). Terminate per Merge Termination (Step 4 below) on `closed`/`merged`. Otherwise diff comments/discussions against the ledger for (a) new replies to this agent's own findings (reuse Fix-Verification Round's logic unchanged) and (b) new threads opened by anyone else; detect approval-state changes.
- Notify new threads (author, snippet, link); draft round replies for (a) and either a substantive response or a lightweight FYI/ack note for (b); append to the ledger file, bump Last Tick.
- When approved and still open, and the merge gate hasn't already been shown for this exact approval state, surface the Approval-to-Merge Gate (Step 3). A tick with nothing new skips straight to a "no new activity" report — no draft, no gate.
- If anything was drafted this tick, run the Confirmation & Posting Phase (Task 4) inline before the tick ends.

- [ ] **Step 3: Write the Approval-to-Merge Gate**

Insert `## Approval-to-Merge Gate` (spec "Flow" → "Approval-to-Merge Gate"):
- Backend-neutral in intent (approval → confirm → merge → follow-through); host-specific mechanics.
- **GitHub**: read merge method from `gh pr view --json mergeStateStatus,mergeable`; merge via `gh pr merge --merge|--squash|--rebase` matching the repo's configured method; honor `.harness/`-documented push-safety convention if present.
- **GitLab**: unchanged from maestro — `glab api projects/:id/merge_requests/<iid>/approvals --repo <group/project>` to read state, `glab mr merge <iid> --repo <group/project> [--squash|--merge] [--remove-source-branch]` to merge.
- NEVER auto-merges. `AskUserQuestion` every time the approval state changes ("Merge now" / "Do nothing — keep watching"); never re-prompts on an unchanged approved state.
- Before merging: run the pre-merge full-diff pass — one more full review pass (not the tick's delta-only scope), report any new findings before proceeding with the merge confirmation.
- On merge success: flow directly into Merge Termination (Step 4) without waiting for the next tick. On merge failure: report and keep watching, never retry blindly.

- [ ] **Step 4: Write Merge Termination**

Insert `## Merge Termination` (spec "Flow" → "Merge Termination"):
- **Watch Origin: review** — report merged, stop. No further action.
- **Watch Origin: coding-chain** — check each declared Sibling PR/MR's state (cheap metadata-only fetch, no discussion fetch, no re-review). All merged (or none declared) → emit:
  ```
  THREAD WATCH: MERGE DETECTED — CODING CHAIN FOLLOW-THROUGH REQUIRED

  PR/MR(s) merged: <this target, plus each Sibling target>
  Task: <slug if known from opening context, else "unknown">
  Action for main loop: Run coding-chain follow-through now (submodule
  sync if applicable), then clear any pending-sync flag for this task.
  Do NOT flip tracker Status here — task-orchestrator already set it
  optimistically at Publish.
  ```
  for the main loop, then stop. One or more siblings still open → report which, do not emit the marker, stop watching this one.
- NEVER flips tracker Status — that stays `task-orchestrator`/`project-manager`'s job (cairn's existing single-writer rule).

- [ ] **Step 5: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 6: Commit**

```bash
git add agents/pr-reviewer.md
git commit -m "Add Thread Watch, Approval-to-Merge Gate, Merge Termination, Pushback Triage to pr-reviewer

Thread Watch stays explicit opt-in, driven by the built-in /loop
skill (not cairn-owned). Approval-to-Merge Gate never auto-merges and runs one more
full-diff pass before an actual merge. GitHub mechanics via gh,
GitLab mechanics unchanged from maestro's original.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `agents/pr-reviewer.md` — Confirmation & Posting Phase, PHASE HANDOFF, EXIT & DERAILMENT, START (assembly + smoke test)

**Files:**
- Modify: `agents/pr-reviewer.md`

**Interfaces:**
- Consumes: spec "Flow" → "Confirmation & Posting Phase"; Tasks 1–3's `<TODO placeholder — see Task 4>` markers (this task removes them and wires the real section in); `agents/codebase-auditor.md`'s PHASE HANDOFF/EXIT & DERAILMENT/START structure.
- Produces: the finished, fully-assembled `agents/pr-reviewer.md`.

- [ ] **Step 1: Write the shared Confirmation & Posting Phase**

Insert `## Confirmation & Posting Phase` (spec "Flow" → "Confirmation & Posting Phase"), then replace every `<TODO placeholder — see Task 4>` marker from Tasks 1–3 with a reference to this section:
1. **Duplicate check** — fetch current comments/discussions (paginated where required), compare drafted content against what's already posted; exclude near-exact matches by default, mention exclusions before asking to post.
2. **Explicit posting confirmation** — `AskUserQuestion`, mode-aware copy (Initial Review finding count / Fix-Verification Round reply count / Thread Watch's combined round-reply-and-FYI-note copy). A prior "yes" to draft content never implies posting permission.
3. **Post**:
   - GitHub top-level: `gh pr comment <number> --body "<text>"`. GitHub thread-level reply: `gh api repos/{owner}/{repo}/pulls/{number}/comments/{comment_id}/replies -f body="<text>"` (`gh pr comment` alone doesn't thread).
   - GitLab new discussion: `glab api "projects/:id/merge_requests/<iid>/discussions" --repo <group/project> -f body="<text>"`. GitLab reply: `glab api "projects/:id/merge_requests/<iid>/discussions/<discussion_id>/notes" --repo <group/project> -f body="<text>"`. GitLab FYI/ack (plain, non-resolvable): `glab api "projects/:id/merge_requests/<iid>/notes" --repo <group/project> -f body="<text>"`.
   - Never diff-anchored/`position`-field comments unless the user explicitly asks, and even then confirm the exact host mechanism first.
   - Capture returned IDs; on a post failure, stop posting further items, report which succeeded/failed, never retry with altered parameters silently.
4. **Un-resolve on reopen** — if a round reply reopens a previously-resolved finding (GitLab: `glab api --method PUT "projects/:id/merge_requests/<iid>/discussions/<discussion_id>?resolved=false" --repo <group/project>`), do it as part of the same posting step.
5. **Summary** — how many posted, their IDs/URLs, anything skipped as duplicate or declined.

- [ ] **Step 2: Write PHASE HANDOFF**

Terminal agent — no automatic PHASE HANDOFF, except the Thread Watch coding-chain-origin merge-detected marker (Task 3 Step 4), which is a mid-run-handoff marker for the main loop, not a handoff to another named agent.

- [ ] **Step 3: Write EXIT & DERAILMENT HANDLING**

Table must include at least (adapted host-neutral from maestro's original):
| Trigger | Response |
|---|---|
| Branch input resolves to zero open PR/MRs | "No open PR/MR found for branch `<branch>`. Provide the URL directly, or confirm a draft-only review with no posting target." |
| Branch input resolves to multiple open PR/MRs | "Multiple open PR/MRs use branch `<branch>`: [list]. Which one?" |
| Host CLI auth check fails | "Not authenticated to `<host>`. Run `gh auth login`/`glab auth login --hostname <host>` and retry." |
| User asks to post before the draft has been shown/confirmed | "Let's finalize the draft first — posting is a separate step once you've confirmed the content." |
| User asks for a diff-anchored inline comment | "Diff-anchored comments need the host's exact line-anchoring schema, and I won't guess at it. Confirm this is really needed — plain body-text comments with file/line are usually the actual convention — and I'll verify the docs before attempting it." |
| User asks to modify source code based on a finding | "Findings are reported, not auto-fixed. Use `task-orchestrator` or `software-engineer` Direct Mode to implement a fix." |
| All findings already appear posted (duplicate check) | "All findings in this draft already appear to be posted. Nothing new to post." |
| Thread Watch requested but target is already merged/closed at the first tick | Report the terminal state immediately (per Merge Termination) and do not start a `/loop`. |
| Thread Watch requested without a clear Watch Origin and it can't be inferred | Ask ONE question: "Is this part of an in-progress coding-chain task, or a standalone review? (Determines whether a merge triggers follow-through.)" |
| User asks Thread Watch to also flip tracker Status on merge | "Thread Watch never writes tracker Status — `task-orchestrator`/`project-manager` own that." |
| User asks to run Thread Watch as a background/dispatched subagent | "Thread Watch needs `AskUserQuestion` for its posting and merge gates, which isn't available in a dispatched background subagent — it has to run in the main thread via `/loop`." |
| `Skill(skill: "code-review", ...)` resolves to something that doesn't match the built-in capability's expected shape (e.g. no effort-level/`--comment` support, or it posts unconditionally with no way to get findings back without posting) | If detected before the call resolves (no effort-level support in the description): stop before drafting, report the mismatch. Accepted residual risk: if a wrong resolution posts unconditionally (an always-posts marketplace plugin sharing the name), that post happens before this agent can detect it — there is no pre-invocation identity check. Report what was posted and by what, and note the target now has an unconfirmed comment from that resolution. |
| Thread Watch is requested and `/loop` can't be resolved | Report that Thread Watch needs the built-in `/loop` capability and can't run here; offer a single manual Fix-Verification Round instead. Never fall back to self-polling or sleeping. |
| An error that doesn't match any other row in this table (looks like a cairn-side defect, not this codebase's) | Attempt `Skill(skill: "feedback-context")`; if it succeeds, surface its one-line suggestion alongside the normal error report. Never blocks — falls through to the normal error report either way. |

- [ ] **Step 4: Write START**

Numbered summary of the full flow (Input Resolution → mode dispatch → mode-specific steps → Confirmation & Posting Phase), modeled on `codebase-auditor.md`'s START section.

- [ ] **Step 5: Validate**

Run: `claude plugin validate . --strict`
Expected: passes clean, no leftover `<TODO placeholder>` markers anywhere in the file (`grep -n "TODO placeholder" agents/pr-reviewer.md` returns nothing).

- [ ] **Step 6: Headless smoke test**

```bash
CAIRN_ROOT="$(pwd)"   # run this from inside the repo/worktree where agents/pr-reviewer.md was just written — NOT a hardcoded path, this plan may run from a worktree
rm -rf /tmp/cairn-pr-reviewer-test   # re-run-safe: fresh scratch dir every time, avoids "remote origin already exists" / accumulating commits on a retry
mkdir -p /tmp/cairn-pr-reviewer-test && cd /tmp/cairn-pr-reviewer-test && git init -q
git commit --allow-empty -q -m "chore: initial commit"
git remote add origin https://github.com/octocat/Hello-World.git
claude -p "review PR #1 on this repo" --plugin-dir "$CAIRN_ROOT" --permission-mode bypassPermissions --output-format text
```
Expected: agent detects `github.com` from `origin`, resolves the `gh` path, runs Input Resolution and Initial Review mode, invoking `Skill(skill: "code-review", ...)`. This is a real public repo/PR so the call should actually resolve — inspect the reported output for **positive evidence** the new `pr-reviewer` agent actually ran (its own draft format, its own mode-detection language, or its own EXIT & DERAILMENT copy — not just "no crash"), since `--plugin-dir` pointing at the wrong tree would silently produce a plausible-looking but unrelated response. A clean "no findings"/auth-required report is fine as long as it's clearly `pr-reviewer`'s own voice, not a generic fallback. Also confirm which `code-review` actually resolved: the built-in one supports effort levels and does not post without `--comment` (this call passes no `--comment`, so **zero new comments should appear on the real PR** — check `gh pr view 1 --repo octocat/Hello-World --json comments` before and after). If a comment appears, the marketplace plugin resolved instead — stop immediately, this is the accepted-residual-risk scenario the EXIT & DERAILMENT table documents, and it means the ambiguity is live in this environment, not just theoretical.

- [ ] **Step 7: Commit**

```bash
git add agents/pr-reviewer.md
git commit -m "Finish pr-reviewer: shared Confirmation & Posting Phase, PHASE HANDOFF, EXIT & DERAILMENT, START

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: `commands/cairn-watch-pr.md`

**Files:**
- Create: `commands/cairn-watch-pr.md`

**Interfaces:**
- Consumes: `commands/cairn-doctor.md` for structural convention; `agents/pr-reviewer.md` (Tasks 1-4) Thread Watch mode as the entry point this dispatches into.
- Produces: the `/cairn-watch-pr` command, referenced in `CLAUDE.md`/`README.md` (Task 6).

- [ ] **Step 1: Write the command file**

```markdown
---
description: "Start a Thread Watch on a GitHub PR or GitLab MR — monitors it for new discussion threads and approval-state changes until merged or closed, driven by the built-in /loop skill, one watch pass per tick. Delegates entirely to pr-reviewer's Thread Watch mode; does not perform an Initial Review itself."
---

## Your task

Start the `pr-reviewer` agent in its **Thread Watch** mode against the PR/MR or branch given as the argument (a GitHub PR URL, a GitLab MR URL, or a branch name plus repo). If Watch Origin (coding-chain vs. review) isn't inferrable from context, `pr-reviewer` will ask.
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 3: Commit**

```bash
git add commands/cairn-watch-pr.md
git commit -m "Add /cairn-watch-pr command

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: `CLAUDE.md` and `README.md` updates

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `agents/pr-reviewer.md` (Tasks 1-4), `commands/cairn-watch-pr.md` (Task 5); existing ported-agent paragraph style (`codebase-auditor`) and command paragraph style (`/cairn-doctor`).

- [ ] **Step 1: Add the `pr-reviewer` agent paragraph to `CLAUDE.md`**

Insert directly after the `release-manager` paragraph added by the release-manager plan (or, if that plan hasn't landed yet in this repo's history, directly after the `qa-auditor` paragraph — before "**End-to-end sequence...**"):

```markdown
**`pr-reviewer` (agents/)** — reviews a GitHub PR or GitLab MR end-to-end: resolves the target, generates findings, drafts them, posts as comments only after explicit confirmation. GitHub targets delegate finding-generation to `Skill(skill: "code-review", ...)` — Claude Code's built-in code-review capability, a core CLI feature rather than a hard-required/soft-optional third-party plugin; an unrelated community marketplace plugin happens to share the name, and resolving to it instead is an accepted residual risk with no pre-invocation check (see the agent's EXIT & DERAILMENT table) — directly (cairn agents can hold `Skill`, unlike maestro's subagents — no Mid-Run Skill Handoff relay needed); GitLab targets are reviewed self-implemented, mirroring `code-review`'s categories and effort levels. Re-invocable as a Fix-Verification Round (delta-diff since the last round, dated follow-up replies) without re-running the review. Also supports an explicit opt-in Thread Watch mode (driven by `/loop`, one pass per tick) with an Approval-to-Merge Gate that never auto-merges — every approval-state change gets a fresh confirmation, and a full-diff pass runs once more right before an actual merge. Writes one append-across-rounds `docs/.reviews/<host>-<owner-repo>-<number>.md`. Terminal, except a coding-chain-origin Thread Watch merge detection, which emits a mid-run marker for the main loop (never flips tracker Status itself — `task-orchestrator`/`project-manager` own that). Ported from maestro's GitLab-only `gitlab-mr-reviewer`, generalized to both hosts. Triggered by manual dispatch, `intent-analyzer` `review` category + judgment-call mapping, or `/cairn-watch-pr` for Thread Watch specifically. See `docs/.specs/2026-08-18-pr-reviewer-design.md` for the full design.
```

- [ ] **Step 1.5: Write the `review` category routing mapping in `CLAUDE.md`**

`intent-analyzer` already emits `review` as a category with no documented destination anywhere in `CLAUDE.md` — every other category that reaches a dispatch (`coding`) has a documented judgment-call mapping (see the "Coding-chain sequence" section); `review` currently has none. Insert a new subsection directly after the "Coding-chain sequence" section (before `/cairn-setup`'s paragraph):

```markdown
**`review` category routing (documented, not a change to `agents/intent-analyzer.md`):** a `ROUTING DECISION: review` classification whose normalized request targets a specific PR/MR (a URL, PR/MR number, or branch — as opposed to a local diff/branch review with no remote target, which stays the plain `code-review` skill invoked directly) dispatches to `pr-reviewer`. Same "Claude's own documented judgment call" pattern as the coding-chain's Direct/Chain routing above — `agents/intent-analyzer.md` itself is unmodified.
```

- [ ] **Step 2: Add the `/cairn-watch-pr` command paragraph to `CLAUDE.md`**

Insert directly after `/cairn-release`'s paragraph (or after `/cairn-doctor` if that plan hasn't landed yet):

```markdown
**`/cairn-watch-pr`** — starts `pr-reviewer` Thread Watch mode on a PR/MR or branch. See `pr-reviewer` above for the full flow.
```

- [ ] **Step 3: Add `pr-reviewer` and `/cairn-watch-pr` bullets to `README.md`**

Same content, condensed to README's existing one-line-per-bullet style, inserted after the `qa-auditor`/`release-manager` Agents bullet and the `/cairn-doctor`/`/cairn-release` Commands bullet respectively. Keep the code-review built-in-vs-marketplace-plugin clause even when condensing — it's the one fact a reader most needs before this agent posts anything on their behalf.

- [ ] **Step 4: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: document pr-reviewer and /cairn-watch-pr

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Version bump + final validation

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Bump version**

New feature (new agent + new command) — minor bump per this repo's own Versioning rule.

- [ ] **Step 2: Final validation**

Run: `claude plugin validate . --strict`
Expected: passes clean — `agents/pr-reviewer.md`, `commands/cairn-watch-pr.md`, and both doc updates all well-formed.

Run: `pytest tests/ -v -s`
Expected: `tests/test_usage_dashboard.py`'s deterministic subset stays green. `tests/test_intent_routing.py`'s eval suite stays at or above `MIN_PASS` — this work makes zero changes to `agents/intent-analyzer.md`.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version for pr-reviewer feature

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
