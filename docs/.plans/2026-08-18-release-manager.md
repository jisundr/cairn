# Release Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port maestro's `release-manager` agent to cairn — proposes a semver bump + changelog from git history since the last tag, confirms once via `AskUserQuestion`, then commits/tags/pushes.

**Architecture:** A new terminal agent (`agents/release-manager.md`) triggered by a new `/cairn-release [rc]` command, plus natural-language recognition documented as a judgment-call mapping in `CLAUDE.md` (not a change to `agents/intent-analyzer.md` itself — same pattern the coding-chain's Direct/Chain routing already uses). The agent reads `.harness/workflow.md`/`standards.md` when present and lets project convention override its own defaults (Keep a Changelog format, `vX.Y.Z`/`vX.Y.Z-rcN` tags).

**Tech Stack:** Markdown agent-definition file (no code execution), `git`/`Bash` for the diff-since-last-tag, commit, tag, push mechanics.

**Spec:** `docs/.specs/2026-08-18-release-manager-design.md`

## Global Constraints

- Never modifies source code, never merges branches — changelog entry, `plugin.json` version bump, and the git tag are the sole write outputs.
- Dry-run then single confirm: the full plan (proposed version + reasoning + changelog draft + tag name) is shown in one `AskUserQuestion` before anything is written — never a two-gate design.
- `plugin.json`'s version, the changelog entry's version, and the tag name must all match before any push — validated as a hard stop, never overwritten if the tag already exists.
- `.harness/workflow.md` (and `.harness/standards.md` for commit-message format) override this agent's defaults when present — read them before drafting.
- Push targets `origin` only — no multi-remote push, matching `task-orchestrator`'s existing convention.
- `agents/intent-analyzer.md` itself is never modified by this work.

---

### Task 1: `agents/release-manager.md`

**Files:**
- Create: `agents/release-manager.md`

**Interfaces:**
- Consumes: spec sections "Flow", "Scope guard", "Trigger integration"; `agents/codebase-auditor.md` for structural convention (frontmatter shape, SYSTEM ROLE / WORKFLOW INTENT / HARD REQUIREMENTS / numbered process / PHASE HANDOFF / EXIT & DERAILMENT / START sections); `.claude-plugin/plugin.json`'s current `version` field as the thing this agent reads and bumps.
- Produces: the `release-manager` agent name, invoked by `commands/cairn-release.md` (Task 2) and referenced in `CLAUDE.md` (Task 3).

- [ ] **Step 1: Write frontmatter**

```yaml
---
name: release-manager
description: "Use this agent to cut a cairn release: it reads git log/diff since the last tag, proposes a semver bump (minor for new features, patch for fixes, per this repo's own Versioning convention) with reasoning, drafts a Keep a Changelog entry, and shows the full plan (version, reasoning, changelog, tag name) in one confirmation before writing anything. On accept: bumps .claude-plugin/plugin.json's version, prepends CHANGELOG.md (creating it fresh on the first-ever release), commits, creates an annotated tag (vX.Y.Z, or vX.Y.Z-rcN for a release candidate), and pushes the commit and tag to origin. Reads .harness/workflow.md and .harness/standards.md when present and lets a documented project convention override this agent's own defaults (changelog format, tag naming, commit-message format) — falls back to its defaults when .harness/ is silent on release process or absent entirely. Never modifies source code, never merges branches — the changelog entry, the plugin.json version bump, and the git tag are its only write outputs.

<example>
Context: User wants to cut a release after merging several features.
user: \"Cut a release\"
assistant: \"I'll use release-manager to propose the version bump and changelog from what's changed since the last tag, then confirm before tagging and pushing.\"
<commentary>
Release-cutting request. release-manager reads git history since the last tag, drafts the full plan, and gets one explicit confirmation before writing anything.
</commentary>
</example>

<example>
Context: User wants a release candidate instead of a final release.
user: \"Tag a release candidate for this\"
assistant: \"I'll use release-manager with the rc flag — same flow, but the tag gets an -rcN suffix instead of a final version.\"
<commentary>
RC tag requested explicitly. release-manager supports this via an optional argument, carried over from maestro's original agent.
</commentary>
</example>"
tools: Read, Glob, Bash, Write, Edit, AskUserQuestion, Skill
model: sonnet
color: green
---
```

- [ ] **Step 2: Write SYSTEM ROLE + WORKFLOW INTENT**

Model the shape on `agents/codebase-auditor.md` lines 9–25. Content requirements (spec "Flow", "Scope guard"):
- Scope is exclusively: `.claude-plugin/plugin.json`'s `version` field, `CHANGELOG.md`, and the git commit/tag/push for a release — never application/agent/skill source.
- Single mode, no Generate/Update split (unlike `harness-engineer`) — one run cuts one release.
- Terminal — no automatic handoff.
- Invoked via `/cairn-release [rc]` or natural-language recognition documented in `CLAUDE.md` (Task 3) — never auto-triggered by any other agent/workflow (explicitly out of scope per spec — no `meta-agent-sync`-style auto-invocation, since `meta-engineer`/`meta-auditor` have no cairn counterpart).

- [ ] **Step 3: Write HARD REQUIREMENTS**

Must include, near-verbatim from the spec:
- NEVER push before the user has explicitly confirmed the full plan (version + reasoning + changelog draft + tag name) via `AskUserQuestion` — draft and push are not separate gates, but nothing is written or pushed before that one confirmation.
- NEVER create a tag that already exists — validate via `git tag -l vX.Y.Z` (or the rc-suffixed form) as a hard stop before writing anything.
- ALWAYS validate `plugin.json`'s version, the changelog entry's version, and the tag name match each other before pushing.
- ALWAYS read `.harness/workflow.md` (and `.harness/standards.md` for commit-message format) if present, before drafting — a documented convention there overrides this agent's defaults (Keep a Changelog format, `vX.Y.Z` tag, `chore: release vX.Y.Z` commit message).
- NEVER modify source code, NEVER merge branches.
- Push targets `origin` only.
- Committing the changelog before tagging is non-negotiable ordering — never tag against an uncommitted changelog.

- [ ] **Step 4: Write the process — Detect, Harness Check, Gather Evidence, Propose, Execute**

Follow spec "Flow" section exactly:
1. **Detect last release point** — `git describe --tags --abbrev=0`; if no tags exist, diff from the repo's first commit (`git log --reverse --format=%H | head -1`) instead.
2. **Harness check** — `Read` `.harness/workflow.md` and `.harness/standards.md` if they exist (`Glob` first); note any release-process or commit-message convention found, to apply in later steps.
3. **Gather evidence** — `git log --format='%s' <last-tag>..HEAD` and `git diff --stat <last-tag>..HEAD`; bucket by conventional-commit prefix (`feat`/`fix`/`chore`/...) where present, otherwise read diff content to classify.
4. **Propose** — draft version (minor if any `feat`/user-visible change, patch if only `fix`/no-user-visible-effect changes, per this repo's own `CLAUDE.md` Versioning rule — quote it), draft Keep a Changelog entry (`### Added`/`### Changed`/`### Fixed` subsections, only the ones with content), draft tag name (`vX.Y.Z` or with `-rcN` if the rc argument was passed). Present all three via one `AskUserQuestion` — accept / edit / abort.
5. **Execute (only on accept)** — validate tag doesn't already exist; write `version` in `.claude-plugin/plugin.json` (`Read` then `Edit`/`Write`); create `CHANGELOG.md` with a standard Keep a Changelog header if it doesn't exist yet, then prepend the entry; validate `plugin.json` version == changelog entry version == tag name; `git add`, `git commit -m "chore: release vX.Y.Z"` (or `.harness/standards.md`'s format if it overrides); `git tag -a vX.Y.Z -m "<summary from changelog entry>"`; `git push origin <branch>` and `git push origin <tag>`.

- [ ] **Step 5: Write PHASE HANDOFF + EXIT & DERAILMENT HANDLING + START**

Model on `codebase-auditor.md`'s equivalent sections. Terminal — no handoff. Completion block reports: version released, tag name, changelog entry, pushed commit/tag SHAs.

EXIT & DERAILMENT table must include at least:
| Trigger | Response |
|---|---|
| Proposed tag already exists | Stop before writing anything; report the collision and ask for a different version or confirm this should be an rc bump instead. |
| No git remote named `origin` | Stop before the Execute step; report that push has no target. |
| Working tree has uncommitted changes unrelated to the release (`git status` not clean before Step 5) | Report the dirty state and ask whether to proceed (release commit only) or the user wants to handle those changes first. |
| User declines the proposed plan | "No release cut. Nothing was written." |
| An error that doesn't match any other row in this table (looks like a cairn-side defect, not this codebase's) | Attempt `Skill(skill: "feedback-context")`; if it succeeds, surface its one-line suggestion alongside the normal error report. Never blocks — falls through to the normal error report either way. |

- [ ] **Step 6: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 7: Headless smoke test**

```bash
mkdir -p /tmp/cairn-release-test && cd /tmp/cairn-release-test && git init -q
git commit --allow-empty -q -m "chore: initial commit"
mkdir -p .claude-plugin && printf '{"name":"test-plugin","version":"0.1.0"}' > .claude-plugin/plugin.json
git add .claude-plugin && git commit -q -m "feat: add plugin manifest"
claude -p "/cairn:cairn-release" --plugin-dir /Users/jaysondelosreyes/cairn --permission-mode bypassPermissions --output-format text
```
Expected: agent detects no tags exist yet, diffs from the first commit, proposes a version bump (likely `0.2.0` given the `feat:` commit) with a `CHANGELOG.md` draft and tag name, and asks for confirmation. Since this is a non-interactive headless run, the `AskUserQuestion` will surface as a stop point — inspect the reported plan text to confirm it's well-formed (version, reasoning, changelog entry, tag name all present and consistent) rather than expecting it to complete the push unattended.

Note: this exercises the `/cairn-release` command path only (matching `CLAUDE.md`'s own documented end-to-end command-testing shape), not the natural-language "cut a release" recognition — that mapping lives in *this* repo's `CLAUDE.md`, which a scratch dir doesn't have. The natural-language trigger is verified manually in this repo instead; this is the plan's only automated smoke test, so `qa-engineer` should treat it as covering Detect→Harness Check→Gather Evidence→Propose only, not Execute (tag-collision, version-match validation, actual tag/push, the `rc` path, `.harness/` override) — consider additional scratch-repo smoke runs at red phase for Execute-step coverage.

- [ ] **Step 8: Commit**

```bash
git add agents/release-manager.md
git commit -m "Add release-manager agent

Ports maestro's release-manager: proposes a semver bump + changelog
from git history since the last tag, confirms once, then commits,
tags, and pushes. Reads .harness/workflow.md when present.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `commands/cairn-release.md`

**Files:**
- Create: `commands/cairn-release.md`

**Interfaces:**
- Consumes: `commands/cairn-doctor.md` for structural convention (frontmatter `description`, `## Your task` numbered steps); `agents/release-manager.md` (Task 1) as the agent it dispatches.
- Produces: the `/cairn-release` command, referenced in `CLAUDE.md` (Task 3) and `README.md` (Task 4).

- [ ] **Step 1: Write the command file**

```markdown
---
description: "Cut a cairn release: propose a semver bump + changelog from git history since the last tag, confirm once, then commit, tag, and push. Pass 'rc' as an argument to cut a release candidate instead of a final release."
argument-hint: "[rc]"
---

## Your task

Dispatch the `release-manager` agent with the optional argument (`rc` if passed, otherwise none) as opening context. `release-manager` handles the full flow itself — detecting the last tag, reading `.harness/workflow.md` if present, proposing the bump and changelog, confirming, and executing the commit/tag/push. Report its completion summary back to the user.
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 3: Commit**

```bash
git add commands/cairn-release.md
git commit -m "Add /cairn-release command

Dispatches release-manager with an optional rc argument.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `CLAUDE.md` updates

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: `agents/release-manager.md` (Task 1), `commands/cairn-release.md` (Task 2); the existing paragraph style for each ported agent (see `codebase-auditor`/`competitor-analyst` paragraphs) and existing command paragraph style (see `/cairn-doctor`).

- [ ] **Step 1: Add the `release-manager` agent paragraph**

Insert a new paragraph directly after the `qa-auditor` paragraph (before "**End-to-end sequence...**"), matching the existing ported-agent paragraph style (see `codebase-auditor`'s "ported from maestro's..." framing):

```markdown
**`release-manager` (agents/)** — proposes a semver bump (minor for new features, patch for fixes, per this file's own Versioning rule below) and a Keep a Changelog entry from git history since the last tag, shows the full plan in one `AskUserQuestion` confirmation, then on accept bumps `.claude-plugin/plugin.json`, writes `CHANGELOG.md`, commits, creates an annotated tag (`vX.Y.Z`, or `vX.Y.Z-rcN` for a release candidate), and pushes to `origin`. Reads `.harness/workflow.md`/`standards.md` when present and lets a documented project convention override its own defaults. Never modifies source, never merges branches — the changelog entry, version bump, and tag are its only write outputs. Terminal, no skill loaded — ported from maestro's `release-manager`, adapted from that framework's fully-automatic bump ownership to a propose-then-confirm model matching this file's existing manual Versioning convention. Triggered by `/cairn-release [rc]` or natural-language recognition ("cut a release", "tag this", "release candidate") — `agents/intent-analyzer.md` itself is unmodified, same judgment-call-in-CLAUDE.md pattern the coding-chain's Direct/Chain routing already uses. See `docs/.specs/2026-08-18-release-manager-design.md` for the full design.
```

- [ ] **Step 2: Add the `/cairn-release` command paragraph**

Insert directly after the `/cairn-doctor` paragraph, matching that paragraph's style:

```markdown
**`/cairn-release [rc]`** — dispatches `release-manager` to cut a release (or, with the `rc` argument, a release candidate). See `release-manager` above for the full flow.
```

- [ ] **Step 2.5: Reconcile `## Versioning` with `release-manager`'s bump ownership**

`CLAUDE.md`'s existing `## Versioning` section instructs a manual per-change bump ("Bump `version`... whenever a change is something a consuming project needs to see reflected") — every plan in this repo (including this one's own Task 5) follows that rule literally. `release-manager` computes and writes that same field independently at release time, from git history since the last tag — two owners, two timings, with no stated reconciliation. Append one sentence to the end of `## Versioning`:

```markdown
`release-manager` (see above) does not replace this rule — it reads whatever `version` is currently committed (the accumulated result of every manual per-change bump since the last tag) and proposes the release tag from that, never overriding a bump you've already made by hand.
```

- [ ] **Step 3: Validate**

Run: `claude plugin validate . --strict`
Expected: passes.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document release-manager and /cairn-release in CLAUDE.md

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `README.md` updates

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: existing Agents/Commands bullet-list style (see `codebase-auditor`/`/cairn-doctor` bullets already in `README.md`).

- [ ] **Step 1: Add the `release-manager` bullet**

Insert directly after the `qa-auditor` bullet in the Agents section:

```markdown
- `release-manager` — proposes a semver bump and changelog entry from git history since the last tag, confirms the full plan with you once, then commits, tags, and pushes to `origin`. Reads `.harness/workflow.md`/`standards.md` when present. Never touches source code.
```

- [ ] **Step 2: Add the `/cairn-release` bullet**

Insert directly after the `/cairn-doctor` bullet in the Commands section:

```markdown
- `/cairn-release [rc]` — cut a release, or with `rc`, a release candidate.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add release-manager and /cairn-release to README

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Version bump + final validation

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Bump version**

This is a new feature (new agent + new command) — minor bump per this repo's own Versioning rule. Before bumping, check `git show main:.claude-plugin/plugin.json` for the current version on `main` (not just the worktree's own copy) — two sibling chain runs (`goal-file-plan-writing`, `pr-reviewer`) are also live against this same repo and independently bump the same field; whichever of the three merges first sets the real baseline, the other two will need a rebase-and-recompute at merge time (`task-orchestrator` Publish Mode's normal conflict-resolution territory, not something to pre-solve here). Bump the minor component from whichever value is actually current when this step runs, reset patch to 0.

- [ ] **Step 2: Final validation**

Run: `claude plugin validate . --strict`
Expected: passes clean — `agents/release-manager.md`, `commands/cairn-release.md`, and both doc updates all well-formed.

Run: `pytest tests/ -v -s`
Expected: `tests/test_usage_dashboard.py`'s deterministic subset stays green (unaffected by this work). `tests/test_intent_routing.py`'s eval suite stays at or above `MIN_PASS` — this work makes zero changes to `agents/intent-analyzer.md`, so no regression is expected; a flip on a single case is normal model variance, not a blocker.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version for release-manager feature

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
