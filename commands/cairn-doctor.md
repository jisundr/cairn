---
description: "Check cairn's health in this project and offer to upgrade the plugin if a newer version is available."
---

## Your task

Run these checks in order and report a summary at the end. None of them are gates — report what you find, fix what's safe to fix automatically (noted per-step below), never block on anything.

1. **Plugin version.** Run `claude plugin update cairn@cairn-plugins` and relay its result.
   - "already at the latest version" → report up to date.
   - Fetched a newer version → report that, and note a new Claude Code session is required before it takes effect (plugins load at session start, not mid-session).
   - Command fails (e.g. `claude`/marketplace not reachable) → relay the error plainly, don't treat it as fatal to the rest of the checks.

2. **`superpowers` plugin.** `idea-explorer` hard-requires it (loads `superpowers:brainstorming` directly, no fallback). Check via `claude plugin list --json`: is `superpowers@claude-plugins-official` present, `enabled: true`, and scoped to this project (`scope == "user"` or `projectPath` matches cwd)?
   - Installed and enabled → report `idea-explorer` fully functional.
   - Not installed/enabled → report `idea-explorer` will abort if dispatched. Suggest the install commands as text — don't run them; installing a plugin on the user's behalf needs their explicit action, not a doctor auto-fix.

3. **Taste Skill / Anthropic Frontend Design plugins.** `product-designer`'s Design Quality Pass and `software-engineer`'s Frontend Polish Pass both use these when present — neither is required, this check is purely informational. Check via `claude plugin list --json`: is `taste-skill@taste-skill` present/`enabled: true`? Is `frontend-design@claude-code-plugins` present/`enabled: true`?
   - Both installed and enabled → report both passes have full access to them.
   - Either missing → report which one, note which pass(es) lose that input (never an abort — both passes are soft-optional), and suggest the real install commands as text, never run them:
     - Taste Skill: `/plugin marketplace add Leonxlnx/taste-skill` then `/plugin install taste-skill@taste-skill`
     - Anthropic Frontend Design: `/plugin marketplace add anthropics/claude-code` then `/plugin install frontend-design@claude-code-plugins`

4. **Emil Kowalski skills.** `software-engineer`'s Frontend Polish Pass uses these when vendored — not required. Check via `Glob(.claude/skills/emil-design-eng/SKILL.md)` in the current project.
   - Present → report the Frontend Polish Pass has access to it.
   - Absent → report it's not vendored here and suggest `npx skills@latest add emilkowalski/skills` as text, never run it.

5. **CLAUDE.md entrypoint wiring.** If the project has a root `CLAUDE.md`, check for a line that is *exactly* `<!-- cairn:start -->` (the whole line, nothing else on it — not just the text appearing somewhere, e.g. inside a code span in prose describing this mechanism).
   - Present → report wired.
   - Absent → report not wired. This is informational, not a problem — mention `/cairn-setup` if they want it, don't suggest anything's broken.
   - No `CLAUDE.md` at all → report not applicable.

6. **`.cairn/` self-ignoring.** Only relevant if `.cairn/` exists in the project (created by `/cairn-dashboard` or the `log-version.sh` hook).
   - `.cairn/.gitignore` exists and contains `*` → report it's correctly self-ignored.
   - Missing or wrong content → write a `.cairn/.gitignore` containing a single `*`, report that you fixed it. This never touches the project's own root `.gitignore` — `.cairn/` ignores itself.
   - `.cairn/` doesn't exist: nothing to do here.

7. **Stale dashboard lockfile.** If `.cairn/usage-dashboard.pid` exists, check whether the PID in it is still alive.
   - Alive → report the dashboard is running, with its URL.
   - Dead → remove the stale lockfile, report that you cleaned it up (otherwise `/cairn-dashboard` would think one's already running when it isn't).

8. **Unexpected check failure.** If any of Steps 1–7 hit something that doesn't fit its own documented pass/fail/missing states above (an actual crash mid-check, not one of the states already listed) — attempt `Skill(skill: "feedback-context")` and surface its suggestion. Never blocks the rest of the checks; include in the final summary.

9. **Summary.** One short report covering all eight checks and what (if anything) was changed.
