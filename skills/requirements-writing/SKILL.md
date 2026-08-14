---
name: requirements-writing
description: Discovery dimensions, artifact formats, and Draft Mode templates for the 4 requirements documents (project-definition, prd, user-stories, user-flows). Loaded by requirements-engineer alongside writer-shared.
---

# Requirements Writing

Loaded by `requirements-engineer` for all 4 requirements document types, alongside `writer-shared` (general discovery/draft/update mechanics).

None of these 4 document types require Mermaid diagrams — do not load `skills/mermaid-diagrams/SKILL.md` for any of them (verified directly against each template below; this differs from `product-design-writing` and `solution-architecture-writing`, which do load it for specific doc types).

---

## Dependency Chain

| Document | Required Upstream |
|---|---|
| `project-definition.md` | None (origin document) |
| `prd.md` | `docs/requirements/project-definition.md` |
| `user-stories.md` | `docs/requirements/prd.md` |
| `user-flows.md` | `docs/requirements/prd.md` |

`user-stories.md` and `user-flows.md` don't depend on each other — either may be produced first, but not concurrently (both run a live interview against the same human).

---

## `project-definition.md`

**Output path:** `docs/requirements/project-definition.md`

**Discovery Dimensions** (ask ONE at a time, cover all 5 before drafting):
1. What is the project and what problem does it solve?
2. Who are the stakeholders and users?
3. What does success look like at a strategic level?
4. What is explicitly out of scope?
5. What are the known constraints, assumptions, or risks?

**Artifact format:**

```markdown
# Project Definition: [Project Name]

## Metadata
- Project Definition Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: User discovery interview
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## Overview
[What this project is and why it exists — 1-3 sentences]

## Goals
- [Goal 1]
- [Goal 2]

## Non-Goals
- [Explicit exclusion 1]
- [Explicit exclusion 2]

## Stakeholders
| Stakeholder | Role | Interest |
|---|---|---|

## Constraints
- [Known constraint that bounds the solution]

## Assumptions & Risks
- [Assumption or risk]

## Open Questions
- [Unresolved item requiring a decision]
```

---

## `prd.md`

**Output path:** `docs/requirements/prd.md`

**Discovery Dimensions** (ask ONE at a time, cover all 5 before drafting):
1. Who are the user personas and what are their primary goals?
2. What are the core functional requirements? (FR-001, FR-002, ...)
3. What are the non-functional requirements (performance, security, accessibility)?
4. What is explicitly out of scope for this PRD?
5. What open questions remain unresolved?

**Artifact format:**

```markdown
# Product Requirements Document: [Feature / Project Name]

## Metadata
- PRD Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/requirements/project-definition.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## Overview
[One paragraph: what, who, why]

## Personas
| Persona | Description | Primary Goal |
|---|---|---|

## Functional Requirements
| ID     | Requirement   | Priority              |
|--------|---------------|------------------------|
| FR-001 | [Requirement] | Must / Should / Could |

## Non-Functional Requirements
| ID      | Category                                       | Requirement   |
|---------|-------------------------------------------------|---------------|
| NFR-001 | [Performance / Security / Accessibility / ...] | [Requirement] |

## Out of Scope
- [Explicit exclusion]

## Open Questions
| # | Question | Owner | Status |
|---|----------|-------|--------|
```

---

## `user-stories.md`

**Output path:** `docs/requirements/user-stories.md`

**Writing Standards:**
- Every user story MUST follow the format: "As a [persona], I want [capability], so that [benefit]"
- Every acceptance criterion MUST be testable — specific, observable, binary pass/fail
- Vague criteria must be challenged and clarified before drafting

**Discovery Dimensions** (ask ONE at a time, cover all 4 before drafting):
1. Which personas and use cases should be covered?
2. For each story: what is the user's goal and the expected outcome?
3. What are the acceptance criteria for each story? (must be testable)
4. What edge cases or failure scenarios should be covered?

**Artifact format:**

```markdown
# User Stories: [Feature / Project Name]

## Metadata
- User Stories Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/requirements/prd.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## [Story Title]

**User Story**
As a [persona], I want [capability], so that [benefit].

**Acceptance Criteria**
- [ ] [Testable criterion — specific, observable, binary pass/fail]
- [ ] [Testable criterion]
- [ ] [Testable criterion]

**Edge Cases**
- [Scenario]: [Expected behavior]

---
```

---

## `user-flows.md`

**Output path:** `docs/requirements/user-flows.md`

**Discovery Dimensions** (ask ONE at a time, cover all 4 before drafting):
1. Which user journeys should be mapped?
2. For each flow: who is the actor, what triggers it, and what is the end state?
3. What alternate paths or conditional branches exist?
4. What error states or failure scenarios should be documented?

**Artifact format:**

```markdown
# User Flows: [Feature / Project Name]

## Metadata
- User Flows Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/requirements/prd.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## [Flow Name]

**Actor:** [persona]
**Trigger:** [what initiates this flow]
**Goal:** [what the actor is trying to accomplish]

**Happy Path**
1. [Step 1]
2. [Step 2]
3. ...
4. **End state:** [what is true when the flow completes successfully]

**Alternate Paths**
- [Condition]: [alternate steps or branch]

**Error States**
- [Error condition]: [expected system behavior]

---
```

---

## Draft Mode (requirements-engineer only)

**Trigger:** a `DRAFT REQUEST` prefix in the opening context, or explicit language in the request — "draft", "quick draft", "rough draft", "explore", "exploratory pass".

If none present → Draft Mode is OFF, proceed to the normal full Discovery Phase (`writer-shared`).

If present → run this flow **instead of** Discovery Phase — Full Flow (Upstream Existence Check and Skill Loading still run as normal):

### Minimal Discovery

Ask at most 3 focused questions, one at a time via `AskUserQuestion`:
1. Purpose — what problem or goal is this document meant to capture?
2. Constraints — any known limits (technical, scope, timeline, compliance)?
3. Success criteria — what does "done" or "good" look like for this?

Skip any already answered by the opening context or an earlier message. Do not ask beyond these three — Draft Mode is intentionally shallow. If the user volunteers more detail unprompted, capture it, but never expand into additional discovery dimensions.

### Approach Proposal

Immediately after Minimal Discovery: present 2-3 candidate approaches to the document's core question (different structuring strategies, scope cuts, or solution shapes depending on document type). One or two lines of trade-offs per approach. End with a clear recommendation and a one-line rationale.

Present conversationally, not via `AskUserQuestion` (this is informational framing, not a discovery question). Ask the user to confirm the recommended approach or pick an alternative before drafting begins. Wait for their choice, then proceed to Draft Phase, shaping the content around the confirmed approach.

### Exploratory Callout

Prepend immediately after the document title:

```
> ⚠️ **Draft** — This is a lightweight exploratory draft produced via Draft Mode (minimal discovery, no full interview). It is intended to be superseded by a full formal run of this agent.
```

In the Metadata block, set the version label to `v0.1-draft` instead of `v0.1`.

### Draft-to-formal upgrade

If Upstream Existence Check / Update mode finds the target document already exists AND carries a callout block whose bold label is exactly `**Draft**` (not merely a `⚠️` icon — that's also used elsewhere), AND the current run does NOT trigger Draft Mode (a normal full-discovery request) → this is a draft-to-formal upgrade: run Discovery Phase — Full Flow as normal, then during Draft Phase remove the Draft callout block and drop the `-draft` version suffix, applying the same Update Mode `+0.1` version bump (e.g. `v0.1-draft` → `v0.2` — one minor version ahead of a from-scratch formal artifact's `v0.1`, since the draft revision counts as prior document history).
