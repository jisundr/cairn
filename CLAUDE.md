# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

cairn is a Claude Code **plugin** (not a project-installed framework) — a personal toolkit of agents, commands, hooks, and skills. Content lives flat at the repo root (`agents/`, `commands/`, `hooks/`, `skills/`, `scripts/`) per the plugin convention, not nested under `.claude/`. It's distributed via `/plugin install cairn@cairn-plugins`, so agents/commands only become available in a session *after* install — they don't load mid-session.

## Commands

- `pytest tests/ -v -s` — run everything. `-s` shows the eval suite's per-case pass/fail summary.
- `pytest tests/test_usage_dashboard.py -v` — the deterministic subset only (pure functions, fast, no external calls, always green — a failure here is a real regression).
- `pytest tests/test_intent_routing.py -v -s` — the eval suite (see Testing below). Slow (~1–2 min, runs cases in parallel), requires `claude` on `PATH` with real auth, and asserts an aggregate pass rate rather than gating on any single case.
- `claude plugin validate . --strict` — validates the plugin manifest; same check CI (`.github/workflows/validate.yml`) runs on every push.

### Testing a command end-to-end

Command files (`commands/*.md`) are natural-language instructions, not code — there's no unit test for them. Verify a command actually behaves as written by running it headless against a scratch directory:

```bash
cd /some/scratch/dir
claude -p "/cairn:cairn-usage stop" --plugin-dir /path/to/cairn --permission-mode bypassPermissions --output-format text
```

`--plugin-dir` loads the plugin for that one session without installing it; the command name is namespaced `/cairn:<command>`. Use a real scratch directory, not this repo, when a command touches `CLAUDE.md`/`.gitignore`/`.cairn/` — inspect the directory's contents afterward to confirm the actual file changes, not just the reported output.

## Architecture

**`intent-analyzer` (agents/)** — classifies a request into an intent category (`planning`/`coding`/`review`/`documentation`/`query`/`mixed`) and normalizes it. Its `ROUTING DECISION:` line names the category itself, not a downstream agent — cairn has no fixed agent roster to route into, unlike frameworks this was adapted from.

**`/cairn-setup` and `/cairn-teardown`** — wire/unwire `intent-analyzer` as a project's mandatory entrypoint by inserting/removing a `<!-- cairn:start --> ... <!-- cairn:end -->` marked block in that project's root `CLAUDE.md`. The block is self-guarding: it no-ops if the plugin isn't installed, and offers to self-install (with approval) rather than breaking a session that lacks it.

**`/cairn-usage` and `scripts/usage_dashboard.py`** — a realtime local dashboard for the current project, **gated on `/cairn-setup` having run** (checks for the `<!-- cairn:start -->` marker before starting; refuses otherwise). `usage_dashboard.py` is stdlib-only Python (no dependencies): it reads Claude Code's own session transcripts directly from `~/.claude/projects/<cwd with / replaced by ->/*.jsonl` (every assistant turn already has a `usage` block — no separate capture needed for tokens/cost) and serves a page that polls `/api/usage` every 4s. The one thing the transcripts don't record is which cairn version was active, so that comes from `.cairn/version-log.jsonl` instead (see hooks below), joined in by session id. The command manages a background process via a `.cairn/usage-dashboard.pid` lockfile (start/stop/idempotent-rerun) and ensures `.cairn/.gitignore` (a single `*`) exists — `.cairn/` is self-ignoring, the target project's own root `.gitignore` is never touched. `stop` itself is never gated — it's cleanup, always allowed.

**`/cairn-doctor`** — on-demand health check: plugin version (via `claude plugin update`), `CLAUDE.md` wiring status, `.cairn/.gitignore` presence/content, and stale dashboard lockfile cleanup. Every check is informational or auto-fixes something safe (append-only); nothing here is a gate, matching the "no gates" framing in the README.

**`hooks/hooks.json`** — `SessionStart` runs two scripts every session: `check-setup.sh` (fast structural sanity check on `agents/intent-analyzer.md`'s frontmatter — silent on success, non-blocking) and `log-version.sh`. `log-version.sh` is itself gated the same way as `/cairn-usage` — it checks for the `<!-- cairn:start -->` marker in `CLAUDE.md` and does nothing at all if it's absent, so `.cairn/` never gets created in a project that hasn't opted in via `/cairn-setup`, even though the hook runs every session regardless of whether cairn is actually being used there. When the project has opted in, it appends `{session_id, timestamp, version}` to `.cairn/version-log.jsonl` (version from `plugin.json`) and creates `.cairn/.gitignore` if missing. Both scripts are read-only/append-only and exit 0 even on failure — a hook here should never break a session.

**`.cairn/`** — the one per-consuming-project state directory cairn writes to, and only in projects that have run `/cairn-setup`: `usage-dashboard.pid` (lockfile), `version-log.jsonl` (per-session version history), and its own `.gitignore` (a single `*`, making the directory self-ignoring — nothing writes to a consuming project's own root `.gitignore`).

## Versioning

Bump `version` in `.claude-plugin/plugin.json` (semver — minor for new features, patch for fixes) whenever a change is something a consuming project needs to see reflected: new/changed agents, commands, or hooks, or any behavior change to what's already wired into a project. `log-version.sh` stamps this value into every session's `.cairn/version-log.jsonl` entry — an unbumped version makes that log lie about what actually ran, and `/cairn-doctor`'s upgrade check has nothing to detect. Skip the bump only for changes with no user-visible effect (docs, tests, internal refactors).

## Testing

Two distinct kinds of test, don't conflate them:

- **`tests/test_usage_dashboard.py`** — ordinary unit tests over pure functions (JSONL parsing/aggregation, using `tmp_path` fixtures). Deterministic, always green.
- **`tests/test_intent_routing.py`** — an *eval*, not a unit test. Each case is a real classification decision from a live `claude` CLI call (`model: haiku`, matching the shipped agent) on a prompt chosen to sit near a category boundary. A single case flipping between runs is expected model variance, not a regression — the test asserts an aggregate pass rate (`MIN_PASS` in that file) across the whole case set, not per-case. Only treat a case as actually broken if it fails consistently across reruns, or the failure reason itself is new.

<!-- cairn:start -->
## cairn (mandatory entrypoint)

If the cairn plugin is installed and its `intent-analyzer` subagent is available, EVERY new user request MUST be routed through `intent-analyzer` first to classify and normalize it before any other action — no exceptions.

If the cairn plugin is not installed, ask the user for approval to install it:
  /plugin marketplace add jisundr/cairn
  /plugin install cairn@cairn-plugins
If approved, install it, tell the user a new Claude Code session is required
before intent-analyzer becomes available, then proceed with this current
request normally (without cairn). If declined, also proceed normally.
<!-- cairn:end -->
