---
description: "Check cairn's health in this project and offer to upgrade the plugin if a newer version is available."
---

## Your task

Run these checks in order and report a summary at the end. None of them are gates — report what you find, fix what's safe to fix automatically (noted per-step below), never block on anything.

1. **Plugin version.** Run `claude plugin update cairn@cairn-plugins` and relay its result.
   - "already at the latest version" → report up to date.
   - Fetched a newer version → report that, and note a new Claude Code session is required before it takes effect (plugins load at session start, not mid-session).
   - Command fails (e.g. `claude`/marketplace not reachable) → relay the error plainly, don't treat it as fatal to the rest of the checks.

2. **CLAUDE.md entrypoint wiring.** If the project has a root `CLAUDE.md`, check for the `<!-- cairn:start -->` marker.
   - Present → report wired.
   - Absent → report not wired. This is informational, not a problem — mention `/cairn-setup` if they want it, don't suggest anything's broken.
   - No `CLAUDE.md` at all → report not applicable.

3. **`.cairn/` gitignored.** Only relevant if `.cairn/` exists in the project (created by `/cairn-usage` or `/cairn-setup`'s hook activity).
   - If it exists and the project has a `.gitignore` that doesn't mention `.cairn/`: append it, report that you did.
   - If it exists and there's no `.gitignore` at all: leave it, don't create one just for this, report that it's untracked-but-not-ignored so they're aware.
   - If `.cairn/` doesn't exist: nothing to do here.

4. **Stale dashboard lockfile.** If `.cairn/usage-dashboard.pid` exists, check whether the PID in it is still alive.
   - Alive → report the dashboard is running, with its URL.
   - Dead → remove the stale lockfile, report that you cleaned it up (otherwise `/cairn-usage` would think one's already running when it isn't).

5. **Summary.** One short report covering all four checks and what (if anything) was changed.
