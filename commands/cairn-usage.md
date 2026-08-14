---
description: "Open a realtime local usage dashboard for this project (wraps `codeburn web` via npx). Requires Node.js/npx on PATH."
argument-hint: "[stop]"
---

## Your task

This command is a thin wrapper around the third-party `codeburn` CLI (`npx codeburn web`) — it does not reimplement a dashboard. It needs `npx` (Node.js) on `PATH`; nothing else in cairn depends on Node, so treat a missing `npx` as an expected possibility, not an error to fix.

**If `$ARGUMENTS` is `stop`:**

1. Look for `.cairn/usage-dashboard.pid` in the project root.
   - Missing: report nothing is running, stop.
2. Read the PID from it. If that process is alive, kill it. Remove the lockfile either way.
3. Report what happened.

**Otherwise (start, the default):**

1. Check `npx` is on `PATH` (`command -v npx`). Missing: tell the user Node.js is required for this command specifically (cairn itself has no Node dependency), then stop.
2. Check `.cairn/usage-dashboard.pid` — if it names a still-alive process, report the dashboard is already running (relay the URL from the lockfile if you saved one) and stop. Don't launch a second instance.
3. Derive the project filter from the current directory's basename (e.g. `cairn` for `/Users/you/cairn`).
4. Run `npx codeburn web --project "<basename>"` **in the background** (detached — this command must return promptly, not block on the server). Capture its PID and the dashboard URL it prints ("CodeBurn dashboard at http://...").
5. Create `.cairn/` in the project root if it doesn't exist, write the PID and URL to `.cairn/usage-dashboard.pid`.
6. Ensure `.cairn/` is gitignored: if the project has a `.gitignore` and it doesn't already mention `.cairn/`, append it. If there's no `.gitignore` at all, leave it — don't create one just for this.
7. Report the dashboard URL to the user, and that `/cairn-usage stop` shuts it down.
