# Dashboard React Redesign — Design

Date: 2026-08-19
Status: Approved (design), pending implementation plan
Tracking: [jisundr/cairn#7](https://github.com/jisundr/cairn/issues/7)

## Context

`scripts/usage_dashboard.py` is a stdlib-only Python HTTP server that reads Claude Code session transcripts and `docs/.tasks/TRACKER.md` directly, and serves a single-file inline-HTML/CSS/JS dashboard (Usage tab, Tracker tab). It is deliberately zero-dependency — no build step, nothing beyond `python3` required to run it. `commands/cairn-dashboard.md` launches it as a background process (PID lockfile), gated on `/cairn-setup` having run.

The user wants the dashboard redesigned to be more interactive. A separate, currently-empty scaffold repo (`git@github.com:jisundr/cairn-dashboard.git`, README stub only) is designated to hold the new frontend, added as a git submodule.

This spec also folds in [jisundr/cairn#6](https://github.com/jisundr/cairn/issues/6) (Swarms tab — track running `Mode: Unattended` tasks) — rather than build that tab twice (once in the old vanilla-JS dashboard, once ported to React), it's built directly as a React tab from the start. The backend piece of #6 (parsing `STATE.md`, discovering swarms, tmux liveness checks) is unchanged by this decision — only the UI target changes.

## Decision: stack

**Frontend:** Vite + React (TypeScript), building to static `dist/` output, committed directly in the `cairn-dashboard` submodule repo. No Next.js — the app has no need for SSR, server-side routing, or API routes (it's a pure client-side SPA polling a JSON API), so Next.js's extra machinery buys nothing here that Vite doesn't already give more simply.

**Backend:** stays `scripts/usage_dashboard.py`, stdlib Python `http.server` — explicitly **not** FastAPI. FastAPI was considered (motivated by Airflow's webserver architecture) and rejected: it requires `pip install fastapi uvicorn`, breaking the zero-dependency promise `/cairn-dashboard` currently makes to every end user, and buys nothing this dashboard actually needs (no auth, no writes, no complex request validation, no RBAC/plugins — the things that justify FastAPI/Flask in something like Airflow). A handful of read-only JSON endpoints parsing local files doesn't need it.

This keeps "static" (no Node runtime needed to serve the UI) and "always-running backend" (Python, unchanged) as two independent, compatible facts rather than in tension.

## Architecture

- New git submodule `dashboard/` at the repo root, tracking `git@github.com:jisundr/cairn-dashboard.git`.
- Inside `dashboard/`: Vite + React SPA source, plus its own committed `dist/` build output. Bumping the dashboard's frontend = build inside the submodule repo, commit `dist/` there, then bump this repo's submodule pointer (gitlink) to the new commit. No build step required at `/cairn-dashboard` runtime.
- `scripts/usage_dashboard.py` keeps its existing responsibilities unchanged: parse transcripts (`aggregate_usage`), `TRACKER.md` (`parse_tracker_md`), and now `STATE.md`/`HISTORY.md` for swarms (new — see below). Only its HTML-serving path changes: the inline `PAGE_HTML` constant and its route are replaced by a static-file handler serving `dashboard/dist/` (`index.html` + built assets).
- `commands/cairn-dashboard.md` is unchanged in shape — same `/cairn-setup` gate, same `.cairn/usage-dashboard.pid` lockfile, same background launch and browser-open — still a single long-running Python process. One addition: on launch, if `dashboard/dist/index.html` is missing, auto-run `git submodule update --init dashboard` before serving (see Error handling).

## Components

- **`dashboard/` (submodule)** — three tabs:
  - **Usage** — ported from the existing vanilla-JS implementation (stat grid, cost-over-time chart, by-model/by-version/by-subagent/by-skill rankings, sessions table).
  - **Tracker** — ported from the existing vanilla-JS implementation (Board/Roadmap sub-views).
  - **Swarms** (new, per #6) — built directly in React, no vanilla-JS predecessor. Shows `Mode: Unattended` tasks: phase, branch, worktree, tmux liveness, `HANDOFF NEEDED` pane tail, stalled indicator (authoritative `STATE.md` `Status: STALLED (...)` badge + soft "no progress in Xm" hint). See #6's own design for the full field list — unchanged by this redesign, only its rendering target changes.
- **`scripts/usage_dashboard.py`** — backend, gains:
  - `parse_state_md(path)` — generic `STATE.md` key:value parser (new, needed for Swarms).
  - `discover_swarms(cwd)` — glob `docs/.tasks/*/STATE.md`, filter `Mode: Unattended`, join `HISTORY.md`.
  - `tmux has-session` / bounded `tmux capture-pane` calls, read-only, degrading to `unknown`/skipped if `tmux` isn't installed.
  - `GET /api/swarms` endpoint.
  - Static-file serving for `dashboard/dist/`, replacing the inline-`PAGE_HTML` route.
  - `GET /api/usage`, `GET /api/tracker`, `--task-report`, `--window-report` — all unchanged.

## Data flow

- Same polling pattern as today: the SPA fetches `/api/usage`, `/api/tracker`, `/api/swarms` on a 4s interval, plain React state (`useState`/`useEffect`) — no state-management library needed at this size.
- Dev-only workflow (contributors working on `dashboard/`, not end users): `npm run dev` inside the submodule runs Vite's dev server with hot reload, proxying `/api/*` requests to the already-running Python backend (`/cairn-dashboard` started separately) so live data is available without rebuilding.

## Error handling

- `dashboard/dist/` missing or empty (submodule never initialized) → `/cairn-dashboard` attempts `git submodule update --init dashboard` automatically on launch (a read-only fetch/checkout of the already-recorded submodule commit, not a destructive operation). If that fails (offline, no recorded commit yet, detached submodule config) → clear error message instead of a crash or a blank page. This is a new failure mode that didn't exist when the HTML was inline in the Python script.
- Existing empty-state handling (no `TRACKER.md` rows, no swarms running) carries over unchanged in behavior, re-implemented in React.

## Testing

- Python: `tests/test_usage_dashboard.py` extended for the new static-file route and `/api/swarms` (`tmp_path` fixtures; `tmux` subprocess calls monkeypatched — deterministic, no real subprocess calls in CI). Same suite, same conventions as today.
- `dashboard/`'s own tests (e.g. Vitest + React Testing Library) live inside that submodule repo as its own concern — not run as part of this repo's `pytest` suite.

## Open questions (not blocking this spec)

- **Release/version-bump workflow for the submodule pointer** — how a future cairn release updates `dashboard/`'s tracked commit (manual `git submodule update --remote` + commit for now; could fold into `release-manager` later). Deferred — not designed here.
- Whether `dashboard/`'s own CI (tests, build verification) is wired into this repo's GitHub Actions or stays entirely within the `cairn-dashboard` repo. Deferred.

## Out of scope

- Any change to the transcript-parsing, cost-calculation (`MODEL_PRICING`), or `--task-report`/`--window-report` CLI logic — all unchanged by this redesign.
- Auth, multi-user access, or remote hosting — this remains a local, single-user, `127.0.0.1`-only tool exactly as today.
