---
description: "Open a realtime local usage dashboard for this project — token/cost totals and a per-session table with the cairn version each session ran on."
argument-hint: "[stop]"
---

## Your task

This runs cairn's own dashboard (`scripts/usage_dashboard.py`, stdlib Python, no dependencies) — it reads this project's session transcripts directly from `~/.claude/projects/`, so there's nothing to install or configure first.

**If `$ARGUMENTS` is `stop`:**

1. Look for `.cairn/usage-dashboard.pid` in the project root.
   - Missing: report nothing is running, stop.
2. Read the PID from it. If that process is alive, kill it. Remove the lockfile either way.
3. Report what happened.

**Otherwise (start, the default):**

1. Check `.cairn/usage-dashboard.pid` — if it names a still-alive process, report the dashboard is already running (relay the URL you saved there) and stop. Don't launch a second instance.
2. Run `python3 "$CLAUDE_PLUGIN_ROOT/scripts/usage_dashboard.py" "$(pwd)"` **in the background** (detached — this command must return promptly, not block on the server). It prints its URL on the first line of stdout ("cairn usage dashboard at http://...") — capture that and the PID.
3. Create `.cairn/` in the project root if it doesn't exist, write the PID and URL to `.cairn/usage-dashboard.pid`.
4. Ensure `.cairn/` is gitignored: if the project has a `.gitignore` and it doesn't already mention `.cairn/`, append it. If there's no `.gitignore` at all, leave it — don't create one just for this.
5. Open the URL in the user's browser.
6. Report the dashboard URL, and that `/cairn-usage stop` shuts it down.

Sessions that ran before this feature existed won't have a version-log entry — the dashboard shows `unknown` for those rather than guessing.
