# Product Requirements Document: cairn-dashboard

## Metadata
- PRD Version: v0.11
- Last Updated: 2026-08-19
- Derived From: docs/cairn-dashboard/requirements/project-definition.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: claude-sonnet-5
- Reviewed By:

---

## Overview
cairn-dashboard is a local, single-user web dashboard giving real-time visibility into Claude Code usage/cost, cairn task-tracker state, and running Unattended coding-chain swarms — replacing manual inspection of session transcripts, `TRACKER.md`, and `tmux`/`STATE.md`. This PRD covers the React redesign (Vite + React frontend, static build, served by the existing stdlib Python backend) and folds in the Swarms tab.

## Personas
| Persona | Description | Primary Goal |
|---|---|---|
| Cairn author/developer | Single user, running cairn against their own projects | Quickly check usage/cost, task state, and running swarms without digging through raw files |

## Functional Requirements
| ID | Requirement | Priority |
|---|---|---|
| FR-001 | Usage tab: cost/token totals, cost-over-time chart, by-model/by-version/by-subagent/by-skill rankings, sessions table | Must |
| FR-002 | Tracker tab: Board (Status-column kanban) and Roadmap (Milestone-grouped) views from `docs/.tasks/TRACKER.md` | Must |
| FR-003 | Swarms tab: list + detail view of `Mode: Unattended` tasks. List: phase, tmux liveness, elapsed time, sortable (Priority default / Recent activity / Name). Detail panel (opens on click, right side): phase-progress timeline, branch, worktree, elapsed time, recent-history log, `HANDOFF NEEDED` pane tail, stalled indicator (authoritative + soft hint) | Must |
| FR-004 | Frontend polls backend JSON APIs on a 4s interval for near-real-time updates | Must |
| FR-005 | ~~Frontend ships as a static, pre-built bundle...~~ — merged into NFR-001 (non-functional constraint, not a separate user-facing behavior) | Merged |
| FR-006 | Existing `--task-report`/`--window-report` CLI report entry points (used by `task-orchestrator`) keep working unchanged | Must |
| FR-007 | Usage tab supports calendar-period filtering (Daily / Weekly / Monthly / Yearly / YTD) with an anchor date and prev/next/Latest navigation to page through history, plus an independent UTC/Local timezone toggle — recomputed client-side against the already-fetched session list, no refetch | Must |
| FR-008 | Daily period shows an hour-by-hour (24-bucket) chart for the anchored day, not a single bar | Must |
| FR-009 | Usage tab shows a GitHub-style usage heatmap (calendar grid, one cell per day, colored by token-volume intensity) covering full session history — independent of the period/anchor filter, but re-bucketed on UTC/Local toggle | Should |
| FR-010 | Sessions table is sortable (click a column header), filterable by model and by cairn version (within the current period window), paginated, and shows a Model(s) column and a Tokens column (input/output/cache breakdown on hover) in addition to Session/Started/Calls/Cost/Version | Should |
| FR-011 | ~~Cost-over-time chart has independent Window/All-time scope and Cost/Tokens metric toggles...~~ — removed at user's request; chart is a plain, always-windowed Cost bar chart (no toggles), covered by FR-001 | Removed |
| FR-012 | By-model/by-version/by-subagent/by-skill ranking panels render above the cost-over-time chart, always scoped to the current period/anchor window (no independent scope toggle) | Should |

## Non-Functional Requirements
| ID | Category | Requirement |
|---|---|---|
| NFR-001 | Dependencies | Zero new runtime dependencies for end users — stdlib Python backend, pre-built static frontend (no Node/npm, no FastAPI, at runtime) |
| NFR-002 | Security | Local-only, bound to `127.0.0.1`, no authentication |
| NFR-003 | Reliability | Graceful degradation — a failed `tmux` check, a missing `dashboard/dist/`, an empty `TRACKER.md`, or zero running swarms each show a clear state; none crash the server |

## Out of Scope
- Authentication, multi-user access, or remote hosting (carried from Project Definition).
- Automated release/version-bump workflow for the `dashboard/` submodule pointer — manual for now.
- `dashboard/`'s own CI setup (tests, build verification) — a separate concern from this PRD.

## Open Questions
| # | Question | Owner | Status |
|---|---|---|---|
| 1 | How does a future cairn release bump the `dashboard/` submodule pointer? Manual today; could fold into `release-manager` later. | Cairn author | Open |
| 2 | Should `product-designer` (UX Spec / UI Layout Spec) be added to this pipeline before architecture? Currently skipped. | Cairn author | Open |
