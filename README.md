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

## Commands

- `/cairn-setup` — wires `intent-analyzer` as a project's entrypoint by adding a marked section to that project's root `CLAUDE.md`. Once wired, every new request in that project is routed through `intent-analyzer` first — mandatory. This is opt-in: run it only in projects where you want that. If a teammate clones a project with cairn wired in but doesn't have the plugin installed, it offers to self-install (with their approval).
- `/cairn-teardown` — removes the wiring `/cairn-setup` added. Doesn't uninstall the plugin itself (`/plugin uninstall cairn@cairn-plugins` for that).
- `/cairn-usage` (or `/cairn-usage stop`) — realtime local usage dashboard for the current project: token totals and a per-session table, including which cairn version each session ran on. Reads Claude Code's own session transcripts directly, no dependencies. Requires `/cairn-setup` to have run first (`stop` doesn't). The per-session version column relies on a `SessionStart` hook that logs the running version — sessions from before `/cairn-setup` ran show `unknown`.
- `/cairn-doctor` — checks plugin version (offers to upgrade), `CLAUDE.md` wiring status, `.cairn/`'s self-ignoring `.gitignore`, and cleans up a stale dashboard lockfile. All informational or auto-fixed where safe — never blocks on anything.
