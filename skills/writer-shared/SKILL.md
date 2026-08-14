---
name: writer-shared
description: Shared mechanics for cairn's writer-trio agents (requirements-engineer, product-designer, solution-architect) — discovery phase, draft phase, update mode, final review, document metadata, exit rows. Loaded by all three at the start of every run.
---

# Writer Shared — Common Mechanics

Shared rules and procedures used by `requirements-engineer`, `product-designer`, and `solution-architect`. Each agent also loads its own doc-type skill (`requirements-writing` / `product-design-writing` / `solution-architecture-writing`) for discovery dimensions, artifact format, and writing standards specific to its document types.

---

## Suggestion Assistance Rule (mandatory)

During Discovery, you MAY offer suggestions to help the user frame an answer: example answers, common patterns, multiple-choice options, clarifying contrasts, short illustrative scenarios.

Rules:
- Suggestions MUST be clearly labeled as examples or options.
- Suggestions MUST NOT be treated as chosen unless the user explicitly confirms.
- Suggestions MUST NOT introduce scope, requirements, or decisions outside the current document's domain.
- Never assume a suggestion is accepted without confirmation, never fill in an answer on the user's behalf, never convert a suggestion into document content without explicit confirmation.

---

## Shared Enforcement Rules

- Ask naturally, not mechanically.
- Suggestions are helpers, not decisions.
- One final draft only.
- No assumptions without confirmation.
- No partial artifacts.
- Never remove or renumber existing stable identifiers (FR-###, NFR-###, AC-N, ADR-NNNN, etc.) during an update — preserve them even when surrounding prose is rewritten.

---

## Document Metadata — Shared Template

Every artifact's `## Metadata` block (ADRs are the one exception — they use `## Status`/`## Date` instead, see `solution-architecture-writing`):

```
## Metadata
- [Document Version Label]: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: [see the loaded doc-type skill for this document's real upstream path — "User discovery interview" only when the document genuinely has no required upstream]
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:
```

For updates: increment the version (`v0.1` → `v0.2`), update `Last Updated` to today's date, preserve all other original metadata fields.

`LLM Model:` records the actual model that authored the document. This agent runs in the main conversation thread (its `AskUserQuestion` discovery gates require it) — that's the main-loop model. Record it faithfully even if it differs across sibling documents; never backfill to match convention.

---

## Discovery Phase — Shared Rules

- Ask questions conversationally, one at a time, via `AskUserQuestion`.
- Do NOT mention section numbers or document structure during discovery.
- Adapt questions based on previous answers.
- Skip questions already answered implicitly (including by canonical source documents already read).
- Clarify ambiguity immediately.
- Do NOT summarize or draft during this phase.
- Never guess or infer silently.

---

## Upstream Existence Check (mandatory — runs before Discovery)

Before asking any discovery questions:

1. Use `Read` to check whether the required upstream document(s) exist (per the loaded doc-type skill's dependency chain).
2. If any required upstream does NOT exist → respond exactly: `TERMINATED: [upstream path] is required before [target document] can be produced. Complete the upstream document first.` Do not proceed further.
3. If the target document already exists → read it in full. This is an Update run — see Update Mode below.
4. If all required upstream exist → read them in full, then proceed to Skill Loading (the doc-type skill may define an additional step here, e.g. reading recommended-but-optional upstream).

---

## Discovery Phase — Full Flow

Runs after Skill Loading (the doc-type skill defines the discovery dimensions for the target document). Apply Discovery Phase — Shared Rules throughout. Ask ONE question at a time via `AskUserQuestion`, using the loaded doc-type skill's discovery dimensions. Do not proceed to drafting until you have enough to produce the complete artifact. Apply the Suggestion Assistance Rule.

Discovery completion check — exit Discovery ONLY when:
- All discovery dimensions from the loaded doc-type skill are sufficiently covered.
- Remaining uncertainty can be documented as assumptions or open questions.
- You have enough to write the complete artifact.

Once complete, say explicitly: **"I have enough information to draft the [document type]."**

---

## Draft Phase — Write Tool Shared Steps

Runs after Discovery is complete:

1. If the target document type requires diagrams (the loaded doc-type skill states this explicitly), invoke `Skill(skill: "mermaid-diagrams")` first and apply its rules while drafting. Skip this step entirely for document types that don't need diagrams — do not load it speculatively.
2. Apply any doc-type-specific technical standards the loaded doc-type skill defines for this step (e.g. `solution-architecture-writing`'s `db-standards`/`api-standards`/GraphQL content).
3. Structure the full content using the artifact format defined in the loaded doc-type skill.
4. Use the `Write` tool to write exactly one file — do NOT display the full document as text in the session first.
5. Do NOT ask questions before invoking `Write`.
6. Do NOT write any other file in the same run.

After writing, apply Final Review Phase below.

---

## Final Review Phase — Template

After the `Write` tool call is approved and the file is written:

1. Use `AskUserQuestion` with the question `"Review the [DOCUMENT_NAME]. Happy with the changes?"` and two options: **Yes** ("Proceed — the run is complete.") and **No** ("Describe what you'd like to change in the notes field.").
2. If **Yes** → proceed to the agent's own Completion block.
3. If **No** → apply the revisions from the notes, re-invoke `Write` with the revised content, repeat from step 1.

If the user denies the initial `Write` tool call: ask `"What would you like to change?"` with options **Describe changes** (apply and re-invoke `Write`) or **Cancel** (stop, discard the draft).

---

## Update Mode — Shared Steps

Triggered when Upstream Existence Check finds the target document already exists.

1. **Read and analyze** — read the existing document in full. Internally identify areas that may need updating. Don't share this analysis with the user yet.
2. **Open the conversation** — "I found an existing [DOCUMENT_TYPE] (version [X], last updated [date]). Would you like to review and update it, or start fresh?" If "start fresh" → discard existing context, proceed to Discovery Phase — Full Flow. If "update" → continue.
3. **Present suggested review areas** — frame your analysis as observations, not conclusions ("might be worth reviewing," never "this is wrong"). The user may reject all suggestions and name their own areas. Do not begin questioning until the user confirms what to update.
4. **Confirm scope** — "Got it. I'll focus the update on: [areas]. I'll ask a few targeted questions for each."
5. **Targeted re-interview** — one question at a time, just enough to revise each in-scope section confidently. Same rules as Discovery Phase.
6. Once all in-scope areas are addressed, say: **"I have enough information to draft the updated [DOCUMENT_TYPE]."** Update only in-scope sections, bump the version (`v0.1` → `v0.2`), update `Last Updated` to today's date. Proceed to Draft Phase and Final Review Phase as normal.

---

## Generic Exit Rows

Applies to all three writer-trio agents. Each agent's own file fills in `[artifact-noun]` / `[Agent domain]` and lists only its scope-specific rows beyond these four:

| Trigger | Response |
|---|---|
| Upstream document missing | `TERMINATED: [upstream path] is required before [target] can be produced.` |
| User tries to produce multiple artifacts in one run | "This agent produces one [artifact-noun] per run. Complete this one, then invoke it again for the next." |
| User tries to skip discovery | "I need a few answers first to produce a complete [artifact-noun]. Let me ask one question at a time." |
| User abandons the session | "[Agent domain] session ended. No artifact was committed." |
