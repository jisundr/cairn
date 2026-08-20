---
description: "Open a realtime local usage dashboard for this project — token/cost totals, breakdowns by model/version/subagent/skill, a per-session table, a task tracker tab, and a swarms tab for monitoring Unattended coding-chain runs. Requires /cairn-setup to have run first."
argument-hint: "[stop]"
---

## Your task

This runs cairn's own dashboard (`scripts/usage_dashboard.py`, stdlib Python, no dependencies, serving the `dashboard/` submodule's committed React build) — it reads this project's session transcripts directly from `~/.claude/projects/`, so there's nothing to install or configure first. It does require the project to have run `/cairn-setup`, though — see step 1 below. Its Usage/Tracker/Swarms tabs read `/api/usage`, `/api/tracker` (`docs/.tasks/TRACKER.md`, empty state if not present — no dependency on `project-manager` having run), and `/api/swarms` (`Mode: Unattended` tasks under `docs/.tasks/*/STATE.md`, empty state if none).

**If `$ARGUMENTS` is `stop`:**

1. Look for `.cairn/usage-dashboard.pid` in the project root.
   - Missing: report nothing is running, stop.
2. Read the PID from it. If that process is alive, kill it. Remove the lockfile either way.
3. Report what happened.

**Otherwise (start, the default):**

1. Check the project has run `/cairn-setup`: root `CLAUDE.md` must exist and contain a line that is *exactly* `<!-- cairn:start -->` (the whole line, nothing else on it — not just the text appearing somewhere, e.g. inside a code span in prose describing this mechanism).
   - Not set up: refuse to start. Tell the user to run `/cairn-setup` first — the dashboard's version-per-session data only makes sense for a project that's opted in, and starting it in an unset-up project would create `.cairn/` with no version history behind it. Stop here.
2. Check `.cairn/usage-dashboard.pid` — if it names a still-alive process, report the dashboard is already running (relay the URL you saved there) and stop. Don't launch a second instance.
3. Check `"$CLAUDE_PLUGIN_ROOT/dashboard/dist/index.html"` exists — this is the plugin's own copy of the dashboard build, not the current project's; the consuming project never has a `dashboard/` of its own, so don't check for it there. If it's missing:
   - Check whether `"$CLAUDE_PLUGIN_ROOT/.git"` exists.
     - It exists: `$CLAUDE_PLUGIN_ROOT` is a real git checkout (e.g. local dev via `--plugin-dir`, or a case where Claude Code runs the plugin directly out of its marketplace clone). Run `git -C "$CLAUDE_PLUGIN_ROOT" submodule update --init dashboard`, then recheck `dashboard/dist/index.html`. If it still fails or is still missing, stop and report the exact git error to the user — don't attempt to start the Python server, since it will just 500 on every page load.
     - It doesn't exist: `$CLAUDE_PLUGIN_ROOT` is Claude Code's flat installed-plugin cache — a plain file copy with no git history of its own, so `git submodule update` can never succeed there no matter what is tried. Don't attempt it. Instead, stop and tell the user: the `dashboard` submodule needs to be initialized once in the plugin's separate **marketplace clone** (the git checkout `/plugin marketplace add` made), not in this installed copy. Look up that clone's path from `~/.claude/plugins/known_marketplaces.json` (the `installLocation` for the marketplace cairn was installed from — commonly `~/.claude/plugins/marketplaces/<marketplace-name>`); if that file isn't readable, name the common path as a best guess instead. Give the user this one-time fix:
       ```
       cd <marketplace clone path>
       git submodule update --init dashboard
       ```
       then run `/plugin update cairn` (or reinstall the plugin) so the installed copy picks up the now-populated `dashboard/dist/`, then retry `/cairn-dashboard`.
4. Run `python3 "$CLAUDE_PLUGIN_ROOT/scripts/usage_dashboard.py" "$(pwd)"` **in the background** (detached — this command must return promptly, not block on the server). It prints its URL on the first line of stdout ("cairn usage dashboard at http://...") — capture that and the PID.
5. Create `.cairn/` in the project root if it doesn't exist, write the PID and URL to `.cairn/usage-dashboard.pid`.
6. Ensure `.cairn/.gitignore` exists containing a single `*` — this makes the whole directory self-ignoring, so nothing under `.cairn/` needs the project's own root `.gitignore` touched at all.
7. Open the URL in the user's browser.
8. Report the dashboard URL, and that `/cairn-dashboard stop` shuts it down.

`stop` never requires setup — it's cleanup, always allowed, even if `/cairn-teardown` ran since the dashboard was started.

Sessions that ran before this feature existed won't have a version-log entry — the dashboard shows `unknown` for those rather than guessing.
