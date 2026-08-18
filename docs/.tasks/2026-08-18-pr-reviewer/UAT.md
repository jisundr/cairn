# UAT Checklist: pr-reviewer

Scope of this PR: **Task 1 only** — Input Resolution + Initial Review mode. Fix-Verification Round, Thread Watch, Approval-to-Merge Gate, and the `/cairn-watch-pr` command are **not implemented** in this PR; they're tracked as follow-up work in `docs/.plans/2026-08-18-pr-reviewer.md` (Tasks 2-6, still present in the plan for that follow-up).

## Setup

1. Install/load the plugin from this branch (e.g. `claude --plugin-dir /path/to/cairn/.worktrees/feature-pr-reviewer`, or a real install once merged).
2. Have `gh` authenticated (`gh auth status`) against a GitHub account with access to a real PR to review. GitLab (`glab`) is optional for this pass — the GitHub path is the easiest to verify end-to-end since finding-generation delegates to the built-in `code-review` skill.

## Checklist

- [ ] **Dispatch**: Ask "review PR #<n> on <owner/repo>" (or paste a full GitHub PR URL) and confirm `pr-reviewer` is the agent that responds — not a generic fallback. Its own voice should be visible (mode-detection language, not boilerplate).
- [ ] **Host detection**: Confirm it correctly identifies `github.com` and resolves to the `gh` CLI path (no attempt to use `glab` against a GitHub target).
- [ ] **Auth check**: Point it at a target while deliberately logged out of `gh` (`gh auth logout`) and confirm it stops and reports rather than failing opaquely.
- [ ] **No checkout**: After a run, confirm the working tree's current branch is unchanged (`git branch --show-current`) — the target's source branch must never be checked out, only fetched.
- [ ] **Finding generation (GitHub)**: Confirm it delegates to `Skill(skill: "code-review", ...)` without `--comment` — i.e. no comment appears on the real PR from this call alone (check `gh pr view <n> --json comments` before/after).
- [ ] **Draft save**: Confirm a file appears at `docs/.reviews/<host>-<owner-repo>-<number>.md` immediately once the first draft is produced, before you're asked anything — not only after you approve it.
- [ ] **Draft/post separation**: Confirm you are asked to review/iterate on the draft first, and that a *separate* explicit confirmation is required before anything posts as a comment. Declining to post should leave the draft file in place with nothing posted.
- [ ] **Posting** (optional, only if you want to actually post): Confirm that after explicit confirmation, findings post as plain body-text comments (not diff-anchored) and the reported count/links match what was posted.
- [ ] **0-findings case**: If a clean target is reviewed, confirm the draft still gets saved with an explicit "no findings" note — not skipped.
- [ ] **GitLab path (optional)**: Point it at a GitLab MR URL and confirm host detection resolves to `glab`, and that findings are generated directly (no `code-review` skill call) at a comparable depth/category set.
- [ ] **`claude plugin validate . --strict`** passes on this branch.
- [ ] **Smoke tests**: `bash tests/smoke/run_pr_reviewer.sh "$(pwd)"` passes 2/2 (sandbox disabled — nested live `claude -p` calls; see STATE.md for the exact invocation note).

## Known gaps (expected, not bugs — out of scope for this PR)

- No Fix-Verification Round: re-running against an already-reviewed target will currently just run Initial Review again rather than detecting prior findings.
- No Thread Watch / Approval-to-Merge Gate / `/cairn-watch-pr` command yet.
- No `CLAUDE.md`/`README.md` documentation entry or `intent-analyzer` `review`-category routing mapping yet (Task 6 of the plan).
- Bare `PR #1` / `MR !1529` number-only input parsing is documented in the agent file but not currently exercised by the smoke test suite (both final tests use explicit-agent-naming + full URLs, per a TDD fix-cycle finding that bare-number prompts dispatch unreliably in headless smoke tests — see STATE.md Key info).
