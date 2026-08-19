# User Stories: cairn-dashboard

## Metadata
- User Stories Version: v0.12
- Last Updated: 2026-08-19
- Derived From: docs/cairn-dashboard/requirements/prd.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: claude-sonnet-5
- Reviewed By:

---

## US-001 — View usage and cost

**Traces to:** FR-001, FR-004, FR-007, FR-008, FR-009, FR-010, FR-012

**User Story**
As a cairn author, I want to see my Claude Code token usage and cost at a glance, so that I can track spend without reading raw transcripts.

**Acceptance Criteria**
- [ ] Usage tab shows total cost, tokens, calls, sessions, and cache-hit rate for the selected period window.
- [ ] A cost-over-time chart renders for the selected window, zero-filled to every bucket in the window (hour/day/month depending on period), not just buckets with an actual session.
- [ ] By-model and by-version ranking lists render sorted descending by cost; by-subagent and by-skill ranking lists render sorted descending by invocation count.
- [ ] A sessions table lists individual sessions with their own cost/token/call figures.
- [ ] Author can switch the period type (Daily / Weekly / Monthly / Yearly / YTD); stats, chart, and rankings recompute against the already-fetched session list — no refetch. Defaults to Daily.
- [ ] Daily/Weekly/Monthly/Yearly periods carry an anchor date with prev/next navigation to page through history, plus a "Latest" control that jumps the anchor back to today. YTD has no anchor (always the current year to date).
- [ ] Daily period's chart shows 24 hourly buckets for the anchored day, not one single-day bar.
- [ ] Weekly/Monthly/Yearly periods are calendar-aligned to the anchor (e.g. Monthly = the 1st through the last day of the anchor's month), not a trailing N-day window.
- [ ] Yearly period's chart uses monthly buckets (12), not daily — a full year of daily points would be too dense to read.
- [ ] Author can toggle displayed times between UTC and Local; this shifts hour/day/month bucket boundaries and all displayed timestamps, independent of the period/anchor selection. Defaults to Local.
- [ ] The view updates within 4 seconds of new usage occurring (poll interval).
- [ ] A note is shown when one or more calls used a model with no pricing entry, distinct from the cost total.
- [ ] A GitHub-style usage heatmap renders first, above the period-filtered sections (stat grid, rankings, chart, sessions table): one cell per day, calendar-year-aligned (Sunday-start weeks, Jan 1 of the earliest activity year through the latest recorded session day), colored across 5 intensity levels by that day's token volume relative to the busiest day in the whole session history.
- [ ] The heatmap always covers full session history — it does not filter with the period/anchor selector — but its day boundaries shift with the UTC/Local toggle, same as the chart.
- [ ] Hovering a heatmap cell shows that day's date, token count, and cost.
- [ ] Sessions table shows Model(s) and Tokens columns in addition to Session/Started/Calls/Cost/Version; Tokens shows the total, with an input/output/cache-write/cache-read breakdown on hover.
- [ ] Clicking a sessions-table column header sorts by that column; clicking the same header again reverses direction.
- [ ] Sessions table can be filtered by model and by cairn version (independent dropdowns, both default to "All"), scoped to the sessions already in the current period window — no refetch.
- [ ] Sessions table is paginated with Prev/Next controls once the current window/filter has more sessions than one page.
- [ ] By-model, by-version, by-subagent, and by-skill panels render above the chart, always scoped to the current period/anchor window — no independent scope control.

**Edge Cases**
- No sessions in the selected window: stat grid shows zeroed values, chart/rankings/sessions table each show an empty state, not an error.
- A model absent from the pricing table: excluded from cost total, surfaced via the unpriced-calls note, not silently $0.
- Navigating past the earliest recorded session (prev) or past today (next): the button disables rather than paging into an empty/future window.
- No sessions at all (fresh install): heatmap area shows an empty-state message instead of an all-empty grid.
- A day with zero sessions: heatmap cell renders at the lowest (empty) level, not omitted from the grid.
- A model/version filter combination matches zero sessions in the window: table shows its empty state, not a blank body.
- Switching period, anchor, or tz while a sort/filter/page is active: page resets to 1 (the row set changed); sort and filter selections persist across the switch.

---

## US-002 — View task tracker state

**Traces to:** FR-002, FR-004

**User Story**
As a cairn author, I want to see my task tracker's Board and Roadmap views, so that I know what's in progress without opening `TRACKER.md` directly.

**Acceptance Criteria**
- [ ] Board tab shows every `TRACKER.md` row grouped by its Status column.
- [ ] Roadmap tab groups rows by Milestone instead of Status.
- [ ] An empty state is shown when `TRACKER.md` doesn't exist or has no rows yet.

**Edge Cases**
- `TRACKER.md` missing entirely: empty state, not a server error.
- A row with no Milestone set: grouped under "Unsorted" on the Roadmap view.

---

## US-003 — Monitor running swarms

**Traces to:** FR-003, FR-004

**User Story**
As a cairn author, I want to see my running Unattended coding-chain swarms in a list + detail view, so that I know their full status without manually checking `tmux` or `STATE.md`, and without leaving the screen to see the detail.

**Acceptance Criteria**
- [ ] Swarms tab lists only `Mode: Unattended` tasks — Attended tasks never appear here.
- [ ] Left list shows each swarm's slug, phase, tmux liveness, and elapsed/last-activity time.
- [ ] Left list is sortable — Priority (Handoff Needed → Stalled → Running → Done), Recent activity (most recent `HISTORY.md` update first), or Name (chronological by date-prefixed slug) — Priority is the default. Sort selection persists across polls, recomputed client-side, no refetch.
- [ ] Clicking a swarm selects it and opens its detail in a right-side panel; the list stays visible and another swarm can be selected without navigating away. No selection shows an empty-state right panel ("Select a swarm to see details").
- [ ] Detail panel shows a phase-progress timeline (PLAN → DOC-GATE → QA-RED → IMPLEMENT → QA-AUDIT → DOC-POST-IMPL → PUBLISH) with the current phase highlighted, computed from the swarm's current `phase` value's position in that fixed order.
- [ ] Detail panel shows branch, worktree, and elapsed/last-activity time.
- [ ] Detail panel shows a scrollable recent-history log (last several `HISTORY.md` phase-transition lines, newest first).
- [ ] Detail panel shows the bounded pane-tail excerpt only when the selected swarm's phase is `HANDOFF NEEDED`.
- [ ] A "stalled" badge is shown (list and detail) only when `STATE.md`'s own `Status` field already carries the `STALLED (...)` marker — the dashboard never computes or declares this itself.
- [ ] A soft "no progress in Xm" hint is shown for a swarm with no recent `HISTORY.md` activity that isn't already `STALLED`, `HANDOFF NEEDED`, or `PUBLISH`.
- [ ] An empty state is shown when no Unattended swarms are currently tracked (both list and detail panel).

**Edge Cases**
- No `docs/.tasks/` folder at all: empty state, not an error.
- `tmux` not installed on the machine running the dashboard: liveness shows "unknown" rather than false/dead.
- A swarm mid-chain but not yet stalled: shows the soft "no progress in Xm" hint only, never the authoritative stalled badge.
- A swarm with fewer than the shown history-log window's worth of entries: log renders whatever exists, no padding/placeholder rows.
- The selected swarm disappears from the list on a poll (e.g. task folder removed): detail panel reverts to the empty state rather than showing stale data.

---

## US-004 — CLI reports keep working

**Traces to:** FR-006

**User Story**
As `task-orchestrator` (consuming agent, not the human persona), I want the `--task-report`/`--window-report` CLI entry points to keep working unchanged, so that Publish Mode and Lightweight Finish can still generate PR/MR usage tables after the redesign.

**Acceptance Criteria**
- [ ] `python3 scripts/usage_dashboard.py --task-report <slug>` produces the same markdown table output as before the redesign.
- [ ] `python3 scripts/usage_dashboard.py --window-report <start> <end> [cwd]` produces the same markdown table output as before the redesign.
- [ ] Neither entry point depends on `dashboard/dist/` existing or the HTTP server running — both work standalone via direct script invocation, as today.

**Edge Cases**
- `dashboard/dist/` missing entirely: both CLI report modes still succeed, since they don't touch the frontend at all.

---
