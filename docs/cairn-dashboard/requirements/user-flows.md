# User Flows: cairn-dashboard

## Metadata
- User Flows Version: v0.10
- Last Updated: 2026-08-19
- Derived From: docs/cairn-dashboard/requirements/prd.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: claude-sonnet-5
- Reviewed By:

---

## UF-001 — Launch the dashboard

**Traces to:** NFR-001, NFR-003

**Actor:** Cairn author
**Trigger:** Runs `/cairn-dashboard`
**Goal:** Get the dashboard running and open in the browser

**Happy Path**
1. `/cairn-dashboard` checks the `/cairn-setup` marker and the `.cairn/usage-dashboard.pid` lockfile.
2. Python backend starts, serving `dashboard/dist/` (this repo's pre-built static bundle, relative to the parent `cairn` repo) as static files plus the JSON APIs.
3. Browser opens to the dashboard, landing on the Usage tab.
4. **End state:** Author sees a working dashboard with no build step or extra install required.

**Alternate Paths**
- Dashboard already running (lockfile names a live process): reports the existing URL instead of starting a second instance.

**Error States**
- `dashboard/dist/` missing or empty (submodule not initialized): `/cairn-dashboard` shows a clear error explaining the fix (`git submodule update --init`), never a blank page. This affects the whole app, not any single tab.
- `/cairn-setup` hasn't run: refuses to start, points to `/cairn-setup` — unchanged from today's behavior.

---

## UF-002 — Check usage and cost

**Traces to:** US-001

**Actor:** Cairn author
**Trigger:** Opens the dashboard (via `/cairn-dashboard`) to check spend
**Goal:** See current token usage and cost for their project

**Happy Path**
1. Dashboard loads with the Usage tab active by default.
2. Stat grid, chart, and rankings render from the initial `/api/usage` fetch.
3. View auto-refreshes every 4 seconds as new usage occurs.
4. **End state:** Author sees up-to-date cost/token/session figures without leaving the browser tab.

**Alternate Paths**
- Author switches the period type (Daily / Weekly / Monthly / Yearly / YTD): stats, chart, and rankings recompute client-side against the already-fetched session list, calendar-aligned to the current anchor.
- Author clicks prev/next: anchor shifts by one period unit (a day, week, month, or year) and the view recomputes for that window.
- Author clicks "Latest": anchor jumps back to today.
- Author toggles UTC/Local: bucket boundaries and all displayed timestamps shift accordingly, independent of the period/anchor.
- Period is Daily: chart shows 24 hourly buckets for the anchored day instead of a single bar.
- Author hovers a cell in the usage heatmap (always full history, unaffected by the period/anchor filter): a tooltip shows that day's date, tokens, and cost.
- Author clicks a sessions-table column header: table sorts by that column (ascending, or descending on a second click), scoped to the current window's already-fetched rows.
- Author picks a Model or Version filter above the sessions table: table narrows to matching rows within the current window, no refetch; picking "All" clears that filter.
- Author clicks Prev/Next below the sessions table: table pages through the current (possibly filtered) row set.

**Error States**
- `/api/usage` fetch fails (server not running, network blip): UI shows a stale-data indicator on the existing view rather than freezing silently or clearing to blank.
- Author navigates prev past the earliest recorded session, or next past today: the button disables rather than paging into an empty/future window.
- No sessions recorded at all: the heatmap area shows an empty-state message rather than a grid of empty cells.
- A model/version filter matches no sessions in the window: table shows its own empty state rather than a blank body.

---

## UF-003 — Check task tracker state

**Traces to:** US-002

**Actor:** Cairn author
**Trigger:** Switches to the Tracker tab to see what's in progress
**Goal:** See current task states without opening `TRACKER.md`

**Happy Path**
1. Author clicks the Tracker tab.
2. Board sub-view renders `TRACKER.md` rows grouped by Status.
3. **End state:** Author sees every tracked task's current stage at a glance.

**Alternate Paths**
- Author switches to the Roadmap sub-view: same row data regrouped by Milestone instead of Status.

**Error States**
- `TRACKER.md` doesn't exist or has no rows: empty state shown ("No tasks tracked yet"), not an error page.

---

## UF-004 — Monitor running swarms

**Traces to:** US-003

**Actor:** Cairn author
**Trigger:** Switches to the Swarms tab to check on a background Unattended run
**Goal:** See whether a swarm is progressing, paused, or stalled without checking `tmux`/`STATE.md` by hand

**Happy Path**
1. Author clicks the Swarms tab.
2. Left list of `Mode: Unattended` tasks renders with phase, tmux liveness, and elapsed time per swarm; right panel shows an empty state ("Select a swarm to see details").
3. Author clicks a swarm in the list.
4. Right panel opens showing that swarm's phase-progress timeline, branch, worktree, elapsed time, and recent-history log. A swarm with no recent `HISTORY.md` progress (and not `HANDOFF NEEDED`/`STALLED`/`PUBLISH`) shows the soft "no progress in Xm" hint; a swarm whose `STATE.md` `Status` already carries the `STALLED (...)` marker shows the authoritative stalled badge instead.
5. **End state:** Author knows the selected swarm's full status — current phase, history, liveness, and whether it needs attention — without leaving the Swarms screen.

**Alternate Paths**
- Author clicks a different swarm in the list: detail panel swaps to the newly selected swarm, list selection updates.
- The selected swarm is at `HANDOFF NEEDED`: its pane-tail excerpt renders inline in the detail panel for extra context on what it's paused on.

**Error States**
- No `docs/.tasks/` folder, or no Unattended tasks: empty state shown ("No unattended swarms running"), not an error.

---
