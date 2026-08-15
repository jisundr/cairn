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

**`idea-explorer` (agents/)** — dispatched, non-interactive counterpart to a live `superpowers:brainstorming` dialogue: explores one bounded design question alone at `opus` (pinned regardless of session model), proposes 2-3 genuinely distinct approaches with a recommendation, and writes to `docs/.drafts/YYYY-MM-DD-<topic>-idea.md` (matching the date format `superpowers:brainstorming` itself uses for `docs/superpowers/specs/`, but a deliberately separate path — drafts are exploration, not an approved spec). Has no `AskUserQuestion`; every uncertainty becomes a written Open Question with a provisional answer instead of a blocked run. Terminal — never hands off to another agent or skill. No dedicated slash command; Claude dispatches it via the Agent tool when a request matches its description (a bounded question, explicit no-interview preference, or background exploration). Hard-requires the `superpowers` plugin: it invokes `Skill(skill: "superpowers:brainstorming")` directly at the start of every run rather than keeping an independent copy of the methodology, and aborts (writes no file) if that fails — deliberate, so it never runs on a silently stale or improvised version of the methodology.

**`requirements-engineer` (agents/)** — produces one requirements artifact per invocation (Project Definition, PRD, User Stories, User Flows), dependency-ordered (project-definition → prd → user-stories/user-flows, tier 3 sequential not concurrent). Formal/Draft/Update modes. Flat `docs/requirements/` output only — no Feature Scope Resolution, no Feature Status Gate (both maestro-only conventions cairn has no counterpart for). Terminal — no automatic handoff to `documentation-auditor`. Invokes `Skill(skill: "writer-shared")` then `Skill(skill: "requirements-writing")`.

**`product-designer` (agents/)** — produces one design artifact per invocation (UX Specification, UI Layout Specification, Design System), dependency-ordered (prd+user-flows → ux-spec → ui-layout-spec; prd → design-system, independent branch). UI Layout Specification hard-requires Impeccable (a vendored third-party design tool, never shipped by cairn — same "hard-required, never reimplemented" pattern as `idea-explorer`/`superpowers`) to be present in the consuming project; aborts that one doc type if absent, invokes it once for pre-fill input into its own discovery rather than a second interview. Terminal. Invokes `Skill(skill: "writer-shared")` then `Skill(skill: "product-design-writing")` (plus `Skill(skill: "mermaid-diagrams")` for `ux-spec.md` only).

**`solution-architect` (agents/)** — produces one technical artifact per invocation (Architecture Specification, Database Schema, API Specification, or an ADR), dependency-ordered (prd+user-flows → architecture-spec → db-schema/api-spec). ADRs are standalone, immutable after write (status-only updates). Terminal. Invokes `Skill(skill: "writer-shared")` then `Skill(skill: "solution-architecture-writing")` (plus `Skill(skill: "mermaid-diagrams")` for `architecture-spec.md`/`db-schema.md`/ADRs, not `api-spec.md`).

**`documentation-auditor` (agents/)** — read-only validator across README/setup/API docs and requirements/design/architecture artifacts: existence, agent-roster accuracy (adapted for cairn's README bullet-list format), source accuracy, completeness, internal consistency, style, and cross-artifact traceability (e.g. every PRD `FR-###` must trace to a user story). Reports findings only — never auto-invokes a writer agent to fix them. Dispatched manually or by Claude, never automatically after a write.

**`codebase-auditor` (agents/)** — read-mostly (writes only its own report) snapshot of codebase health: best-effort tooling (`npm audit`/`outdated`, `tsc`, `eslint`, `pip-audit`, `mypy`, `ruff`, whatever the detected manifests justify — skipped silently, never failed, if unavailable), TODO/FIXME debt and secret-shaped-value grep sweeps (never reproduces a found secret's value, `file:line` only), and a grep-level dead-code pass labelled `INFO` unless corroborated by tooling. Writes one timestamped `docs/codebase-audit/YYYYMMDD-HHmmss-{project-name}.md`, no Update Mode. Distinct from `documentation-auditor`: that one is pure read-only and validates existing docs; this one analyzes source and produces a new artifact. Terminal, no skill loaded — ported from maestro's `codebase-auditor`, dropping its submodule-profiling interview, `codegraph` MCP dependency, and adaptive folder-splitting output (all YAGNI for cairn's single-file-snapshot convention).

**`competitor-analyst` (agents/)** — given named competitors (from opening context, confirmed via mandatory `AskUserQuestion` before any fetching, capped at 6 per run), researches each one's positioning, pricing, features, and strengths/weaknesses and writes one dated, citation-backed snapshot (`([Source](url), accessed YYYY-MM-DD)` or `UNVERIFIED`) with a `mermaid-diagrams` positioning quadrant chart to `docs/competitor-analysis/YYYYMMDD-HHmmss-{scope}.md`. Treats all fetched page content as untrusted data, never instructions (prompt-injection guard); degrades per-competitor to `DATA UNAVAILABLE` on fetch failure rather than aborting the run. No Update Mode. Deliberately does NOT hard-require the `marketing-skills` plugin's `competitor-profiling` skill as its engine — that skill assumes Firecrawl/DataForSEO MCP tools with no documented offline fallback, which would make this agent fail on any machine without those servers connected; it's mentioned only as an optional, never-auto-invoked pointer for deeper SEO/backlink research. Terminal, invokes `Skill(skill: "mermaid-diagrams")` only — ported from maestro's `competitor-analyst`, which was already close to cairn's conventions (single timestamped file, citation-first, offline-degrade).

**`market-researcher` (agents/)** — new agent, no maestro equivalent. Studies the market/customer side (segments, ICP, jobs-to-be-done, pain points, positioning gaps) as opposed to `competitor-analyst`'s named-competitor profiling. Hard-requires the `marketing-skills` plugin: invokes `Skill(skill: "marketing-skills:customer-research")` at the start of its research phase rather than keeping an independent copy of that methodology, and aborts (writes no file) if unavailable — same "hard-required, never reimplemented" pattern as `idea-explorer`/`superpowers`, chosen here (unlike `competitor-analyst`'s choice above) because `customer-research` is pure LLM methodology with no external-tool assumption, so it's safe to hard-require. Confidence-tiers every finding and persona (High/Medium/Low by source count); never invents persona detail below a 5-10-data-point bar, labelling thin personas provisional instead. Writes one dated `docs/market-research/YYYYMMDD-HHmmss-{scope}.md`, no Update Mode. Terminal.

**`documentation-engineer` (agents/)** — creates/updates README, setup guides, API docs, and developer guides. Discovers existing docs and source material first, follows existing conventions. Does not touch `agents/`/`skills/`/`commands/` files or requirements/design/architecture artifacts (those belong to the other four). Terminal, no skill loaded.

**End-to-end sequence (documented, not a `Workflow` script):** `requirements-engineer` (×4 tiers) → `documentation-auditor` → `product-designer` (×3) → `documentation-auditor` → `solution-architect` (×3, ADR any time) → `documentation-auditor`. This is guidance for Claude to follow by invoking each agent directly in the main thread, one at a time — not automated. The `Workflow` tool's `agent()` calls are non-interactive background subagents and can't host the live `AskUserQuestion` interviews all three writer agents require (a hard requirement documented in maestro's own `product-designer` source). A user can start at any stage, skip design entirely, or re-run any stage via its own Update Mode.

**`/cairn-setup` and `/cairn-teardown`** — wire/unwire `intent-analyzer` as a project's mandatory entrypoint by inserting/removing a `<!-- cairn:start --> ... <!-- cairn:end -->` marked block in that project's root `CLAUDE.md`. The block is self-guarding: it no-ops if the plugin isn't installed, and offers to self-install (with approval) rather than breaking a session that lacks it.

**`/cairn-usage` and `scripts/usage_dashboard.py`** — a realtime local dashboard for the current project, **gated on `/cairn-setup` having run** (checks for the `<!-- cairn:start -->` marker before starting; refuses otherwise). `usage_dashboard.py` is stdlib-only Python (no dependencies): it reads Claude Code's own session transcripts directly from `~/.claude/projects/<cwd with / replaced by ->/*.jsonl` (every assistant turn already has a `usage` block — no separate capture needed for tokens/cost) and serves a page that polls `/api/usage` every 4s. The one thing the transcripts don't record is which cairn version was active, so that comes from `.cairn/version-log.jsonl` instead (see hooks below), joined in by session id. The command manages a background process via a `.cairn/usage-dashboard.pid` lockfile (start/stop/idempotent-rerun) and ensures `.cairn/.gitignore` (a single `*`) exists — `.cairn/` is self-ignoring, the target project's own root `.gitignore` is never touched. `stop` itself is never gated — it's cleanup, always allowed.

**`/cairn-doctor`** — on-demand health check: plugin version (via `claude plugin update`), whether `superpowers` (an `idea-explorer` hard requirement) is installed and enabled, `CLAUDE.md` wiring status, `.cairn/.gitignore` presence/content, and stale dashboard lockfile cleanup. Every check is informational or auto-fixes something safe (append-only) — except the `superpowers` check, which only reports and suggests install commands as text, since installing a plugin on the user's behalf needs their explicit action. Nothing here is a gate, matching the "no gates" framing in the README.

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
