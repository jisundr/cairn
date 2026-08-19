---
description: "Open a realtime local usage dashboard for this project — token/cost totals, breakdowns by model/version/subagent/skill, a per-session table, and a task tracker tab. Requires /cairn-setup to have run first."
argument-hint: "[stop]"
---

## Your task

This runs cairn's own dashboard (`scripts/usage_dashboard.py`, stdlib Python, no dependencies) — it reads this project's session transcripts directly from `~/.claude/projects/`, so there's nothing to install or configure first. It does require the project to have run `/cairn-setup`, though — see step 1 below. Its Tracker tab reads `docs/.tasks/TRACKER.md` if present (empty state if not — no dependency on `project-manager` having run).

**If `$ARGUMENTS` is `stop`:**

1. Look for `.cairn/usage-dashboard.pid` in the project root.
   - Missing: report nothing is running, stop.
2. Read the PID from it. If that process is alive, kill it. Remove the lockfile either way.
3. Report what happened.

**Otherwise (start, the default):**

1. Check the project has run `/cairn-setup`: root `CLAUDE.md` must exist and contain a line that is *exactly* `<!-- cairn:start -->` (the whole line, nothing else on it — not just the text appearing somewhere, e.g. inside a code span in prose describing this mechanism).
   - Not set up: refuse to start. Tell the user to run `/cairn-setup` first — the dashboard's version-per-session data only makes sense for a project that's opted in, and starting it in an unset-up project would create `.cairn/` with no version history behind it. Stop here.
2. Check `.cairn/usage-dashboard.pid` — if it names a still-alive process, report the dashboard is already running (relay the URL you saved there) and stop. Don't launch a second instance.
3. Check `dashboard/dist/index.html` exists. If it doesn't:
   - Run `git submodule update --init dashboard` in the project root.
   - If that fails (offline, no recorded submodule commit, detached submodule config), stop and report the exact git error to the user — don't attempt to start the Python server, since it will just 500 on every page load.
4. Run `python3 "$CLAUDE_PLUGIN_ROOT/scripts/usage_dashboard.py" "$(pwd)"` **in the background** (detached — this command must return promptly, not block on the server). It prints its URL on the first line of stdout ("cairn usage dashboard at http://...") — capture that and the PID.
5. Create `.cairn/` in the project root if it doesn't exist, write the PID and URL to `.cairn/usage-dashboard.pid`.
6. Ensure `.cairn/.gitignore` exists containing a single `*` — this makes the whole directory self-ignoring, so nothing under `.cairn/` needs the project's own root `.gitignore` touched at all.
7. Open the URL in the user's browser.
8. Report the dashboard URL, and that `/cairn-dashboard stop` shuts it down.

`stop` never requires setup — it's cleanup, always allowed, even if `/cairn-teardown` ran since the dashboard was started.

Sessions that ran before this feature existed won't have a version-log entry — the dashboard shows `unknown` for those rather than guessing.
