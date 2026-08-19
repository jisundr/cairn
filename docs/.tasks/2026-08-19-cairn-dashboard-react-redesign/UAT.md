# UAT Checklist: cairn-dashboard-react-redesign

Manual verification for the Vite+React SPA redesign of `/cairn-dashboard` (three tabs — Usage, Tracker, Swarms — served as a static build from `dashboard/dist/`, replacing the old inline-HTML/vanilla-JS page). Automated coverage (pytest 44/44, dashboard Vitest 21/21, `npm run build`) already confirmed by `qa-auditor`'s independent rerun — this checklist is for what only a human eyeballing the running dashboard in a browser can confirm.

## Setup

- [ ] From a project that has run `/cairn-setup`, run `/cairn-dashboard` (or `/cairn:cairn-dashboard`) and confirm it auto-initializes the `dashboard/` submodule if not already checked out, then opens/serves the dashboard without requiring Node/npm to be installed.
- [ ] Confirm the page loads at `http://127.0.0.1:<port>` and shows three tabs: **Usage**, **Tracker**, **Swarms**.

## Usage tab (US-001)

- [ ] Confirm token/cost totals render, broken down by model, by cairn version, and by subagent/skill invocation counts.
- [ ] Confirm the Daily/24-hour chart and the usage heatmap render with real data (or an empty state if no sessions exist yet).
- [ ] Confirm the sessions table supports sort, filter, and pagination, and shows Model(s)/Tokens columns.
- [ ] Confirm ranking panels above the chart reflect the selected Window/All-time scope toggle.
- [ ] Trigger a call using a model absent from `MODEL_PRICING` (or inspect an existing one) and confirm it's excluded from the cost total with an "N call(s) used a model with no pricing entry" note, not silently costed at $0.
- [ ] Confirm the page auto-refreshes roughly every 4 seconds without a full reload.

## Tracker tab (US-002)

- [ ] With no `docs/.tasks/TRACKER.md` present, confirm the Tracker tab shows an empty state rather than an error.
- [ ] With a populated `TRACKER.md`, confirm the Board view renders a Status-column kanban (Idea/Groomed/In Progress/In Review/Blocked/Done).
- [ ] Confirm the Roadmap view groups rows by Milestone (a distinct rail from Status) and that a milestone spanning multiple statuses renders correctly.

## Swarms tab (US-003, issue #6)

- [ ] With no `Mode: Unattended` tasks present, confirm the Swarms tab shows an empty state.
- [ ] With an Unattended task's `STATE.md` present, confirm it's listed with tmux liveness (alive/dead/unknown) — confirm `Mode: Attended` tasks never appear here (FR-003).
- [ ] For a task paused at `Phase: HANDOFF NEEDED`, confirm a tmux pane-tail excerpt renders in the detail panel.
- [ ] Confirm the sort-order control (Priority/Recent activity/Name) reorders the list as expected.
- [ ] Confirm clicking a swarm opens its detail panel, and confirm the close-panel behavior works.
- [ ] Stop the `tmux` session backing a listed swarm (or run somewhere `tmux` isn't installed) and confirm liveness gracefully degrades to "unknown" rather than crashing the tab (NFR-003).

## Graceful degradation (NFR-003)

- [ ] Temporarily rename/remove `dashboard/dist/` and confirm `/cairn-dashboard` shows a clear error, not a blank page or an unexplained 500.
- [ ] Confirm the existing `/api/usage` and `/api/tracker` endpoints, and the `--task-report`/`--window-report` CLI entry points, still behave unchanged (FR-006/US-004) — this plan only extended `scripts/usage_dashboard.py`, never modified those code paths.

## Shipping a change (submodule workflow)

- [ ] Confirm `cd dashboard && npm run build` regenerates `dist/` byte-identical to what's committed (already confirmed by `qa-auditor`; worth a spot re-check if this checklist is run after further changes).
- [ ] Confirm `dashboard/dist/` is not present in any `.gitignore` (committed build output, per Global Constraints).

## Outstanding before this checklist is fully meaningful

- [ ] **Blocking for a fresh clone:** push the `dashboard/` submodule's 4 local commits to `git@github.com:jisundr/cairn-dashboard.git` (`cd dashboard && git push`) — the parent repo's submodule pointer bump is meaningless to anyone who doesn't already have these commits locally. See PR description.
