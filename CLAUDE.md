# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

cairn is a Claude Code **plugin** (not a project-installed framework) — a personal toolkit of agents, commands, hooks, and skills. Content lives flat at the repo root (`agents/`, `commands/`, `hooks/`, `skills/`, `scripts/`) per the plugin convention, not nested under `.claude/`. It's distributed via `/plugin install cairn@cairn-plugins`, so agents/commands only become available in a session *after* install — they don't load mid-session.

## Commands

- `pytest tests/ -v -s` — run the pytest suite (unit tests + eval). `-s` shows the eval suite's per-case pass/fail summary. Does not collect `tests/smoke/*.sh` (see Testing below) — run those separately.
- `pytest tests/test_usage_dashboard.py -v` — the deterministic subset only (pure functions, fast, no external calls, always green — a failure here is a real regression).
- `pytest tests/test_intent_routing.py -v -s` — the eval suite (see Testing below). Slow (~1–2 min, runs cases in parallel), requires `claude` on `PATH` with real auth, and asserts an aggregate pass rate rather than gating on any single case.
- `bash tests/smoke/<script>.sh [plugin-dir]` — a headless smoke test (see Testing below); run individually, not via pytest.
- `claude plugin validate . --strict` — validates the plugin manifest; same check CI (`.github/workflows/validate.yml`) runs on every push.

### Testing a command end-to-end

Command files (`commands/*.md`) are natural-language instructions, not code — there's no unit test for them. Verify a command actually behaves as written by running it headless against a scratch directory:

```bash
cd /some/scratch/dir
claude -p "/cairn:cairn-dashboard stop" --plugin-dir /path/to/cairn --permission-mode bypassPermissions --output-format text
```

`--plugin-dir` loads the plugin for that one session without installing it; the command name is namespaced `/cairn:<command>`. Use a real scratch directory, not this repo, when a command touches `CLAUDE.md`/`.gitignore`/`.cairn/` — inspect the directory's contents afterward to confirm the actual file changes, not just the reported output.

## Architecture

Full detail (every agent's modes, handoffs, hard/soft dependencies, the coding-chain sequence, and each command/hook) lives in **`docs/ARCHITECTURE.md`**. Index below; read that file before touching any of this.

**Writer trio + support** (agents/): `intent-analyzer` classifies every request (`planning`/`coding`/`review`/`documentation`/`query`/`mixed`) and runs the Brainstorming Gate. `idea-explorer` is idea-explorer.md's non-interactive brainstorming counterpart (opus, `docs/.drafts/`). `spec-writing`/`plan-writing` (skills/) wrap `superpowers:brainstorming`/`writing-plans` with cairn's own save paths + Chain-vs-Direct heuristic + `/goal` offer. `requirements-engineer`, `product-designer`, `solution-architect`, `documentation-auditor` produce/validate requirements, design, and architecture artifacts (see End-to-end sequence in ARCHITECTURE.md). `codebase-auditor`, `competitor-analyst`, `market-researcher`, `documentation-engineer` are standalone report/doc agents.

**Coding chain** (agents/): `project-manager` (PRD → `docs/.tasks/TRACKER.md`, ticket sync), `harness-engineer` (`.harness/*.md` convention files), `task-orchestrator` (Plan/Publish/Lightweight modes — worktrees, PRs, Environment Preflight), `qa-engineer` (Chain-red/Direct/Feasibility test modes), `software-engineer` (Chain-green/Direct/Feasibility implementation, opus), `qa-auditor` (Chain-only post-impl re-verification), `release-manager` (semver bump + changelog + tag). Two flows off `intent-analyzer`'s routing: **Direct** (`software-engineer` → `qa-engineer`, no task file unless Lightweight Start ran) and **Chain** (`task-orchestrator` Plan → doc gate → `qa-engineer` red → `software-engineer` green → `qa-auditor` → doc post-impl → `task-orchestrator` Publish). Entry via `/cairn-run-task` or plain request through `intent-analyzer`.

**Shared skills**: `coding-chain-shared` (template asset bundle, not directly invoked), `graphify-context` (soft-optional Graphify detection/query, loaded by 8 agents).

**Commands**: `/cairn-setup`/`/cairn-teardown` (wire/unwire the mandatory-entrypoint marker block), `/cairn-dashboard` (realtime usage/tracker/swarms dashboard, gated on setup), `/cairn-doctor` (health check), `/cairn-release [rc]` (dispatches `release-manager`).

**Hooks** (`hooks/hooks.json`): `SessionStart` runs `check-setup.sh` + `log-version.sh` (writes `.cairn/version-log.jsonl` when opted in); `UserPromptSubmit` runs `goal-guard.sh` (`/goal`-vs-plan-file warning). All read-only/append-only, exit 0 on failure.

**`.cairn/`** — per-project state dir (dashboard lockfile, version log, self-ignoring `.gitignore`), only created after `/cairn-setup`.

## Versioning

Bump policy (semver: minor for new features/behavior changes, patch for fixes, skip for docs/tests/internal-refactor-only) lives in `.harness/workflow.md`. `log-version.sh` stamps whatever `version` is currently committed into every session's `.cairn/version-log.jsonl` entry — an unbumped version makes that log lie about what actually ran, and `/cairn-doctor`'s upgrade check has nothing to detect.

`release-manager` (see above) does not replace this rule — it reads whatever `version` is currently committed (the accumulated result of every manual per-change bump since the last tag) as its baseline, then proposes and writes a further bump on top of it for the release tag itself (e.g. a hand-bumped `0.18.0` becomes the release-manager-proposed `0.19.0` if there's another `feat:`-worthy change since). The two are sequential, not competing: your manual bumps stay authoritative for what's committed day-to-day, `release-manager` only decides the final release-point version at cut time, and always shows its proposed version for confirmation before writing it.

## Testing

Which of the three kinds a file belongs to, and the exact run commands, live in `.harness/standards.md`. Kept here since it's not mechanical convention: `tests/smoke/*.sh` also has `bash tests/smoke/run_all.sh [plugin-dir]` for `release-manager`'s suite specifically, and every script asserts against observable output/artifacts (a saved file, a `STATE.md` field, whether a `tmux` session still exists) rather than parsing the outer CLI's paraphrased text — that text varies run to run. Each script only exercises what a non-interactive run can reach — for `release-manager` that's Detect→Propose; anything gated behind an `AskUserQuestion` confirmation (Execute-step mechanics) has no automated coverage and is verified by code inspection instead.

<!-- cairn:start -->
## cairn (mandatory entrypoint)

If the cairn plugin is installed and its `intent-analyzer` subagent is available, EVERY new user request MUST be routed through `intent-analyzer` first to classify and normalize it before any other action — no exceptions.

This also applies when a skill's own trigger would otherwise fire directly
(e.g. superpowers:brainstorming's "let's build X", superpowers:writing-plans'
planning trigger) without having gone through intent-analyzer yet. Before
invoking either skill directly in that case, ask: "Route this through
intent-analyzer first, or continue directly with superpowers?" Proceed per
the user's answer.

If the cairn plugin is not installed, ask the user for approval to install it:
  /plugin marketplace add jisundr/cairn
  /plugin install cairn@cairn-plugins
If approved, install it, tell the user a new Claude Code session is required
before intent-analyzer becomes available, then proceed with this current
request normally (without cairn). If declined, also proceed normally.
<!-- cairn:end -->
