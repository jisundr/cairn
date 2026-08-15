---
name: coding-chain-shared
description: Shared template assets for cairn's coding-chain agents (project-manager, harness-engineer, task-orchestrator, qa-engineer, software-engineer, qa-auditor) — TRACKER.md format, per-task STATE/HISTORY/UAT templates, .harness/ templates. Loaded by each at the start of a run that creates or reads these files.
---

# Coding Chain Shared — Template Assets

Shared file templates used across the coding chain. Each agent loads this skill once at the start of any run that creates or reads `docs/.tasks/TRACKER.md`, a per-task folder, or `.harness/`.

## Templates in this skill

- `assets/TRACKER.template.md` — seed content for `docs/.tasks/TRACKER.md` (`project-manager`, Generate mode)
- `assets/task/STATE.template.md` — seed content for `docs/.tasks/<slug>/STATE.md` (`task-orchestrator`, Plan Mode)
- `assets/task/HISTORY.template.md` — seed content for `docs/.tasks/<slug>/HISTORY.md` (`task-orchestrator`, Plan Mode)
- `assets/task/UAT.template.md` — seed content for `docs/.tasks/<slug>/UAT.md` (`task-orchestrator`, Publish Mode)
- `assets/harness/architecture.template.md`, `standards.template.md`, `workflow.template.md` — seed shape for `.harness/*.md` (`harness-engineer`, Generate mode)

Every template's headings are structural scaffolding only — content under them is always derived (evidence-based for `.harness/`, decomposed-from-PRD for `TRACKER.md`, chain-state for `STATE.md`/`HISTORY.md`/`UAT.md`), never copied verbatim from the template itself.

## Status values (`TRACKER.md`)

`Idea` · `Groomed` · `In Progress: <phase>` · `In Review` · `Blocked` · `Done` — see `assets/TRACKER.template.md` for the legend. `Idea` = no ticket yet (rows can be hand-authored, never required to trace to a PRD requirement). `Groomed` = a ticket exists, chain not yet started. `In Progress`/`In Review`/`Done` mirror the ticket's own status, flipped live by `task-orchestrator` via `project-manager`. `Blocked` maps from `STATE.md`'s `HANDOFF NEEDED` phase.

## Phase values (`STATE.md`)

`PLAN` · `DOC-GATE` · `QA-RED` · `IMPLEMENT` · `QA-AUDIT` · `DOC-POST-IMPL` · `PUBLISH` — one per chain-agent invocation, in order. Plus `HANDOFF NEEDED` as an unattended-only pause state.
