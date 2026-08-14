---
name: mermaid-diagrams
description: Mermaid.js diagram type selection, placement, and formatting rules for cairn's design/architecture doc-writing agents. Loaded conditionally by product-designer (ux-spec.md) and solution-architect (architecture-spec.md, db-schema.md, ADRs) — never by requirements-engineer. The specific doc-type skill loading this determines WHERE a diagram goes; this skill defines HOW to draw it correctly once you're there.
---

# Mermaid Diagram Standards

Diagram type selection, placement, and formatting rules for any document that embeds a Mermaid diagram. Which section of which document needs a diagram is defined by the loaded doc-type skill (`product-design-writing` or `solution-architecture-writing`), not by this file — this file only defines how to draw the diagram correctly once you know where one goes.

---

## Diagram Type Reference

| Content | Type | Keyword |
|---|---|---|
| System context / external actors | C4 Context | `C4Context` |
| User flows, experience maps | User Journey | `journey` |
| Multi-step processes | Flowchart | `flowchart TD` |
| Stakeholder/component relationships | Flowchart | `flowchart LR` |
| Scope boundaries | Subgraph Flowchart | `flowchart TD` + `subgraph` |
| Status/lifecycle transitions | State Diagram | `stateDiagram-v2` |
| System/API interactions | Sequence Diagram | `sequenceDiagram` |
| Entity relationships | ER Diagram | `erDiagram` |
| Timelines, phases | Gantt | `gantt` |
| Prioritization, positioning | Quadrant Chart | `quadrantChart` |
| Architecture blocks | Block Diagram | `block-beta` |

---

## Diagram Placement Rules

- Insert each diagram **immediately after the (sub)section heading** it illustrates, before existing prose.
- Add a caption on the line after the closing fence: `**Figure N: [Description]**`.
- Number figures sequentially across the full document starting at 1.
- Skip: Metadata, Change Log, and Open Questions sections — never add a diagram there.
- Do not add a second diagram of the same type to the same section.
- If discovery data is incomplete, use placeholder labels like `[TBD]` — still include the diagram rather than omitting it.

---

## Diagram Format Rules

- Use fenced code blocks with the ` ```mermaid ` language tag.
- Node labels: max 5 words, no special characters.
- Node IDs: alphanumeric only — `BookingSubmit`, not `booking submit`.
- Direction: `TD` for processes/hierarchies; `LR` for relationships.
- Use `subgraph` to group related nodes.
- Split diagrams with more than 15 nodes into two focused diagrams.

Standard Mermaid.js syntax (`journey`, `flowchart`, `stateDiagram-v2`, `erDiagram`, `block-beta`, `sequenceDiagram`, etc.) is assumed.
