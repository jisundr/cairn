# Project Definition: cairn-dashboard

## Metadata
- Project Definition Version: v0.2
- Last Updated: 2026-08-19
- Derived From: User discovery interview
- Author:
  - AI Tool: Claude Code
  - LLM Model: claude-sonnet-5
- Reviewed By:

---

## Overview
cairn-dashboard is a local, single-user web dashboard for cairn: it shows Claude Code token usage/cost, a task tracker (Board/Roadmap views from `docs/.tasks/TRACKER.md`), and running Unattended coding-chain swarms. It solves the problem of having no visibility into AI-assisted dev work in progress — cost, task state, background chain runs — without digging through session transcripts or task files by hand.

## Goals
- Give real-time visibility into Claude Code usage/cost for the current project.
- Surface task-tracker state (Board/Roadmap) without opening `TRACKER.md` directly.
- Surface running Unattended swarms (phase, liveness, stalled/handoff status) without manually checking `tmux`/`STATE.md`.
- Be interactive and pleasant enough to actually open and check regularly, not just exist as a fallback tool.

## Non-Goals
- Multi-user access or shared/team dashboards.
- Authentication or access control.
- Remote hosting or exposure beyond `127.0.0.1`.

## Stakeholders
| Stakeholder | Role | Interest |
|---|---|---|
| Cairn author (you) | Primary and sole user | Wants daily-usable visibility into usage/cost, tasks, and swarms for their own cairn-driven projects |

## Constraints
- End users must need zero extra installs to run the dashboard — backend stays stdlib Python (`scripts/usage_dashboard.py` in the **parent `cairn` repo**, no FastAPI or other pip dependency), frontend ships as pre-built, committed static assets (Vite + React) in this repo's own `dist/` — no Node/npm required at runtime.
- Local-only: binds to `127.0.0.1`, no remote hosting.

## Assumptions & Risks
- Assumption: a single user, running on their own machine against their own project's transcripts/task files, is sufficient scope — no need to design for concurrent/shared access.
- Risk: committing built frontend output (this repo's `dist/`, served by the parent repo as `dashboard/dist/`) directly into the `cairn-dashboard` repo is unusual repo hygiene and needs a manual sync/bump step whenever the dashboard changes — not yet automated (open question carried from the design spec at the **parent `cairn` repo**'s `docs/.specs/2026-08-19-dashboard-react-redesign-design.md`).

## Open Questions
- How does a future cairn release bump this repo's submodule pointer (as `dashboard/` in the parent `cairn` repo) — manual for now, could fold into `release-manager` later (carried from the design spec, not resolved here).
