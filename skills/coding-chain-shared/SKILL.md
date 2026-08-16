---
name: coding-chain-shared
description: Shared template assets for cairn's coding-chain agents (project-manager, harness-engineer, task-orchestrator, qa-engineer, software-engineer, qa-auditor) — TRACKER.md format, per-task STATE/HISTORY/UAT templates, .harness/ templates. An asset bundle read by path, not a skill any agent invokes.
---

# Coding Chain Shared — Template Assets

Shared file templates used across the coding chain. This is an **asset bundle, not an invoked skill**: no agent calls `Skill(skill: "coding-chain-shared")` — `project-manager` doesn't even carry `Skill` in its `tools:` list, and `harness-engineer` carries it only for `graphify-context`. Instead, each agent `Read`s the specific template it needs directly by path at the point it seeds a file, using `${CLAUDE_PLUGIN_ROOT}/skills/coding-chain-shared/assets/...` (the plugin's own install location — a bare `skills/...` path would resolve against the consuming project's cwd and fail).

## Templates in this bundle

- `assets/TRACKER.template.md` — seed content for `docs/.tasks/TRACKER.md` (`project-manager`, Generate mode)
- `assets/task/STATE.template.md` — seed content for `docs/.tasks/<slug>/STATE.md` (`task-orchestrator`, Plan Mode)
- `assets/task/HISTORY.template.md` — seed content for `docs/.tasks/<slug>/HISTORY.md` (`task-orchestrator`, Plan Mode)
- `assets/task/UAT.template.md` — seed content for `docs/.tasks/<slug>/UAT.md` (`task-orchestrator`, Publish Mode)
- `assets/harness/architecture.template.md`, `standards.template.md`, `workflow.template.md`, `environment.template.md` — seed shape for `.harness/*.md` (`harness-engineer`, Generate mode). `environment.md` differs from the other three: its rules are a typed, machine-checkable vocabulary (`tool-version` / `port-open` / `env-var-set` / `command`) executed by `task-orchestrator`'s Environment Preflight step, not prose guidance other agents read and follow — each rule also carries a `[blocking]`/`[warning]` severity tag the other three files don't have.

Every template's headings are structural scaffolding only — content under them is always derived (evidence-based for `.harness/`, decomposed-from-PRD for `TRACKER.md`, chain-state for `STATE.md`/`HISTORY.md`/`UAT.md`), never copied verbatim from the template itself.

## Status values (`TRACKER.md`)

`Idea` · `Groomed` · `In Progress: <phase>` · `In Review` · `Blocked` · `Done` — see `assets/TRACKER.template.md` for the legend. `Idea` = no ticket yet (rows can be hand-authored, never required to trace to a PRD requirement). `Groomed` = a ticket exists, chain not yet started. `In Progress`/`In Review`/`Done` mirror the ticket's own status, flipped live by `task-orchestrator` via `project-manager`. `Blocked` maps from `STATE.md`'s `HANDOFF NEEDED` phase.

## Phase values (`STATE.md`)

`PLAN` · `DOC-GATE` · `QA-RED` · `IMPLEMENT` · `QA-AUDIT` · `DOC-POST-IMPL` · `PUBLISH` — one per chain-agent invocation, in order. Plus `HANDOFF NEEDED` as an unattended-only pause state.

## Two fields that behave differently (`STATE.md`)

`Key info` is **overwritten** every phase — it carries only what the next agent needs right now. `Harness flags` is **append-only** and accumulates across the whole chain: `qa-engineer`, `software-engineer`, and `qa-auditor` each append any `HARNESS FLAG:` note there (never to `Key info`), and `task-orchestrator` Publish Mode reads the accumulated field for its one consolidated harness/doc-drift question. Seeded as `none`; the first flag replaces that placeholder, later ones are added under it.
