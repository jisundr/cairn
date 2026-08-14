# Design: Port `requirements-engineer`, `documentation-auditor`, `documentation-engineer` from maestro into cairn

## Summary

Port three maestro agents into cairn: `requirements-engineer` (writes requirements docs), `documentation-auditor` (validates docs generally — README/setup/API/dev-guides plus requirements cross-artifact traceability), and `documentation-engineer` (writes README/setup/API/dev-guide docs). All three are self-contained and terminal — no automatic cross-agent handoffs — but keep their real maestro names and general-purpose scope so they're reusable for future cairn doc work, not narrowed to only this one use case. This is the first multi-agent-plus-skill port from maestro into cairn, and the first entries in cairn's `skills/` directory (currently empty).

## Source

- `~/Projects/maestro/.claude/agents/requirements-engineer.md`
- `~/Projects/maestro/.claude/agents/documentation-auditor.md`
- `~/Projects/maestro/.claude/agents/documentation-engineer.md`
- `~/Projects/maestro/.claude/skills/writer-agent-guide/SKILL.md`
- `~/Projects/maestro/.claude/skills/{project-definition,prd,user-stories,user-flows}-guide/SKILL.md`

## Scope decision

maestro is a fully workflow-bound agentic framework: 19 agents wired into one mesh via `intent-analyzer` (central router, references all 19) and hub agents like `documentation-auditor` (references `product-designer`, `solution-architect`, `documentation-engineer`, `meta-engineer`, `release-manager`, `competitor-analyst`) and `documentation-engineer` (references `gitlab-mr-reviewer`, `meta-engineer`, `meta-auditor`, `release-manager`, `task-orchestrator` via its Sync and Learnings Capture modes). Porting any one of these agents at face value pulls in that entire mesh.

cairn's design is the opposite: no fixed agent roster, self-contained agents (`idea-explorer` has exactly one hard external dependency — `superpowers:brainstorming` — and aborts rather than reimplement methodology it doesn't own). Recreating the full mesh would mean forking maestro's entire architecture into cairn, a different, much larger project.

**Decision: port three agents, each self-contained:**
- `requirements-engineer` — full scope kept (it was already the least coupled of the three; its only external reach was the auditor handoff).
- `documentation-auditor` — kept at full general-purpose breadth (Checks 1-7, all doc types), since these two agents are meant to be reusable in future cairn doc workflows, not just this one. Only the checks/modes that key off un-ported agents or maestro-only conventions are dropped.
- `documentation-engineer` — kept at full Create/Update-mode breadth (README, setup, API docs, developer guides). Sync Mode (triggered by `meta-auditor`) and Learnings Capture Mode (tied to `meta-engineer`/`gitlab-mr-reviewer`/`task-orchestrator`/`/sync-framework` checkpoints, and to a `## Learnings` `CLAUDE.md` convention maestro-specific enough to be its own separate concern) are dropped — both are deep, unrelated subsystems, not writing-docs machinery.

**No automatic handoffs.** All three stay terminal after their own work — matches cairn's no-gates philosophy and `idea-explorer`'s precedent. `requirements-engineer` and `documentation-engineer` don't auto-invoke `documentation-auditor` after writing; running the auditor is a separate, deliberate step (by the user, or by Claude choosing to dispatch it).

## What's dropped and why

### From `requirements-engineer`

| maestro feature | Why dropped |
|---|---|
| Automatic `PHASE HANDOFF → documentation-auditor` | `documentation-auditor` IS being ported, but as a separately-dispatched agent, not an automatic post-write handoff (see "No automatic handoffs" above). |
| Feature Status Gate (reads `docs/project-definition/02_identity.md` Section 4) | Keyed to a maestro-wide feature-status tracking file cairn has no counterpart for. |
| Feature Scope Resolution / feature-scoped output paths (`docs/features/<name>/requirements/`) | Keyed to a `Feature Scope:` field maestro's own `intent-analyzer` injects into opening context; cairn's `intent-analyzer` has no such field. Flat paths only. |
| Optional Competitive Input (reads `competitor-analyst` snapshots) | `competitor-analyst` isn't being ported; this was optional/presence-gated in maestro too, so dropping it changes nothing structurally. |
| ClickUp exit row (defers to `project-manager`) | `project-manager` isn't being ported. |
| `mermaid-diagram-guide` load step in Draft Phase | None of the 4 artifact templates use diagrams (Scope & Boundaries explicitly forbids them; none of the other sections call for one). Dead weight for this agent. |
| Adaptive Output Rule (single-file vs numbered multi-file split) | None of the 4 doc-type guides define a Split Condition — all four are always single-file. |
| "Scope & Boundaries" 4-status-table section (Implemented / Current / Pending Review ×2) in Project Definition & PRD templates | Artifact-side half of the Feature Status Gate mechanic, dropped along with the gate. `project-definition.md` already has Goals/Non-Goals and `prd.md` already has an Out of Scope list — same need, no dead machinery. |

### From `documentation-auditor`

| maestro feature | Why dropped |
|---|---|
| Check 8 (Feature Status Consistency) | Reads `docs/project-definition/02_identity.md` — dropped along with Feature Status Gate. |
| CROSS-FEATURE VALIDATION MODE | Depends on `docs/features/*/` — dropped along with Feature Scope Resolution. |
| META AGENT SYNC MODE | Hands off to `release-manager` — not ported. |
| COMPETITOR ANALYSIS UNVERIFIED CARVE-OUT | No `competitor-analyst` output exists to carve out. |
| SYNC HANDOFF block (automated routing to responsible agent) | No automatic handoff — findings are reported with a "Fix" note naming which agent/mode would address them, but nothing is auto-invoked. |
| Check 7c/7d/7e/7f/7g (architecture/API/DB/UX alignment) sub-checks | No architecture/API/DB/UX-producing agents exist in cairn yet. Left defined but structurally dormant (they simply never find matching docs to check) rather than deleted — this is exactly the kind of future-reuse the general-purpose scope decision was for. |
| `meta-auditor` cross-reference (".claude/ is meta-auditor's scope") | No `meta-auditor` ported; note dropped as moot. |

**Check 2 (Agent Roster Accuracy) adapted, not dropped:** maestro's version compares a README table against a `.claude/CLAUDE.md` Custom Agents table (including a per-agent `model` column). cairn has no such registry — its source of truth is `agents/*.md` frontmatter directly, and its README lists agents as a bullet list (see `README.md` "## Agents"), not a table, with no model column. Adapted checks:
- **2a Completeness:** every agent file in `agents/*.md` must have a corresponding bullet in README's "## Agents" section.
- **2b Staleness:** every agent named in README's bullet list must exist as a file in `agents/`.
- **2d Purpose accuracy:** the README bullet's description must not contradict the agent file's frontmatter `description`.
- **2c Model accuracy dropped** — cairn's README doesn't surface a per-agent model column to check against.

### From `documentation-engineer`

| maestro feature | Why dropped |
|---|---|
| SYNC MODE (triggered by `PHASE HANDOFF` from `meta-auditor`) | `meta-auditor` and the meta-engineering workflow it syncs from aren't ported. |
| LEARNINGS CAPTURE MODE (writes `## Learnings` sections, dedup/cap rules, wrap-up offers at `/sync-framework`/`task-orchestrator`/`gitlab-mr-reviewer` checkpoints, annotation entries from `meta-engineer`) | A deep, separate subsystem tied to four un-ported agents/commands and a `CLAUDE.md` convention cairn doesn't use. Out of scope for a docs-writing port; could be its own future design if cairn wants a learnings-capture feature. |
| Automatic `PHASE HANDOFF → documentation-auditor` after Create/Update | Same no-automatic-handoffs decision as `requirements-engineer`. |
| `Bash` tool | Its only use in maestro's version was `git submodule status` inside Learnings Capture mode, which is dropped. Not needed for Create/Update modes. |

## What's kept

### `requirements-engineer`
- **Modes:** Formal (default, full discovery), Draft (`DRAFT REQUEST` prefix or explicit draft/explore language; 3-question minimal discovery → 2-3 approaches with recommendation → confirm → write), Update (existing doc → targeted re-interview on in-scope sections only).
- **4-document dependency chain**, entirely internal to this one agent:
  ```
  project-definition.md (tier 1, no upstream)
     → prd.md (tier 2, requires project-definition.md)
        → user-stories.md (tier 3, requires prd.md)
        → user-flows.md  (tier 3, requires prd.md)
  ```
  Tier 3 documents (`user-stories.md`, `user-flows.md`) don't depend on each other, so either can be produced first — but not concurrently. Each runs an `AskUserQuestion`-driven discovery interview against the same human; two instances in parallel would mean two simultaneous interview threads competing for the same person's attention. Unlike maestro (which assumes independently-interviewable concurrent instances), cairn's port is strictly sequential — one artifact, one interview, start to finish, before the next.
- **Upstream Existence Check** — refuse (`TERMINATED: ...`) if the required upstream doc is missing.
- **One artifact per run** — hard rule, refuse multi-artifact requests. (Wording changed from maestro's "launch separate instances" suggestion, which implied parallelism — now: "Complete this one, then invoke it again for the next.")
- **Discovery Phase discipline** — one question at a time via `AskUserQuestion`, suggestions labeled as examples never auto-accepted, no drafting during discovery, explicit "I have enough information to draft the [document type]" checkpoint.
- **Final Review Phase** — after `Write`, ask "Happy with the changes?" (Yes → done; No → revise and re-write) via `AskUserQuestion`.
- **Draft-to-formal upgrade path** — a doc carrying the `**Draft**` callout, re-run without a draft trigger, gets the callout stripped and version bumped one full minor past where a from-scratch formal doc would start.
- **Document metadata block** (version, Last Updated, Derived From, Author/LLM Model, Reviewed By) — `Derived From` simplified to "User discovery interview" (no upstream agent chain to cite).

### `documentation-auditor`
- Checks 1 (Existence/Coverage, both agentic-project and requirements-doc rules), 2 (Agent Roster, adapted per above), 3 (Accuracy Against Source), 4 (Completeness), 5 (Internal Consistency), 6 (Style/Formatting), 7a/7b (requirements traceability — active) and 7c-7g (dormant until matching doc-producing agents exist).
- DRAFT MODE ARTIFACT AWARENESS — downgrades completeness-type findings to `INFO` for docs carrying the `**Draft**` callout.
- FOCUSED REVIEW MODE — audit a single specified document rather than the whole set.
- Findings classification tiers (CRITICAL/HIGH/MEDIUM/LOW/INFO) and the AUDIT REPORT format (finding counts table + `DOC-###` detail blocks).
- Read-only — never writes or modifies files.

### `documentation-engineer`
- **Create Mode** — clarify scope if vague (one question via `AskUserQuestion`), discover existing docs, read related source material, write following project conventions. Standard outlines for README / Setup Guide / API Documentation / Developer Guide.
- **Update Mode** — always read the target file first; targeted `Edit` preferred, full `Write` rewrite only with explicit user confirmation for substantial existing content.
- Hard requirements: never touch `.claude/`-equivalent files (n/a in cairn, but keep the boundary as "never touch agent/skill/command definition files" — this agent writes human-facing docs only, not `agents/`/`skills/`/`commands/`), never write application code, always read before modifying, never invent content, Result block mandatory.

## Agent: `agents/requirements-engineer.md`

```yaml
---
name: requirements-engineer
description: "Use this agent to produce ONE requirements artifact per invocation — Project Definition, PRD, User Stories, or User Flows — scoped to a specific project or feature. Upstream documents must exist before downstream ones (project-definition → prd → user-stories/user-flows). Tier-3 documents (user-stories, user-flows) can be produced in either order but not concurrently — each runs its own interactive discovery interview against the same human. Invoke when a user has an idea, feature request, or product goal that needs to be formally specified before implementation begins. Supports a lightweight Draft Mode for quick exploratory passes (triggered by 'draft'/'quick draft'/'explore' language) alongside the full formal discovery flow."
tools: Read, Write, Glob, AskUserQuestion
model: opus
color: purple
---
```

Body carries (trimmed per the tables above, merged from maestro's agent file + the shared `writer-agent-guide` sections it actually uses):
- SYSTEM ROLE — Requirements Engineer, requirements-only scope, no architecture/design/code
- WORKFLOW INTENT — dependency tiers, tier-3 either-order-but-sequential note, Formal/Draft/Update mode table
- HARD REQUIREMENTS — one artifact/run, upstream-must-exist, requirements-only, no partial drafts, no file writes without confirmation, testable acceptance criteria, load doc skill before discovery, flat output path only
- DOCUMENT MODE DETECTION — identify target doc type from request; `AskUserQuestion` if ambiguous
- DRAFT MODE trigger detection, minimal discovery, approach proposal, exploratory callout, draft-to-formal upgrade
- DEPENDENCY CHAIN table + Update mode note
- UPSTREAM EXISTENCE CHECK
- SKILL LOADING — loads `skills/requirements-writing/SKILL.md`, target-doc-type section
- DISCOVERY PHASE
- DRAFT PHASE (Write tool) — no mermaid step
- FINAL REVIEW PHASE
- **COMPLETION** (replaces PHASE HANDOFF — terminal). Matches maestro's `Running → **[emoji] agent-name**` banner convention — same shape `idea-explorer` already uses in cairn:
  ```
  Running → **🟣 requirements-engineer**

  REQUIREMENTS ARTIFACT COMPLETE

  Document   → [Project Definition | PRD | User Stories | User Flows]
  Written to → docs/requirements/[doc].md
  Mode       → Formal | Draft | Update

  Result
    Status  → ✅ COMPLETE
    Flags   → [Draft Mode — supersedes with a full formal run | upgraded from draft to formal | none]
  ```
- EXIT & DERAILMENT HANDLING — the four generic rows (upstream missing, multi-artifact request, skip-discovery, session-abandoned) plus: architecture/design/code request → refuse, scope is requirements only; finalize-without-testable-criteria → ask one more question. ClickUp row dropped.
- START — numbered sequence mirroring the phases above, minus Feature Status Gate / Feature Scope Resolution / Competitive Input steps.

## Skill: `skills/requirements-writing/SKILL.md`

One file (splittable later — nothing here locks in a merge). Merges:
- From `writer-agent-guide`: Suggestion Assistance Rule, Shared Enforcement Rules, Document Metadata template (simplified `Derived From`), Discovery Phase shared rules, Upstream Existence Check procedure, Discovery Phase full flow, Draft Phase write-tool steps (mermaid step removed), Minimal Discovery + Approach Proposal templates (Draft Mode), Exploratory Callout template, Final Review Phase template, Update Mode shared steps, generic exit rows.
- From the 4 doc guides: discovery dimensions, artifact format (Scope & Boundaries table removed from `project-definition` and `prd` templates), writing standards — one section per doc type, selected by the agent at Skill Loading time based on target document.

`documentation-auditor` and `documentation-engineer` load no external skill — same as their maestro originals, all logic is inline in the agent file.

## Agent: `agents/documentation-auditor.md`

```yaml
---
name: documentation-auditor
description: "Use this agent to validate project documentation — README, setup docs, API docs, developer guides, and requirements artifacts (docs/requirements/) — for accuracy, completeness, consistency, and cross-artifact traceability. Read-only; reports findings, does not fix them. Invoke after writing or updating any documentation, or on request to audit current doc state (e.g. 'does the README still match the code', 'check the PRD and user stories are consistent')."
tools: Read, Glob, Grep
model: opus
color: orange
---
```

Body: SYSTEM ROLE (read-only validator, project documentation broadly) → VALIDATION CHECKS 1-7 (as scoped above — 7c-7g dormant-but-defined) → DRAFT MODE ARTIFACT AWARENESS → FOCUSED REVIEW MODE → FINDINGS CLASSIFICATION → AUDIT REPORT FORMAT (finding-counts table + `DOC-###` blocks, each finding's "Fix" line names the agent+mode that would address it — informational only) → COMPLETION (terminal, `Running → **🟠 documentation-auditor**` banner, `Result` block with finding counts by severity — no SYNC HANDOFF) → EXIT & DERAILMENT HANDLING (file unreadable, no docs found, user asks it to fix issues → "My role is validation only; the Fix note on each finding names which agent to re-run.").

**Agent-routing reference (informational, used only in Fix text — not auto-invoked):**

| Artifact | Agent to re-run |
|---|---|
| `docs/requirements/*.md` | `requirements-engineer` |
| `README.md`, setup docs, API docs, developer guides | `documentation-engineer` |

## Agent: `agents/documentation-engineer.md`

```yaml
---
name: documentation-engineer
description: "Use this agent to create or update project documentation — README, setup/installation guides, API documentation, or developer guides. Discovers existing docs and source material first, follows the project's existing conventions, and asks at most one clarifying question if scope is vague. Does not write application code or touch agent/skill/command definition files."
tools: Read, Write, Edit, Glob, Grep, AskUserQuestion
model: opus
color: green
---
```

Body: SYSTEM ROLE (documentation only, no app code, no agent/skill/command files) → CREATE MODE WORKFLOW (clarify scope if vague → discover existing docs → read related source → write, per standard outlines for README/Setup/API/Developer Guide) → UPDATE MODE WORKFLOW (read target → identify targeted-edit vs full-rewrite → apply, confirm before full rewrites) → COMPLETION (terminal, `Running → **🟢 documentation-engineer**` banner + `Result` block: Status, Mode, Created/Updated file list) → EXIT & DERAILMENT HANDLING (source files don't exist yet → placeholder callout noting the gap; nothing needs updating → say so explicitly).

## Optional composition via Workflow (not built now)

"No automatic handoff" means the *agents* never decide to chain themselves — that decision is deliberately kept out of `agents/*.md` and `skills/requirements-writing/SKILL.md` entirely, so each stays a pure, single-purpose, independently-testable unit (consistent with the "terminal, no fixed roster" decision above).

Where a maestro-style pipeline is actually wanted for a given task, it belongs in an external `Workflow` script instead — e.g. `pipeline([docType], d => agent(..., {agentType: 'requirements-engineer'}), r => agent(..., {agentType: 'documentation-auditor'}))` — composing the already-ported agents from outside, on demand, per cairn's existing `Workflow` tool. This gets the orchestration maestro's `PHASE HANDOFF` provided, without hardcoding it into the agents, and without requiring every invocation to pay for it (workflows are explicit opt-in, per-session).

Not part of this port's file changes — no workflow script is being authored now. Noted here as the documented extension point so a future `docs/superpowers/specs/*-requirements-pipeline-workflow.md` (or similar) has a clear starting point rather than reopening this design.

## File changes

- **New:** `agents/requirements-engineer.md`
- **New:** `agents/documentation-auditor.md`
- **New:** `agents/documentation-engineer.md`
- **New:** `skills/requirements-writing/SKILL.md`
- **Edit:** `.claude-plugin/plugin.json` — version `0.6.0` → `0.7.0` (new user-visible agents + skill, per CLAUDE.md versioning rule)
- **Edit:** `CLAUDE.md` — add entries for all three agents to the Architecture section: scope, dependency chain (`requirements-engineer`), check coverage (`documentation-auditor`), mode coverage (`documentation-engineer`), and the maestro-port trimming decisions above (so future edits don't accidentally reintroduce dropped coupling — e.g. re-adding an automatic handoff, or Sync/Learnings-Capture modes)
- **Edit:** `README.md` — add bullets for all three agents to "## Agents" (feeds `documentation-auditor`'s own Check 2a/2b — should stay in sync with `agents/*.md`)

## Testing / verification

No unit-test equivalent exists for natural-language agents in cairn (`idea-explorer` has none either). Verify via the same headless pattern CLAUDE.md documents for commands, adapted for an agent:

```bash
cd /some/scratch/dir
claude -p "Produce a project definition for a simple todo app" --plugin-dir /path/to/cairn --permission-mode bypassPermissions --output-format text
```

- **`requirements-engineer`:** run once for the tier-1 doc (project-definition, no upstream — should proceed straight to discovery), once for a tier-2/3 doc with no upstream present (should `TERMINATED`), once for a Draft Mode trigger. Inspect `docs/requirements/*.md` output, not just the reported text.
- **`documentation-auditor`:** produce a PRD with an `FR-001` that has no corresponding user story, run the auditor, confirm a `HIGH` traceability finding with correct `DOC-###` format; produce the missing story, confirm a clean re-run. Separately, run it against a scratch project with a stale README (references a nonexistent file) and confirm a Check 3 finding.
- **`documentation-engineer`:** run Create Mode against a scratch project with no README and confirm it writes one following the standard outline; run Update Mode against an existing README with a stale section and confirm only that section changes (targeted `Edit`, not a full rewrite, absent explicit confirmation).

## Open questions

None outstanding — all scope, naming, model, and skill-structure decisions were resolved during brainstorming above.
