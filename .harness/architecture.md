> Refines coding-chain behavior. Cannot skip chain agents or verification.

# Architecture Rules

## Stack
- Claude Code plugin, not a project-installed framework — content flat at repo root (`agents/`, `commands/`, `hooks/`, `skills/`, `scripts/`), distributed via `/plugin install` — *from-codebase*
- `scripts/usage_dashboard.py` is stdlib-only Python, no dependencies — *from-codebase* (pyproject.toml `dependencies = []`)
- `dashboard/` git submodule: Vite + React + TypeScript SPA, its own npm build-time toolchain — *from-plan* (docs/.plans/2026-08-19-cairn-dashboard-react-redesign.md)

## Layering
- `agents/` = subagent defs, `commands/` = slash commands, `skills/` = shared skill/template assets, `hooks/` + `hooks/scripts/` = SessionStart hooks, `scripts/` = standalone utilities — no nested `src/` at the parent-repo root — *from-codebase*
- `dashboard/` submodule is exempt from the no-nested-`src/` rule: its own conventional Vite/React `src/` layout (`dashboard/src/components/`, etc.) is separate plugin content, not the parent repo's — *from-plan* (docs/.plans/2026-08-19-cairn-dashboard-react-redesign.md)

## Boundaries
- Writer-agent output dirs strictly separated by concern — `docs/requirements/`, `docs/design/`, `docs/architecture/`/`docs/backend/`/`docs/adr/`, vs. dot-prefixed private working dirs `docs/.specs/`, `docs/.plans/`, `docs/.tasks/`, `docs/.drafts/` — *from-codebase*

## Data
- No database — persistence is flat files: JSONL transcripts (external, read-only, `~/.claude/projects/...`), append-only `.cairn/version-log.jsonl`, `docs/.tasks/TRACKER.md` as a flat markdown table used as a data store — *from-codebase*
