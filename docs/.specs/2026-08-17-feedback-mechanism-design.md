# Design: Sanitized feedback-to-issue mechanism

## Summary

Adds a way for a consuming project (any project cairn is installed into) to report feedback/bugs about cairn itself back to `jisundr/cairn`'s issue board, without leaking sensitive information from that consuming project. Two entry points — an explicit `/cairn-feedback` command, and a soft-optional agent-initiated suggestion (`skills/feedback-context/SKILL.md`, wired into all 16 agents plus `cairn-doctor`) — both funnel into the same drafting/review/push flow: Claude drafts a sanitized local `.md` file, stops and shows it for review, and only on the user's explicit confirmation offers to push it via `gh` — never automatically, and re-confirmed every single time (posting to a third party's public issue tracker on the user's behalf is a materially higher-trust action than the consuming repo's own PR/MR automation, which cairn already does elsewhere with standing confirmation-per-use).

## Scope decisions

| Decision | Chosen | Why |
|---|---|---|
| Trigger | Explicit `/cairn-feedback` command + agent-initiated suggestion | Broader coverage than command-only — a real cairn bug is often surfaced mid-task by whatever agent hit it, not remembered later for a manual command. |
| Suggestion scope | `cairn-doctor` + all 16 agents, narrow trigger | Matches "any agent on unexpected failure." Scoped narrowly (see Trigger definition below) to avoid over-triggering on normal task friction or the consuming codebase's own bugs. |
| Mechanism for the 16-agent rollout | Shared skill (`feedback-context`), one row added to each agent's `EXIT & DERAILMENT HANDLING` table | Same "one soft-optional addition per agent, no duplicated logic" shape as the already-shipped `graphify-context` integration (8 agents) — direct precedent in this repo. |
| Sanitization | Disciplined drafting + mandatory human review, no automated scrub pass | Automated secret-detection is unreliable (false negatives are dangerous in a "this leaves the machine" context) — `codebase-auditor`'s own secret-grep is already documented as best-effort, not a guarantee. A drafting discipline (only ever include a fixed, narrow field list) plus a hard stop for human review is more trustworthy than a regex pass that could create false confidence. |
| Local file location | `.cairn/feedback/YYYYMMDD-HHmmss-<slug>.md` | `.cairn/` is already the plugin's per-project state directory (self-ignored, `/cairn-setup`-gated) — feedback drafts are cairn-internal working files, not a long-lived process-doc convention like `docs/.specs/`/`docs/.plans/`. Timestamp format matches `codebase-auditor`'s existing `YYYYMMDD-HHmmss-{project-name}.md` convention. |
| `.cairn/` gating | Require `/cairn-setup`, same as `/cairn-dashboard` | Consistent with `.cairn/`'s existing documented invariant (only exists in projects that ran setup) — one invariant, no special-cased exception. |
| Push mechanism | Offer `gh issue create --repo jisundr/cairn ...`, confirmed every time; fall back to copy-paste if `gh` is unavailable | Never automatic, never standing permission — matches the backlog note's explicit "user manually pushes." |

## Trigger definition (the narrow heuristic `feedback-context` documents)

**Fires:** an unhandled exception/crash in cairn's own tooling — a Python traceback from `scripts/usage_dashboard.py`, a malformed template render, a `Skill()` invocation failing in a way the calling agent's own `EXIT & DERAILMENT HANDLING` table doesn't already name.

**Never fires:** the consuming codebase's own bugs (that's what the agent is there to work on), or any state the agent's `EXIT & DERAILMENT HANDLING` table already documents (a `TERMINATED`, a `HANDOFF NEEDED`, a declined `AskUserQuestion` — these are cairn working as designed, not a defect).

## Components

### `commands/cairn-feedback.md` (new)

Explicit entry point, same natural-language command-file convention as `cairn-doctor.md`/`cairn-dashboard.md`.

1. Gate: check for the `<!-- cairn:start -->` marker in the project's root `CLAUDE.md` (identical check to `/cairn-dashboard`'s gate). Absent → refuse, point at `/cairn-setup`.
2. Gather: if the invocation didn't already describe the issue, ask what happened. Collect: cairn version (from `.claude-plugin/plugin.json` or `.cairn/version-log.jsonl`'s latest entry), which agent/skill was involved if known, the error/unexpected-behavior text if any.
3. Draft: write `.cairn/feedback/YYYYMMDD-HHmmss-<slug>.md` (slug: short kebab-case, ad hoc from the issue description) containing only the fixed field list below. Never include file contents, absolute paths, env var values, or any other repo-specific identifier.
4. Stop: show the draft's full content to the user, ask them to review/redact before anything about pushing is discussed.
5. On explicit confirmation the draft is ready: if `gh auth status` succeeds, offer `gh issue create --repo jisundr/cairn --title <title> --body-file <path>` — ask before running it, every time. If `gh` is unavailable/unauthenticated, or the user declines, give the copy-paste fallback: point at `https://github.com/jisundr/cairn/issues/new` and the local file path.

**Draft field list (fixed, exhaustive — nothing outside this list gets drafted):**
- cairn version
- Which agent/command/skill was involved (if known)
- What happened (the error text or unexpected behavior, as reported)
- A generic repro description (steps in terms of cairn's own flow — "ran `/cairn-dashboard`", "task-orchestrator Plan Mode step 7" — never the consuming project's actual file paths, code, or business logic)

### `skills/feedback-context/SKILL.md` (new)

Not a user-invoked skill — loaded by an agent at the point it would otherwise just report an error, same shape as `graphify-context`. Documents:
1. The trigger definition above.
2. The same draft field list and drafting discipline as `/cairn-feedback` (this skill and the command share the same discipline — the command is the manual path in, this skill is the agent-initiated path in, both end up writing the same shape of file).
3. The suggestion convention: one line, plain text (not a hard `AskUserQuestion` gate — this is a suggestion an agent surfaces alongside its normal error report, e.g. "This looks like it might be a cairn bug, not something in this project — want to file feedback? I can draft a local sanitized file for you to review first."). Never auto-drafts unasked.
4. On yes: follow the same gate → gather → draft → stop → offer-push flow as `/cairn-feedback` Steps 1–5.

### `agents/*.md` (16 files) — one new `EXIT & DERAILMENT HANDLING` row each

Each agent's existing `EXIT & DERAILMENT HANDLING` table (every agent in `agents/` already has one, per the codebase's existing convention) gains one row:

> An error that doesn't match any other row in this table (looks like a cairn-side defect, not this codebase's) → attempt `Skill(skill: "feedback-context")`; if it succeeds, surface its one-line suggestion alongside the normal error report. Never blocks — falls through to the normal error report either way.

### `commands/cairn-doctor.md` — one new step

New Step (after the existing 7, renumbering the Summary step): if any check in Steps 1–7 hits something that doesn't fit its own documented pass/fail/missing states (an actual crash mid-check, not one of the states already listed), attempt `Skill(skill: "feedback-context")` and surface its suggestion. Included in the final Summary report.

## Data flow

No new persistent state beyond the `.cairn/feedback/*.md` files themselves. No `.jsonl` log, no `TRACKER.md` entry, no correlation to anything else in `.cairn/`. Each file is a one-shot artifact: written, reviewed, either pushed (and the user may delete it afterward, cairn never auto-deletes it) or left as a local note.

## Error handling

- `/cairn-setup` not run → refuse, point at `/cairn-setup`. Same posture as `/cairn-dashboard`.
- `gh` missing or `gh auth status` fails at push time → fall back to the copy-paste instruction; never blocks the draft itself, which already exists on disk regardless.
- `Skill(skill: "feedback-context")` fails to load from within an agent (shouldn't happen, ships with the plugin, but same discipline as every other soft-optional skill attempt in cairn) → the calling agent falls through to its normal error report exactly as if the skill didn't exist. Never `ABORT`s the agent's own run over a failed feedback-suggestion attempt.

## Testing

No unit-testable surface — `commands/cairn-feedback.md` and `skills/feedback-context/SKILL.md` are natural-language instructions, not code (same category as every other `commands/*.md` file; `tests/test_usage_dashboard.py`'s scope is untouched). Verified per `CLAUDE.md`'s existing "Testing a command end-to-end" convention: headless runs against a scratch directory (`claude -p "/cairn:cairn-feedback ..." --plugin-dir /path/to/cairn --permission-mode bypassPermissions --output-format text`), confirming: the `/cairn-setup` gate refuses correctly when absent, a drafted file never contains anything outside the fixed field list, the `gh` offer path and the copy-paste fallback both produce correct output, and at least 2–3 of the 16 agents' new `EXIT & DERAILMENT` rows actually fire the suggestion on a simulated unmatched error (spot-check, not exhaustive across all 16 — the row's text is identical across every agent, so this is a formatting/wiring check, not a design one).

## Versioning

New command, new skill, 16 agent files + `cairn-doctor.md` touched — bump `.claude-plugin/plugin.json` per `CLAUDE.md`'s Versioning section (minor, new feature) once implemented.
