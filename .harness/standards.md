> Refines coding-chain behavior. Cannot skip chain agents or verification.

# Coding Standards

## Naming
- kebab-case filenames for agents/commands/skills, matching each file's frontmatter `name:` exactly — *from-codebase*
- Python: snake_case functions, UPPER_SNAKE_CASE module constants (`DEFAULT_PORT`, `MODEL_PRICING`) — *from-codebase*

## Error handling
- Python: narrow `try/except` on specific exceptions (`OSError`, `json.JSONDecodeError`), never bare `except`; explicit `raise RuntimeError(...)` for an exhausted-resource condition — *from-codebase*
- Bash hooks: `set -uo pipefail`; degrade silently with early `exit 0` when a prerequisite (marker file, `jq`, session id) is missing, rather than failing the session — *from-codebase*

## Testing
- Three distinct kinds, never conflated — `tests/test_usage_dashboard.py` (deterministic unit tests over pure functions, `importlib` by path), `tests/test_intent_routing.py` (eval suite, asserts aggregate pass rate not per-case — only treat a case as broken if it fails consistently across reruns), `tests/smoke/*.sh` (headless bash scripts, NOT pytest-collected, requires `claude` on PATH + `tmux` for Unattended fixtures) — *from-codebase*
- Run: `pytest tests/ -v -s` (full suite, skips `tests/smoke/`); `pytest tests/test_usage_dashboard.py -v` (deterministic subset only); `pytest tests/test_intent_routing.py -v -s` (eval, ~1-2 min); `bash tests/smoke/<script>.sh [plugin-dir]` (run individually) — *from-codebase*

## Logging
- No logging framework — hook scripts emit Claude Code's `hookSpecificOutput` JSON protocol to stdout on failure only; `usage_dashboard.py` uses stdlib `print(..., file=sys.stderr)` for CLI errors, plain `print()` for status — *from-codebase*
