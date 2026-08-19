# UAT Checklist: cairn-dashboard-react-redesign

Manual verification for the Vite+React dashboard redesign (replaces the inline-HTML/vanilla-JS frontend with a 3-tab SPA — Usage, Tracker, Swarms — served as static files by `scripts/usage_dashboard.py`).

## Launch

- [ ] In a project that has run `/cairn-setup`, run `/cairn-dashboard` — it starts without error and opens a browser tab.
- [ ] In a fresh checkout where `dashboard/dist/` hasn't been initialized (`git submodule deinit dashboard` then re-run), `/cairn-dashboard` auto-runs `git submodule update --init dashboard` and still launches successfully.
- [ ] `/cairn-dashboard stop` shuts the server down and removes `.cairn/usage-dashboard.pid`.

## Usage tab (default, `#usage`)

- [ ] Loads with real session data — totals, sessions table, By model / By cairn version / Top subagents / Top skills ranking panels above the chart.
- [ ] Period buttons (Daily/WTD/MTD/YTD or equivalent) switch the chart and sessions table without a page reload; Daily shows 24 hourly buckets.
- [ ] UTC/Local toggle visibly shifts bucket boundaries.
- [ ] Usage heatmap renders full session history regardless of the selected period, and is unaffected by switching periods.
- [ ] Sessions table sorts on column click (second click reverses), filters by Model/Version, and paginates at 5 rows/page.
- [ ] With no sessions at all (fresh project), shows an empty state rather than an error.

## Tracker tab (`#tracker`)

- [ ] With a populated `docs/.tasks/TRACKER.md`, Board view renders a Status-column kanban (Idea/Groomed/In Progress/In Review/Blocked/Done).
- [ ] Roadmap view groups by Milestone instead of Status.
- [ ] With no `TRACKER.md`, shows an empty state rather than an error.

## Swarms tab (`#swarms`)

- [ ] Lists only `Mode: Unattended` tasks — an `Attended` task never appears here.
- [ ] Each row shows live `tmux` liveness; `tmux` unavailable shows `unknown` rather than crashing.
- [ ] Selecting a swarm opens the detail panel: phase timeline, branch, worktree, last-activity elapsed time, recent history log.
- [ ] A swarm at `Phase: HANDOFF NEEDED` shows a pane-tail excerpt in the detail panel; other phases don't.
- [ ] With no Unattended tasks, shows an empty state rather than an error.

## Backend regression (existing surface untouched — FR-006/US-004)

- [ ] `curl http://127.0.0.1:4756/api/usage`, `/api/tracker`, and `/api/swarms` each return valid JSON.
- [ ] `python3 scripts/usage_dashboard.py --task-report <slug>` and `--window-report <start> <end>` still work unchanged.

## Graceful degradation (NFR-003)

- [ ] Renaming/removing `dashboard/dist/` and hitting the dashboard URL returns a clear error naming `git submodule update --init dashboard`, not a blank page or unexplained 500.
