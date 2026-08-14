---
description: "Wire cairn's intent-analyzer as this project's mandatory entrypoint by adding a marked section to the project's root CLAUDE.md."
---

## Your task

Wire cairn into this project's root `CLAUDE.md` as the mandatory entrypoint, matching how maestro forces itself as the entrypoint for consuming projects.

1. **Check for `CLAUDE.md` at the project root.**
   - If it does **not** exist: tell the user to run `/init` first (Claude Code's built-in command — documents the codebase into a `CLAUDE.md`), then re-run `/cairn-setup`. Stop here; do not proceed further in this case.

2. **Check whether cairn is already wired.** Read `CLAUDE.md` and look for a `<!-- cairn:start -->` marker.
   - If found: report that cairn is already wired and stop. Do not add a second copy (idempotent).

3. **Append the following block to the end of `CLAUDE.md`** (preceded by a blank line if the file doesn't already end in one), verbatim:

   ```
   <!-- cairn:start -->
   ## cairn (mandatory entrypoint)

   If the cairn plugin is installed and its `intent-analyzer` subagent is available, EVERY new user request MUST be routed through `intent-analyzer` first to classify and normalize it before any other action — no exceptions.

   If the cairn plugin is not installed, ask the user for approval to install it:
     /plugin marketplace add jisundr/cairn
     /plugin install cairn@cairn-plugins
   If approved, install it, tell the user a new Claude Code session is required
   before intent-analyzer becomes available, then proceed with this current
   request normally (without cairn). If declined, also proceed normally.
   <!-- cairn:end -->
   ```

4. **Report what changed** — confirm the section was added and remind the user that a new Claude Code session is needed before the entrypoint rule takes effect (subagents load at session start, not mid-session).

To undo this, use `/cairn-teardown`.
