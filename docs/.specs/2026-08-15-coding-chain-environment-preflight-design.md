# Design: Environment preflight for the coding chain

## Summary

The coding chain has no step that checks whether the machine actually running it is fit to — toolchain versions, required local services, required env vars. `qa-auditor`'s security/perf/dependency checks are conditional and code-scoped; `task-orchestrator`'s Step 7 feasibility assessment checks whether the *plan* is testable/implementable, not whether the *environment* running it is sane. Nothing today catches a "works on my machine" divergence before a task starts.

This adds a fourth `.harness/` convention file, `environment.md` (declarative, machine-checkable rules — distinct in kind from the prose guidance in `architecture.md`/`standards.md`/`workflow.md`), authored by `harness-engineer` using its existing evidence-derivation + confirm-gate pattern, and executed by a new `task-orchestrator` Plan Mode step before branch/worktree creation.

No new agent. Two existing agents change: `harness-engineer` (4th file) and `task-orchestrator` (one new step). `coding-chain-shared`'s template bundle gains one file.

## Scope decision

| Option considered | Why not |
|---|---|
| New dedicated `environment-engineer` agent | Would duplicate `harness-engineer`'s evidence-derivation + `AskUserQuestion` confirm-gate + ~40-line-cap machinery for no real gain — the only thing that differs is *what's being derived* (checkable rules vs. prose conventions), not *how*. Extending `harness-engineer` keeps "one agent owns all `.harness/` files." |
| Free-form shell commands per check | Maximum flexibility, but the whole file becomes executable payload `task-orchestrator` runs unattended (including in tmux-detached Unattended mode) — too large a blast radius for a file whose primary content should be ordinary version/port/env-var checks. |
| Delegate entirely to a project-owned `check-env` script | Lightest cairn footprint, but only works for projects that already have one; `harness-engineer`'s evidence-derivation step would have nothing to offer out of the box for the common case. |
| Standalone check decoupled from `task-orchestrator` (like `/cairn-doctor`) | Rejected in favor of a `task-orchestrator` Plan Mode step — the check needs to gate the chain itself (block before branch/worktree creation), not just be separately invocable. |
| Silent-skip on an unrunnable check (matching `codebase-auditor`'s "best-effort, skip silently if tool unavailable" precedent) | Deliberately rejected here — see Degradation below. A check whose command can't run at all is treated as failed, not `UNVERIFIED`, because the point of this feature is catching "my machine isn't set up right," and a missing checker binary is itself evidence of that. |

## `.harness/environment.md` format

A typed check vocabulary, not free-form shell — three declarative kinds interpreted by `task-orchestrator` directly (no shell execution), plus one escape-hatch kind that does:

| Kind | Fields | How it's checked |
|---|---|---|
| `tool-version` | `tool`, `min` | Run `<tool> --version`, parse and compare against `min` |
| `port-open` | `host`, `port` | TCP connect attempt only, no payload sent |
| `env-var-set` | `name` | Presence check only — cairn never reads or logs the value |
| `command` | `cmd`, `expect-exit` | Literal shell string, compared against expected exit code — the one kind that executes arbitrary shell, used only when the other three can't express the check |

Each check carries a severity tag (`[blocking]` / `[warning]`) and an evidence note, matching the other three `.harness/` files' convention:

```
> Refines coding-chain behavior. Blocking checks gate task-orchestrator Plan Mode.

# Environment Checks

## Toolchain
- [blocking] node >= 20.0.0 — tool-version: node, min 20.0.0 — evidence: package.json engines.node
## Services
- [blocking] Postgres reachable — port-open: localhost:5432 — evidence: docker-compose.yml
## Env vars
- [warning] DATABASE_URL set — env-var-set: DATABASE_URL — evidence: .env.example
```

Same ~40-line cap as the other three files. Seed template: `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/harness/environment.template.md`, added to `coding-chain-shared`'s asset bundle alongside `architecture.template.md`/`standards.template.md`/`workflow.template.md`.

## `harness-engineer` changes

Fourth file, same Generate/Update modes, same per-rule `AskUserQuestion` confirm gate — including severity (`blocking`/`warning`) as part of what gets confirmed per check, never auto-assigned.

Evidence sources for candidate checks:

- **Toolchain** — `package.json` `engines` field, `.nvmrc`, `.python-version`, `.tool-versions`, CI config's declared runtime versions.
- **Services** — `docker-compose.yml` service ports, any `Procfile`/`docker-compose.override.yml`.
- **Env vars** — `.env.example` key names only, never values.

Generate mode's fresh-codebase fallback (pre-fill from `docs/architecture/architecture-spec.md`, then interview) and Update mode's diff-and-amend behavior both extend to this file unchanged — no new mode, no new gate shape.

## `task-orchestrator` changes

New **Step 4.5 — Environment Preflight**, Plan Mode, inserted between the existing Step 4 (`.harness/workflow.md` load) and Step 5 (branch/worktree creation) — before any branch or worktree gets created, so a failed blocking check never leaves a half-set-up task behind.

1. `Glob(.harness/environment.md)` — absent → skip silently, no note. Same optionality as every other `.harness/` file today; no regression for repos that don't have one.
2. Present → `Read` it, run each check via its typed interpreter (see format above).
3. A check whose command can't execute at all (missing binary, unreachable host, whatever the cause) counts as **failed** — not skipped, not `UNVERIFIED`. Same treatment as an actual value mismatch.
4. Any failed `[blocking]` check → `AskUserQuestion` (Attended) / `STATE.md` `Phase: HANDOFF NEEDED` (Unattended) — same shape as Step 7's feasibility-blocker gate: fix the environment and retry, or proceed anyway and accept the risk. Failed `[warning]` checks are noted only, never pause.
5. Results (pass/fail per check, by name) fold into `STATE.md`'s `Key info` at Step 9 (write time), alongside the existing feasibility notes and `.harness/` suggestion flag — so a resumed or Unattended-monitored task shows what was actually checked.

No other step changes. Step 6 (`.harness/` absence suggestion) is unaffected — it already suggests running `harness-engineer` when `.harness/` is missing entirely, which now also covers the case where `environment.md` specifically doesn't exist yet.

## Error handling summary

| Condition | Result |
|---|---|
| `.harness/environment.md` absent | Skip silently, no note |
| Check passes | No note beyond the STATE.md tally |
| `[warning]` check fails | Noted in `STATE.md` `Key info`, never pauses |
| `[blocking]` check fails (real mismatch) | `AskUserQuestion` / `HANDOFF NEEDED` — fix or proceed anyway |
| `[blocking]` check's own command can't run | Same as a real failure — no silent-skip tier |

## Testing & verification

`harness-engineer`'s new file-generation path is agent-level, natural-language instructions — not independently unit-testable, same as its other three files (per this repo's existing distinction between deterministic tests and command/agent behavior verified by scratch-directory runs).

`task-orchestrator`'s new step needs a manual end-to-end run per this repo's "Testing a command end-to-end" convention: a scratch repo with a `.harness/environment.md` containing one intentionally-failing `[blocking]` check, confirming the gate actually fires (Attended `AskUserQuestion` / Unattended `HANDOFF NEEDED`) and that `STATE.md` records the check results correctly.

## Out of scope

- No retroactive check of an already-running task — this gates Plan Mode's Step 4.5 only, once, before branch/worktree creation.
- No periodic re-check during a long-running task — if the environment changes mid-task (a service goes down), that's caught by whatever step actually needed it (tests failing, `software-engineer` unable to run something), not by this preflight.
- No auto-remediation — a failed check is surfaced, never auto-fixed (installing a missing tool, starting a missing service, etc. stays a human/CI concern).
