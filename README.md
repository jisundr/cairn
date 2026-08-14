# cairn

My personal bag of tricks. No warranty, no gates, use your judgment.

A Claude Code plugin — skills, agents, and commands I've found useful. Nothing here is mandatory; take what's relevant and ignore the rest.

## Install

```
/plugin marketplace add jisundr/cairn
/plugin install cairn@cairn-plugins
```

## Agents

- `intent-analyzer` — classifies a raw request into an intent category (`planning` / `coding` / `review` / `documentation` / `query` / `mixed`) and normalizes it before work begins. Category-only output, since cairn has no fixed agent roster to route into yet.
- `idea-explorer` — dispatched, non-interactive counterpart to a live `superpowers:brainstorming` dialogue. Explores a bounded design question alone at `opus`, proposes 2-3 genuinely distinct approaches with a recommendation, and writes the result to `docs/.drafts/YYYY-MM-DD-<topic>-idea.md`. Can't ask questions — surfaces uncertainty as an explicit Open Questions list instead of blocking. Use for a question you don't want to be interviewed about, or want explored in the background. Hard-requires the `superpowers` plugin — loads `superpowers:brainstorming` directly rather than keeping its own copy of the methodology; aborts if the plugin isn't installed.
- `requirements-engineer` — produces one requirements artifact per invocation (Project Definition, PRD, User Stories, User Flows), in dependency order. Formal, Draft, and Update modes. Writes to `docs/requirements/`.
- `product-designer` — produces one design artifact per invocation (UX Specification, UI Layout Specification, Design System). UI Layout Specification requires the third-party Impeccable tool vendored in your project (`.claude/skills/impeccable`) — cairn doesn't ship it, same pattern as the `superpowers` requirement on `idea-explorer`. Writes to `docs/design/`.
- `solution-architect` — produces one technical artifact per invocation (Architecture Specification, Database Schema, API Specification, or an ADR). ADRs are immutable after write — only their status can change later. Writes to `docs/architecture/`, `docs/backend/`, or `docs/adr/`.
- `documentation-auditor` — read-only documentation validator: checks README/setup/API docs plus requirements/design/architecture artifacts for accuracy, completeness, consistency, and cross-artifact traceability. Reports findings, never fixes them.
- `documentation-engineer` — creates and updates README, setup guides, API docs, and developer guides, following your project's existing conventions.

## Commands

- `/cairn-setup` — wires `intent-analyzer` as a project's entrypoint by adding a marked section to that project's root `CLAUDE.md`. Once wired, every new request in that project is routed through `intent-analyzer` first — mandatory. This is opt-in: run it only in projects where you want that. If a teammate clones a project with cairn wired in but doesn't have the plugin installed, it offers to self-install (with their approval).
- `/cairn-teardown` — removes the wiring `/cairn-setup` added. Doesn't uninstall the plugin itself (`/plugin uninstall cairn@cairn-plugins` for that).
- `/cairn-usage` (or `/cairn-usage stop`) — realtime local usage dashboard for the current project: token totals and a per-session table, including which cairn version each session ran on. Reads Claude Code's own session transcripts directly, no dependencies. Requires `/cairn-setup` to have run first (`stop` doesn't). The per-session version column relies on a `SessionStart` hook that logs the running version — sessions from before `/cairn-setup` ran show `unknown`.
- `/cairn-doctor` — checks plugin version (offers to upgrade), whether the `superpowers` plugin `idea-explorer` requires is installed, `CLAUDE.md` wiring status, `.cairn/`'s self-ignoring `.gitignore`, and cleans up a stale dashboard lockfile. All informational or auto-fixed where safe — never blocks on anything.
