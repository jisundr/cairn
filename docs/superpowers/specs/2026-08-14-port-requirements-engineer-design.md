# Design: Port `requirements-engineer` + `requirements-auditor` from maestro into cairn

## Summary

Port maestro's `requirements-engineer` agent into cairn, plus a second, trimmed `requirements-auditor` agent covering the one slice of `documentation-auditor` that's actually relevant to requirements docs (cross-artifact traceability). Both are self-contained — no cross-agent auto-handoffs, no fixed-roster dependencies. This is the first agent-plus-skill port from maestro into cairn, and the first entries in cairn's `skills/` directory (currently empty).

## Source

- `~/Projects/maestro/.claude/agents/requirements-engineer.md`
- `~/Projects/maestro/.claude/agents/documentation-auditor.md` (trimmed — see `requirements-auditor` below)
- `~/Projects/maestro/.claude/skills/writer-agent-guide/SKILL.md`
- `~/Projects/maestro/.claude/skills/{project-definition,prd,user-stories,user-flows}-guide/SKILL.md`

## Scope decision

maestro is a fully workflow-bound agentic framework: 19 agents wired into one mesh via `intent-analyzer` (central router, references all 19) and hub agents like `documentation-auditor` (references `product-designer`, `solution-architect`, `documentation-engineer`, `meta-engineer`, `release-manager`, `competitor-analyst`). `requirements-engineer` alone pulls in that entire mesh through its `PHASE HANDOFF → documentation-auditor` step.

cairn's design is the opposite: no fixed agent roster, self-contained agents (`idea-explorer` has exactly one hard external dependency — `superpowers:brainstorming` — and aborts rather than reimplement methodology it doesn't own). Recreating the full mesh would mean forking maestro's entire architecture into cairn, which is a different, much larger project and structurally contradicts cairn's design.

**Decision: port `requirements-engineer` alone**, self-contained, keeping its own internal 4-document dependency chain (that's local to this one agent, not a cross-agent dependency) and its Draft Mode (also fully internal — no other agent involved). Drop everything that reaches for another maestro agent or a maestro-only convention cairn has no counterpart for.

## What's dropped and why

| maestro feature | Why dropped |
|---|---|
| Automatic `PHASE HANDOFF → documentation-auditor` | `requirements-auditor` (below) IS being ported, but as a separately-dispatched agent, not an automatic post-write handoff — matches cairn's no-gates philosophy. `requirements-engineer` stays terminal; running the auditor afterward is optional, at the user's (or Claude's) discretion. |
| Feature Status Gate (reads `docs/project-definition/02_identity.md` Section 4) | Keyed to a maestro-wide feature-status tracking file cairn has no counterpart for. |
| Feature Scope Resolution / feature-scoped output paths (`docs/features/<name>/requirements/`) | Keyed to a `Feature Scope:` field maestro's own `intent-analyzer` injects into opening context; cairn's `intent-analyzer` has no such field. Flat paths only. |
| Optional Competitive Input (reads `competitor-analyst` snapshots) | `competitor-analyst` isn't being ported; this was optional/presence-gated in maestro too, so dropping it changes nothing structurally. |
| ClickUp exit row (defers to `project-manager`) | `project-manager` isn't being ported. |
| `mermaid-diagram-guide` load step in Draft Phase | None of the 4 artifact templates use diagrams (Scope & Boundaries explicitly forbids them; none of the other sections call for one). Dead weight for this agent. |
| Adaptive Output Rule (single-file vs numbered multi-file split) | None of the 4 doc-type guides define a Split Condition — all four are always single-file. This machinery exists in `writer-agent-guide` for other maestro writer agents (e.g. architecture docs), not for these four. |
| "Scope & Boundaries" 4-status-table section (Implemented / Current / Pending Review ×2) in Project Definition & PRD templates | This table is the artifact-side half of the Feature Status Gate mechanic — it only gets populated/maintained by that gate, which is dropped. Kept without the gate it'd just be a permanently-stub section. `project-definition.md` already has Goals/Non-Goals and `prd.md` already has an Out of Scope list — those cover the same "what's in/out" need without the dead machinery. |

## What's kept

- **Modes:** Formal (default, full discovery), Draft (`DRAFT REQUEST` prefix or explicit draft/explore language; 3-question minimal discovery → 2-3 approaches with recommendation → confirm → write), Update (existing doc → targeted re-interview on in-scope sections only).
- **4-document dependency chain**, entirely internal to this one agent:
  ```
  project-definition.md (tier 1, no upstream)
     → prd.md (tier 2, requires project-definition.md)
        → user-stories.md (tier 3, requires prd.md)
        → user-flows.md  (tier 3, requires prd.md)
  ```
  Tier 3 documents (`user-stories.md`, `user-flows.md`) don't depend on each other, so either can be produced first — but not concurrently. Each runs a `AskUserQuestion`-driven discovery interview against the same human; two instances in parallel would mean two simultaneous interview threads competing for the same person's attention. Unlike maestro (which assumes independently-interviewable concurrent instances), cairn's port is strictly sequential — one artifact, one interview, start to finish, before the next.
- **Upstream Existence Check** — refuse (`TERMINATED: ...`) if the required upstream doc is missing.
- **One artifact per run** — hard rule, refuse multi-artifact requests.
- **Discovery Phase discipline** — one question at a time via `AskUserQuestion`, suggestions labeled as examples never auto-accepted, no drafting during discovery, explicit "I have enough information to draft the [document type]" checkpoint.
- **Final Review Phase** — after `Write`, ask "Happy with the changes?" (Yes → done; No → revise and re-write) via `AskUserQuestion`.
- **Draft-to-formal upgrade path** — a doc carrying the `**Draft**` callout, re-run without a draft trigger, gets the callout stripped and version bumped one full minor past where a from-scratch formal doc would start (documents the draft revision as real history).
- **Document metadata block** (version, Last Updated, Derived From, Author/LLM Model, Reviewed By) — same shared template, `Derived From` simplified to just "User discovery interview" (drops maestro's agent-pipeline provenance language since there's no upstream agent chain).

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

`color: purple` matches maestro's original. Pairs with a `🟣` banner emoji (see COMPLETION below) — the colored-circle convention maestro already uses for several agents (`documentation-auditor` 🟠, `meta-auditor` 🔴, `meta-engineer` 🔵, `documentation-engineer` 🟢).

Body carries (trimmed per the table above, merged from maestro's agent file + the shared `writer-agent-guide` sections it actually uses):
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
- **COMPLETION** (replaces PHASE HANDOFF — terminal, no agent to hand off to). Matches maestro's `Running → **[emoji] agent-name**` banner convention — same shape `idea-explorer` already uses in cairn (banner, then a short key→value summary, then a `Result` block):
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
- EXIT & DERAILMENT HANDLING — the four generic rows (upstream missing, multi-artifact request, skip-discovery, session-abandoned) plus: architecture/design/code request → refuse, scope is requirements only; finalize-without-testable-criteria → ask one more question. ClickUp row dropped (no `project-manager`). Multi-artifact-request row's wording changed: maestro's original suggests "launch separate instances" to parallelize — dropped per the sequential-only decision above; response becomes "This agent produces one requirements artifact per run. Complete this one, then invoke it again for the next."
- START — numbered sequence mirroring the phases above, minus Feature Status Gate / Feature Scope Resolution / Competitive Input steps.

## Skill: `skills/requirements-writing/SKILL.md`

One file (splittable later — nothing here locks in a merge). Merges:
- From `writer-agent-guide`: Suggestion Assistance Rule, Shared Enforcement Rules, Document Metadata template (simplified `Derived From`), Discovery Phase shared rules, Upstream Existence Check procedure, Discovery Phase full flow, Draft Phase write-tool steps (mermaid step removed), Minimal Discovery + Approach Proposal templates (Draft Mode), Exploratory Callout template, Final Review Phase template, Update Mode shared steps, generic exit rows.
- From the 4 doc guides: discovery dimensions, artifact format (Scope & Boundaries table removed from `project-definition` and `prd` templates per the table above), writing standards — one section per doc type, selected by the agent at Skill Loading time based on target document.

## Agent: `agents/requirements-auditor.md`

Trimmed from maestro's `documentation-auditor`. Only the slice relevant to a requirements-only port survives.

**Dropped from `documentation-auditor`:**

| maestro feature | Why dropped |
|---|---|
| Check 2 (Agent Roster Accuracy) | About README vs `.claude/CLAUDE.md` agent listings — unrelated to requirements docs. |
| Check 3 (Setup/README accuracy against source), Check 4 (README/setup/API completeness), Check 6 (style/formatting) | All about README/setup/API docs — that's `documentation-engineer`'s territory, not ported (see doc-sync discussion above). |
| Check 7c/7d/7e/7f/7g (architecture/API/DB/UX alignment) | No architecture/API/DB/UX-producing agents exist in cairn to check against. |
| Check 8 (Feature Status Consistency) | Reads `docs/project-definition/02_identity.md` — dropped along with Feature Status Gate in `requirements-engineer`. |
| CROSS-FEATURE VALIDATION MODE | Depends on `docs/features/*/` — dropped along with Feature Scope Resolution. |
| META AGENT SYNC MODE | Hands off to `release-manager` — not ported. |
| COMPETITOR ANALYSIS UNVERIFIED CARVE-OUT | No `competitor-analyst` output exists to carve out. |
| SYNC HANDOFF block / agent-routing table | No automatic handoff (see above) — findings are reported, not routed. |
| `.claude/`-scope exclusion note, `meta-auditor` cross-reference | Meta-agent concerns, not applicable. |

**Kept:**
- Check 1 (Existence/Coverage), narrowed to requirements docs only: downstream doc exists without its required upstream → `HIGH`.
- Check 7a (PRD → user-stories traceability: every `FR-###` has a corresponding story) and 7b (user-flows → user-stories coverage: every flow has a corresponding story).
- DRAFT MODE ARTIFACT AWARENESS — downgrades Check 1/7 completeness-type findings to `INFO` for docs carrying the `**Draft**` callout.
- FOCUSED REVIEW MODE — audit a single specified document rather than the whole set.
- Findings classification tiers (CRITICAL/HIGH/MEDIUM/LOW/INFO) and the AUDIT REPORT format (finding counts table + `DOC-###` detail blocks).
- Read-only — never writes or modifies files.

```yaml
---
name: requirements-auditor
description: "Use this agent to validate cross-artifact consistency across docs/requirements/ — checking that PRD functional requirements trace to user stories, and user flows trace to user stories. Read-only; reports findings, does not fix them. Invoke after updating any requirements doc, or on request to check whether the requirements set is internally consistent."
tools: Read, Glob, Grep
model: opus
color: orange
---
```

Body: SYSTEM ROLE (read-only validator) → VALIDATION CHECKS (Check 1 + 7a/7b as scoped above) → DRAFT MODE ARTIFACT AWARENESS → FOCUSED REVIEW MODE → FINDINGS CLASSIFICATION → AUDIT REPORT FORMAT → COMPLETION (terminal, same `Running → **🟠 requirements-auditor**` banner convention, `Result` block lists finding counts by severity — no SYNC HANDOFF, no agent routing) → EXIT & DERAILMENT HANDLING (file unreadable, no requirements docs found, user asks it to fix issues → "My role is validation only; re-run requirements-engineer in Update Mode for the flagged doc.").

## File changes

- **New:** `agents/requirements-engineer.md`
- **New:** `agents/requirements-auditor.md`
- **New:** `skills/requirements-writing/SKILL.md`
- **Edit:** `.claude-plugin/plugin.json` — version `0.6.0` → `0.7.0` (new user-visible agents + skill, per CLAUDE.md versioning rule)
- **Edit:** `CLAUDE.md` — add `requirements-engineer` and `requirements-auditor` entries to the Architecture section describing scope, dependency chain, output location, and the maestro-port trimming decisions above (so future edits don't accidentally reintroduce dropped coupling)

## Testing / verification

No unit-test equivalent exists for natural-language agents in cairn (`idea-explorer` has none either). Verify via the same headless pattern CLAUDE.md documents for commands, adapted for an agent:

```bash
cd /some/scratch/dir
claude -p "Produce a project definition for a simple todo app" --plugin-dir /path/to/cairn --permission-mode bypassPermissions --output-format text
```

Run once for the tier-1 doc (project-definition, no upstream — should proceed straight to discovery), once for a tier-2/3 doc with no upstream present (should `TERMINATED`), and once for a Draft Mode trigger. Inspect the scratch directory's `docs/requirements/*.md` output, not just the reported text.

For `requirements-auditor`: produce a PRD with an `FR-001` that has no corresponding user story, then run the auditor against `docs/requirements/` and confirm it reports a `HIGH` traceability finding with the right `DOC-###` format — then produce the missing story and confirm a clean re-run.

## Open questions

None outstanding — all scope, naming, model, and skill-structure decisions were resolved during brainstorming above.
