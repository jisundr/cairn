> Refines coding-chain behavior. Cannot skip chain agents or verification.

# Architecture Rules

## Stack
- Claude Code plugin, not a project-installed framework — content flat at repo root (`agents/`, `commands/`, `hooks/`, `skills/`, `scripts/`), distributed via `/plugin install` — *from-codebase*
- `scripts/usage_dashboard.py` is stdlib-only Python, no dependencies — *from-codebase* (pyproject.toml `dependencies = []`)

## Layering
- `agents/` = subagent defs, `commands/` = slash commands, `skills/` = shared skill/template assets, `hooks/` + `hooks/scripts/` = SessionStart hooks, `scripts/` = standalone utilities — no nested `src/` — *from-codebase*

## Boundaries
- Writer-agent output dirs strictly separated by concern — `docs/requirements/`, `docs/design/`, `docs/architecture/`/`docs/backend/`/`docs/adr/`, vs. dot-prefixed private working dirs `docs/.specs/`, `docs/.plans/`, `docs/.tasks/`, `docs/.drafts/` — *from-codebase*

## Data
- No database — persistence is flat files: JSONL transcripts (external, read-only, `~/.claude/projects/...`), append-only `.cairn/version-log.jsonl`, `docs/.tasks/TRACKER.md` as a flat markdown table used as a data store — *from-codebase*
