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
