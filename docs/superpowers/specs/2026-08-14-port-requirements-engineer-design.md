# Design: Port maestro's writer trio + doc agents into cairn

## Summary

Port five maestro agents into cairn, covering an end-to-end requirements → design → architecture pipeline:

- `requirements-engineer` — Project Definition, PRD, User Stories, User Flows
- `product-designer` — UX Specification, UI Layout Specification, Design System
- `solution-architect` — Architecture Specification, Database Schema, API Specification, ADRs
- `documentation-auditor` — read-only validator across all of the above, plus general project docs (README/setup/API/dev-guides)
- `documentation-engineer` — writes/updates README/setup/API/dev-guide docs

All five are self-contained and terminal — no automatic cross-agent handoffs. The three writer agents (`requirements-engineer`, `product-designer`, `solution-architect`) share a common shape (maestro calls this the "writer trio") and a common constraint: each runs a live, one-question-at-a-time `AskUserQuestion` discovery interview, which — per maestro's own `product-designer` HARD REQUIREMENTS — means **it must run in the main conversation thread**, not as a dispatched background subagent. That constraint shapes both the skill structure (below) and how the end-to-end sequence works (see "End-to-end sequence" — it is a documented order, not a `Workflow`-tool script, because `Workflow`'s `agent()` calls are non-interactive background subagents and can't host a live interview).

This is the first multi-agent-plus-skill port from maestro into cairn, and the first entries in cairn's `skills/` directory (currently empty).

## Source

- `~/Projects/maestro/.claude/agents/{requirements-engineer,product-designer,solution-architect,documentation-auditor,documentation-engineer}.md`
- `~/Projects/maestro/.claude/skills/writer-agent-guide/SKILL.md` (shared writer-trio mechanics)
- `~/Projects/maestro/.claude/skills/{project-definition,prd,user-stories,user-flows}-guide/SKILL.md` (requirements-engineer doc types)
- `~/Projects/maestro/.claude/skills/{ux-spec,ui-layout-spec,design-system}-guide/SKILL.md` (product-designer doc types)
- `~/Projects/maestro/.claude/skills/{architecture-spec,db-schema,api-spec,adr}-guide/SKILL.md` + `{db-standards,api-standards}-guide/SKILL.md` (solution-architect doc types + standards)
- `~/Projects/maestro/.claude/skills/mermaid-diagram-guide/SKILL.md` (diagram rules — used by `ux-spec.md`, `architecture-spec.md`, `db-schema.md`, and ADRs; verified NOT dead weight for the two doc-producing agents other than `requirements-engineer` — see below)
- `~/Projects/maestro/.claude/skills/impeccable-guide/SKILL.md` (reference only — see Impeccable section below; the `impeccable` tool itself is NOT a source, see below)

## Scope decision

maestro is a fully workflow-bound agentic framework: 19 agents wired into one mesh via `intent-analyzer` (central router, references all 19) and hub agents like `documentation-auditor`. `documentation-engineer` alone pulls in `gitlab-mr-reviewer`, `meta-engineer`, `meta-auditor`, `release-manager`, `task-orchestrator` through its Sync and Learnings Capture modes. Porting any one of these agents at face value pulls in that entire mesh.

cairn's design is the opposite: no fixed agent roster, self-contained agents (`idea-explorer` has exactly one hard external dependency — `superpowers:brainstorming` — and aborts rather than reimplement methodology it doesn't own). Recreating the full mesh would mean forking maestro's entire architecture into cairn, a different, much larger project.

**Decision: port five agents, each self-contained, at full general-purpose scope** (not narrowed to a single use case — these are meant to be reusable for future cairn doc/design/architecture work):
- `requirements-engineer`, `product-designer`, `solution-architect` — kept at full doc-type breadth each. Only the pieces that key off un-ported agents or maestro-only conventions (Feature Status Gate, Feature Scope Resolution, `.codegraph`/`.harness` tooling) are dropped.
- `documentation-auditor` — kept at full general-purpose breadth (Checks 1-7, all doc types).
- `documentation-engineer` — kept at full Create/Update-mode breadth (README, setup, API docs, developer guides). Sync Mode and Learnings Capture Mode dropped (deep, unrelated subsystems tied to un-ported meta-agents).

**No automatic handoffs.** All five stay terminal after their own work. Running `documentation-auditor` after a write is a separate, deliberate step.

**No `Workflow`-tool orchestration for the writer trio.** See "End-to-end sequence" below.

## What's dropped and why

### From `requirements-engineer`

| maestro feature | Why dropped |
|---|---|
| Automatic `PHASE HANDOFF → documentation-auditor` | No automatic handoffs (see above). |
| Feature Status Gate (reads `docs/project-definition/02_identity.md` Section 4) | Keyed to a maestro-wide feature-status tracking file cairn has no counterpart for. |
| Feature Scope Resolution / feature-scoped output paths (`docs/features/<name>/requirements/`) | Keyed to a `Feature Scope:` field maestro's own `intent-analyzer` injects into opening context; cairn's `intent-analyzer` has no such field. Flat paths only. |
| Optional Competitive Input (reads `competitor-analyst` snapshots) | `competitor-analyst` isn't being ported; optional/presence-gated in maestro too, so dropping changes nothing structurally. |
| ClickUp exit row (defers to `project-manager`) | `project-manager` isn't being ported. |
| `mermaid-diagram-guide` load step in Draft Phase | None of `requirements-engineer`'s 4 artifact templates use diagrams. **Scoped to this agent only** — verified `ux-spec.md`, `architecture-spec.md`, `db-schema.md`, and ADRs DO require it; kept for `product-designer`/`solution-architect` (see their sections below), not dropped globally. |
| Adaptive Output Rule (single-file vs numbered multi-file split) | None of the 4 doc-type guides define a Split Condition. |
| "Scope & Boundaries" 4-status-table section in Project Definition & PRD templates | Artifact-side half of the Feature Status Gate mechanic, dropped along with the gate. Goals/Non-Goals and Out of Scope lists cover the same need. |

### Stale writing-standard note, found across 5 more doc-type guides

Every doc-type guide checked (`ux-spec`, `ui-layout-spec`, `architecture-spec`, `db-schema`, `api-spec` — verified by reading each directly, not assumed from the `project-definition`/`prd` fix alone) carries the same trailing note:

> **Scope or Feature Coverage sections:** If a Scope or Feature Coverage section is included, represent it as status tables (one per feature status category: Implemented, Current, Pending Review — Pre-existing, Pending Review — Not Yet Implemented).

Same Feature-Status-Gate-tied convention already dropped from `project-definition.md`/`prd.md`'s actual template section — this is the conditional writing-standard version of the same dead rule (applies *if* such a section is ever added, which nothing in the ported templates does). Dropped from all 5 doc-type skills for the same reason. `user-stories`, `user-flows`, `design-system`, and `adr` guides don't carry this note — verified clean, no change needed there.

### From `product-designer`

| maestro feature | Why dropped |
|---|---|
| Automatic `PHASE HANDOFF → documentation-auditor` | No automatic handoffs. |
| Feature Status Gate / Feature Scope Resolution | Same as `requirements-engineer` — no cairn counterpart. |
| ClickUp / other cross-agent exit rows | N/A — none present in source beyond the generic ones. |

**Kept, adapted:**
- **Reference Artifact Intake** (UI Layout Spec & Design System only) — reads a local file or fetches a `claude.ai/artifacts`-style URL as visual reference, cross-checks against upstream docs, flags conflicts rather than silently overriding. Fully self-contained (`Read`/`WebFetch` only), no cross-agent dependency — kept as-is.
- **Impeccable Shape Pass** (UI Layout Spec only) — see below, adapted rather than dropped or kept as-is.
- **`mermaid-diagram-guide`** (UX Specification only — its "Interaction Flows" section requires one Mermaid flowchart per user journey). NOT loaded for UI Layout Specification (uses ASCII/text layout diagrams, not Mermaid) or Design System (no diagrams in its template). Verified by reading all 3 doc-type guides directly, not assumed from the shared `writer-agent-guide` step alone.

### Impeccable — hard-required, never vendored

`impeccable` is not a maestro-authored skill — it's a vendored third-party tool (51,295 lines: compiled CLI, scripts, config), a separate "design guidance system for AI coding agents" that maestro commits into its own repo. Vendoring it into cairn is a materially different decision than porting an agent definition (licensing, updates, ownership of someone else's code) and is explicitly out of scope for this port.

Instead, `product-designer` treats it the way `idea-explorer` treats `superpowers`: **hard-required, never reimplemented, abort rather than silently degrade** — but scoped to just the one doc type that needs it. Maestro's own template already excludes Impeccable from UX Specification and Design System (`Do NOT run this step for UX Specification or Design System artifacts`), so the hard-requirement is scoped the same way.

**Verified against the real vendored skill** (`~/Projects/maestro/.claude/skills/impeccable/SKILL.md`), not assumed:

- **Invocation mechanism resolved:** `impeccable/SKILL.md` carries `user-invocable: true` frontmatter — it IS a genuine, `Skill`-tool-callable skill, same mechanism `idea-explorer` already uses for `superpowers` (`Skill(skill: "impeccable", args: "shape ...")`), not a slash-command-only interface. The earlier open question is resolved.
- **Needs `Bash`.** Its frontmatter (`allowed-tools: Bash(npx impeccable *), Bash(node .claude/skills/impeccable/scripts/*)`) and its own mandatory Setup steps ("You MUST run `node .claude/skills/impeccable/scripts/context.mjs`...") mean the invoking agent needs `Bash` — `Skill` doesn't sandbox its own tool grants; the invoking agent's own tool list is what actually executes. `product-designer`'s tools now include `Bash`, scoped to this one purpose.
- **Stacked-interview risk found and designed around:** the specific sub-command `/impeccable shape` is itself a full multi-round `AskUserQuestion` discovery interview ("Design planning only... STOP and call the AskUserQuestion tool"), covering purpose/audience/content/design-direction/scope — substantially overlapping `ui-layout-spec-guide`'s own discovery dimensions. It also expects its own `PRODUCT.md` context file (unrelated to `docs/requirements/prd.md`); if absent, `shape` is one of the commands that diverts into impeccable's own from-scratch product-definition interview first. Naively invoking it in full would stack up to three interviews for one artifact.

**Resolved design: pre-fill only, not a second interview.** `product-designer` invokes `Skill(skill: "impeccable", args: "shape [ui-layout-spec scope]")` once, but treats its design-brief output purely as **pre-filled input** to `product-designer`'s own Discovery Phase — same treatment as Reference Artifact Intake's pre-fills (propose the pre-filled answer per dimension, ask the user to confirm or correct, never assume silently). It does not run as a second freestanding interview layered on top. The one-time `PRODUCT.md` bootstrap cost (if impeccable has never run in this project before) is real and is documented as an expected first-run cost, not hidden.

- Producing `ui-layout-spec.md`: check for `.claude/skills/impeccable` (via `Glob`). If present, invoke `shape` for pre-fill per above. If absent, `ABORT` **that run only** — "Impeccable is required for UI Layout Specification and isn't vendored in this project. Vendor it (see impeccable's own setup) and re-run." UX Specification and Design System runs are entirely unaffected by Impeccable's presence or absence.

### From `solution-architect`

| maestro feature | Why dropped |
|---|---|
| Automatic `PHASE HANDOFF → documentation-auditor` | No automatic handoffs. |
| Feature Status Gate / Feature Scope Resolution | Same as the other two writer agents. |
| `.codegraph/codegraph.db` + `codegraph_explore` MCP tool check (Architecture Spec drafting) | maestro-specific tooling; no MCP tool of this name exists in cairn's environment, and — unlike Impeccable — there's no "vendor it yourself" story here since this is an MCP tool binding, not a file-presence check. Dropped entirely, not adapted. |
| `.harness/architecture.md` + `harness-rules-guide` check | Same maestro-specific "harness" tooling concept, not ported. Dropped entirely. |

**Kept:**
- All 3 doc types + dependency tiers (architecture-spec → db-schema/api-spec in parallel-tier-but-sequential-in-practice, same AskUserQuestion-collision reasoning as `requirements-engineer`'s tier 3).
- **ADR Mode** — fully self-contained (own numbering via `Glob`-scan of `docs/adr/`, own skill, immutable-after-write content with status-only updates). No dependency on any un-ported agent. Kept as-is.
- `db-standards-guide` / `api-standards-guide` — technical standards loaded during Draft Phase, kept.
- `graphql-guide` — conditional load when the API surface is GraphQL, kept (self-contained skill file, no cross-agent dependency).
- **`mermaid-diagram-guide`** — loaded for `architecture-spec.md` (Architecture Diagram, Component Interactions, Deployment Model — 3 separate diagram sections) and `db-schema.md` (Entity Relationship Diagram), and explicitly required by `adr-guide` itself for ADRs. NOT loaded for `api-spec.md` (no diagrams in its template — verified, not assumed).

### From `documentation-auditor`

| maestro feature | Why dropped |
|---|---|
| Check 8 (Feature Status Consistency) | Reads `docs/project-definition/02_identity.md` — dropped along with Feature Status Gate. |
| CROSS-FEATURE VALIDATION MODE | Depends on `docs/features/*/` — dropped along with Feature Scope Resolution. |
| META AGENT SYNC MODE | Hands off to `release-manager` — not ported. |
| COMPETITOR ANALYSIS UNVERIFIED CARVE-OUT | No `competitor-analyst` output exists to carve out. |
| SYNC HANDOFF block (automated routing) | No automatic handoff — findings are reported with a "Fix" note naming which agent/mode would address them, nothing auto-invoked. |

**Check 2 (Agent Roster Accuracy) adapted:** maestro compares a README table against a `.claude/CLAUDE.md` Custom Agents table (with a `model` column). cairn's source of truth is `agents/*.md` frontmatter directly; its README lists agents as a bullet list (see `README.md` "## Agents"), no model column. Adapted: 2a completeness (every `agents/*.md` has a README bullet), 2b staleness (every README bullet names a real agent file), 2d purpose accuracy (bullet doesn't contradict frontmatter `description`). 2c (model accuracy) dropped — no column to check.

**Checks 7c-7g (architecture/API/DB/UX alignment) left defined but dormant** — no architecture/API/DB/UX docs existed before this port; now that `solution-architect` and `product-designer` are also ported, these checks become live (this is exactly the future-reuse the general-purpose scope decision was for).

### From `documentation-engineer`

| maestro feature | Why dropped |
|---|---|
| SYNC MODE (triggered by `meta-auditor`) | Not ported. |
| LEARNINGS CAPTURE MODE | Deep subsystem tied to 4 un-ported agents/commands and a `CLAUDE.md` convention cairn doesn't use. Could be its own future design. |
| Automatic `PHASE HANDOFF → documentation-auditor` | No automatic handoffs. |
| `Bash` tool | Only use was `git submodule status` inside the dropped Learnings Capture mode. |

## What's kept (behavioral summary)

### `requirements-engineer`
- Modes: Formal, Draft (3-question minimal discovery → 2-3 approaches → confirm → write, `**Draft**` callout, `v0.1-draft`, upgrade path), Update.
- 4-doc dependency chain: `project-definition.md` → `prd.md` → `user-stories.md`/`user-flows.md` (tier 3, either order, sequential — not concurrent, since both run live interviews against the same human).
- Upstream Existence Check (`TERMINATED:` if missing), one artifact per run, Discovery Phase discipline, Final Review Phase, Document Metadata block (`Derived From: User discovery interview`).

### `product-designer`
- 3-doc dependency chain: `ux-spec.md` (requires prd+user-flows) → `ui-layout-spec.md` (requires ux-spec); `design-system.md` (requires prd only, independent branch).
- Strict per-doc scope boundaries (UX = interaction only, UI Layout = structure only, Design System = visual standards only) — enforced by exit-row refusals when a user asks for the wrong layer in the wrong doc.
- Reference Artifact Intake (UI Layout Spec & Design System), Impeccable Shape Pass (UI Layout Spec only, hard-required/scoped per above).

### `solution-architect`
- Dependency tiers: `architecture-spec.md` (requires prd+user-flows) → `db-schema.md` / `api-spec.md` (both require architecture-spec, sequential in practice). ADR standalone, any time.
- Recommended-but-not-required upstream reads (ux-spec/ui-layout-spec for architecture-spec; prd/user-flows for db-schema/api-spec).
- Traceability requirement: every component/table/endpoint must trace to a requirement or user flow.

### `documentation-auditor`
- Checks 1-7 (7c-7g dormant until matching docs exist), Draft Mode Artifact Awareness, Focused Review Mode, severity tiers, `DOC-###` report format.

### `documentation-engineer`
- Create Mode (clarify-if-vague, discover existing docs, read source material, write per standard outline), Update Mode (read-first, targeted `Edit` preferred, confirm before full rewrite).

## Agents

All five: `model: opus` (consistency with `idea-explorer`'s established precedent in cairn), `Running → **[emoji] name**` completion banner (matches maestro's own convention for the two doc agents; extended to the writer trio for consistency, since none of the three originally had one in maestro).

### `agents/requirements-engineer.md`
```yaml
---
name: requirements-engineer
description: "Use this agent to produce ONE requirements artifact per invocation — Project Definition, PRD, User Stories, or User Flows — scoped to a specific project or feature. Upstream documents must exist before downstream ones (project-definition → prd → user-stories/user-flows). Tier-3 documents (user-stories, user-flows) can be produced in either order but not concurrently — each runs its own interactive discovery interview against the same human. Invoke when a user has an idea, feature request, or product goal that needs to be formally specified before implementation begins. Supports a lightweight Draft Mode for quick exploratory passes."
tools: Read, Write, Glob, AskUserQuestion
model: opus
color: purple
---
```
Banner: `Running → **🟣 requirements-engineer**`. Loads `skills/writer-shared/SKILL.md` + `skills/requirements-writing/SKILL.md` (see Skills below).

### `agents/product-designer.md`
```yaml
---
name: product-designer
description: "Use this agent to produce ONE design artifact per invocation — UX Specification, UI Layout Specification, or Design System — scoped to a specific project. Upstream documents must exist before downstream ones (prd+user-flows → ux-spec → ui-layout-spec; prd → design-system, independent branch). UI Layout Specification requires Impeccable to be vendored in the project (.claude/skills/impeccable) — aborts that run if absent; invokes it once for pre-fill input into its own discovery, not as a second interview. Invoke when requirements are documented and the user wants to define user interaction and interface structure."
tools: Read, Write, Glob, AskUserQuestion, WebFetch, Bash
model: opus
color: pink
---
```
`Bash` is scoped to one purpose: running Impeccable's own required setup scripts (`node .claude/skills/impeccable/scripts/context.mjs` etc.) when producing `ui-layout-spec.md` — Impeccable's `allowed-tools` frontmatter requires it, and `Skill` invocation doesn't grant tools the invoking agent doesn't already have. Banner: `Running → **🎨 product-designer**` (no standard "pink circle" emoji exists; picked a thematic icon, same reasoning maestro itself used for e.g. `harness-engineer`'s 🧩). Loads `skills/writer-shared/SKILL.md` + `skills/product-design-writing/SKILL.md`.

### `agents/solution-architect.md`
```yaml
---
name: solution-architect
description: "Use this agent to produce ONE technical artifact per invocation — Architecture Specification, Database Schema, API Specification, or an ADR — scoped to a specific project. Upstream documents must exist before downstream ones (prd+user-flows → architecture-spec → db-schema/api-spec). ADRs are standalone, no upstream required, immutable content after write (status-only updates). Invoke when requirements (and optionally design docs) are ready and the user wants to define system structure, data storage, or service contracts."
tools: Read, Write, Glob, AskUserQuestion
model: opus
color: yellow
---
```
Banner: `Running → **🟡 solution-architect**`. Loads `skills/writer-shared/SKILL.md` + `skills/solution-architecture-writing/SKILL.md`.

### `agents/documentation-auditor.md`
```yaml
---
name: documentation-auditor
description: "Use this agent to validate project documentation — README, setup docs, API docs, developer guides, requirements/design/architecture artifacts — for accuracy, completeness, consistency, and cross-artifact traceability. Read-only; reports findings, does not fix them. Invoke after writing or updating any documentation, or on request to audit current doc state."
tools: Read, Glob, Grep
model: opus
color: orange
---
```
Banner: `Running → **🟠 documentation-auditor**`. No skill loaded (all logic inline, matching maestro's original — it never loaded an external skill either).

### `agents/documentation-engineer.md`
```yaml
---
name: documentation-engineer
description: "Use this agent to create or update project documentation — README, setup/installation guides, API documentation, or developer guides. Discovers existing docs and source material first, follows existing conventions, asks at most one clarifying question if scope is vague. Does not write application code or touch agent/skill/command definition files."
tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
model: opus
color: green
---
```
Banner: `Running → **🟢 documentation-engineer**`. No skill loaded.

## Skills

Three writer agents now share the same underlying mechanics (discovery phase, draft phase, update mode, final review, exit rows, document metadata) — unlike the original single-agent `requirements-engineer`-only design, duplicating this across three separate skill files would drift out of sync. Restructured as:

- **`skills/writer-shared/SKILL.md`** — the shared mechanics, equivalent to maestro's `writer-agent-guide` trimmed of Feature Status Gate, Feature Scope Resolution, and the Draft Mode templates (Draft Mode is `requirements-engineer`-only, kept in its own skill instead — see below). Loaded by all three writer agents.
- **`skills/requirements-writing/SKILL.md`** — the 4 requirements doc types (discovery dimensions, artifact format, writing standards) + Draft Mode templates (Minimal Discovery, Approach Proposal, Exploratory Callout — still `requirements-engineer`-only).
- **`skills/product-design-writing/SKILL.md`** — the 3 design doc types + Reference Artifact Intake + Impeccable Shape Pass procedure. References `skills/mermaid-diagrams/SKILL.md` for `ux-spec.md` only.
- **`skills/solution-architecture-writing/SKILL.md`** — the 3 technical doc types + ADR Mode (numbering, sub-modes, immutability rule) + `db-standards-guide`/`api-standards-guide`/`graphql-guide` content merged in. References `skills/mermaid-diagrams/SKILL.md` for `architecture-spec.md`, `db-schema.md`, and ADRs — not `api-spec.md`.
- **`skills/mermaid-diagrams/SKILL.md`** — ported from `mermaid-diagram-guide` as-is (generic diagram-formatting rules, no cross-agent dependency). Loaded conditionally, per doc type, by `product-designer` and `solution-architect` — never by `requirements-engineer` (none of its 4 doc types use diagrams).

Five files total (plus none for the two doc agents, which stay skill-free like their maestro originals). Splittable further later — nothing here locks in the grouping.

## End-to-end sequence (documented order, not a `Workflow` script)

Because every writer-trio run is a live main-thread interview, this is a sequence Claude follows by invoking each agent directly (via the Agent tool or natural dispatch) one at a time — not a `Workflow`-tool script. `Workflow`'s `agent()` calls are non-interactive background subagents; they can't host an `AskUserQuestion` interview with a live human, which is a hard requirement of all three writer agents (this is maestro's own stated reason its writer trio "must run in the main conversation thread").

```
1. requirements-engineer → project-definition.md
2. requirements-engineer → prd.md
3. requirements-engineer → user-stories.md, user-flows.md   (either order, sequential)
4. documentation-auditor  → validate docs/requirements/
5. product-designer       → ux-spec.md
6. product-designer       → design-system.md                (independent of ux-spec, only needs prd.md)
7. product-designer       → ui-layout-spec.md                (requires ux-spec.md; requires impeccable vendored)
8. documentation-auditor  → validate docs/design/
9. solution-architect     → architecture-spec.md
10. solution-architect    → db-schema.md, api-spec.md        (either order, sequential)
11. documentation-auditor → validate docs/architecture/, full cross-artifact pass
```

`documentation-auditor` steps (4, 8, 11) ARE legitimate candidates for background dispatch (no `AskUserQuestion`), but running them inline in the main thread is simpler and keeps the sequence linear — no benefit to backgrounding a single quick read-only check between interview stages. This sequence is documented (in `CLAUDE.md`, and/or as its own skill or command later) as guidance for Claude to follow, not encoded as an enforced state machine — consistent with cairn's no-gates philosophy; a user can start at any stage, skip design entirely and go straight to architecture, re-run any stage, etc., same as maestro's own agents allow via their Update Mode.

## File changes

- **New:** `agents/{requirements-engineer,product-designer,solution-architect,documentation-auditor,documentation-engineer}.md`
- **New:** `skills/writer-shared/SKILL.md`
- **New:** `skills/requirements-writing/SKILL.md`
- **New:** `skills/product-design-writing/SKILL.md`
- **New:** `skills/solution-architecture-writing/SKILL.md`
- **New:** `skills/mermaid-diagrams/SKILL.md`
- **Edit:** `.claude-plugin/plugin.json` — version `0.6.0` → `0.7.0` (new user-visible agents + skills, per CLAUDE.md versioning rule)
- **Edit:** `CLAUDE.md` — add entries for all five agents to the Architecture section (scope, dependency chains, check coverage, mode coverage), the maestro-port trimming decisions above, the Impeccable hard-requirement note, and the End-to-end sequence as documented guidance
- **Edit:** `README.md` — add bullets for all five agents to "## Agents" (feeds `documentation-auditor`'s Check 2a/2b)

## Testing / verification

No unit-test equivalent exists for natural-language agents in cairn (`idea-explorer` has none either). Verify via the headless pattern CLAUDE.md documents for commands, adapted per agent:

```bash
cd /some/scratch/dir
claude -p "Produce a project definition for a simple todo app" --plugin-dir /path/to/cairn --permission-mode bypassPermissions --output-format text
```

- **`requirements-engineer`:** tier-1 doc with no upstream (proceeds), tier-2/3 doc with no upstream (`TERMINATED`), Draft Mode trigger. Inspect `docs/requirements/*.md`.
- **`product-designer`:** `ux-spec.md` with `prd.md`+`user-flows.md` present; `ui-layout-spec.md` with `.claude/skills/impeccable` absent (confirm scoped `ABORT`, not a full-agent failure — `design-system.md` should still work in the same project); Reference Artifact Intake with a local file path; `ui-layout-spec.md` with impeccable present (confirm `shape`'s output pre-fills discovery dimensions rather than running as a second full interview — the specific regression to watch for).
- **`solution-architect`:** `architecture-spec.md` with upstream present (confirm the 3 Mermaid diagram sections are actually populated, not left as placeholders); ADR Mode new-decision flow (confirm numbering starts at `0001` in an empty `docs/adr/`, and that a Mermaid diagram is included per `adr-guide`); status-update flow on an existing ADR (confirm content is untouched, only `## Status` changes); `api-spec.md` (confirm no diagram-loading step fires — it shouldn't need one).
- **`documentation-auditor`:** PRD with an untraced `FR-001` → confirm `HIGH` Check 7a finding; stale README referencing a nonexistent file → confirm Check 3 finding; run after `solution-architect`/`product-designer` produce docs to confirm Checks 7c-7g go live (no longer permanently dormant).
- **`documentation-engineer`:** Create Mode on a scratch project with no README; Update Mode on an existing README with one stale section (confirm targeted `Edit`, not full rewrite, absent explicit confirmation).

## Open questions

None outstanding. The one open item from the previous draft — Impeccable's invocation mechanism — was verified against the real vendored skill (`~/Projects/maestro/.claude/skills/impeccable/SKILL.md`): it's `Skill`-tool-callable (`user-invocable: true`), requires `Bash` in the invoking agent's tools, and its `shape` sub-command runs its own discovery interview — resolved as a pre-fill-only integration (see Impeccable section above), not a second freestanding interview.
