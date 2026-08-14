---
name: product-design-writing
description: Discovery dimensions, artifact formats, Reference Artifact Intake, and the Impeccable Shape Pass for the 3 design documents (ux-spec, ui-layout-spec, design-system). Loaded by product-designer alongside writer-shared.
---

# Product Design Writing

Loaded by `product-designer` for all 3 design document types, alongside `writer-shared` (general discovery/draft/update mechanics).

---

## Dependency Chain

| Document | Required Upstream |
|---|---|
| `ux-spec.md` | `docs/requirements/prd.md` AND `docs/requirements/user-flows.md` |
| `ui-layout-spec.md` | `docs/design/ux-spec.md` |
| `design-system.md` | `docs/requirements/prd.md` (independent branch — does not require `ux-spec.md`) |

`ui-layout-spec.md` additionally requires Impeccable to be vendored — see Impeccable Shape Pass below; this is a separate, additional gate on top of the upstream document check.

---

## `ux-spec.md`

**Scope:** Interaction behavior and user experience ONLY. No layout structure, no visual design, no component placement.

**Output path:** `docs/design/ux-spec.md`

**Requires Mermaid** — load `skills/mermaid-diagrams/SKILL.md` during Draft Phase (Interaction Flows section).

**Discovery Dimensions** (ask ONE at a time, cover all 7 before drafting):
1. Who are the primary user personas and what are their core goals?
2. What distinct screens or surfaces does the product have?
3. What are the primary user journeys — what tasks do users complete on each screen?
4. What actions are available per screen, and what does the system do in response?
5. What are the navigation rules — how do users move between screens?
6. What states must be handled per screen? (loading, empty, error, success)
7. Are there permission-driven visibility rules? Which actions or elements depend on user role?

**Artifact format:**

```markdown
# UX Specification: [Project Name]

## Metadata
- UX Specification Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/requirements/prd.md, docs/requirements/user-flows.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## User Personas
| Persona | Description | Primary Goal |
|---------|-------------|--------------|

---

## User Journey
[Narrative description of the core end-to-end experience for each persona]

---

## Interaction Flows
[One Mermaid flowchart per core user journey]

---

## Navigation Model
| From Screen | Action | Destination | Condition |
|-------------|--------|-------------|-----------|

---

## Screen Specifications

### [Screen Name]
**Purpose:** [What this screen exists to accomplish]
**Accessible Roles:** [Which personas or roles can access this screen]

**Primary Actions:**
| Action | Available To | System Response |
|--------|-------------|-----------------|

**Permission Rules:**
| Element / Action | Role | Visibility |
|-----------------|------|------------|

**States:**
- **Loading:** [Behavior when content is loading]
- **Empty:** [Behavior when there is no data to display]
- **Error:** [Behavior when an error occurs]
- **Success:** [Feedback after a successful action]

---

## Assumptions & Open Questions
**Assumptions:**
- [Each assumption made during discovery]

**Open Questions:**
- [Unresolved items, if any — omit section if none]
```

---

## `ui-layout-spec.md`

**Scope:** Screen layout and component structure ONLY. No interaction behavior, no validation logic, no visual styling.

**Output path:** `docs/design/ui-layout-spec.md`

**No Mermaid** — uses ASCII/text layout diagrams instead (shown inline in the template below). Do not load `skills/mermaid-diagrams/SKILL.md` for this document type.

**Discovery Dimensions** (ask ONE at a time, cover all 5 before drafting):
1. For each screen: what is the overall layout pattern? (e.g., list+detail, dashboard, full-page form, wizard)
2. What page regions exist globally across screens? (e.g., top navigation, sidebar, main content area, footer)
3. For each screen: what components occupy each region?
4. What is the component hierarchy — how are components nested within regions?
5. How does the layout respond to different screen sizes? What collapses, stacks, or converts?

**Artifact format:**

```markdown
# UI Layout Specification: [Project Name]

## Metadata
- UI Layout Specification Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/design/ux-spec.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## Global Regions
| Region ID | Region Name | Scope | Description |
|-----------|-------------|-------|-------------|
| REG-1 | [e.g., Top Navigation] | Global | ... |

---

## Screen Layouts

### [Screen Name]
**Layout Pattern:** [e.g., List + Detail, Dashboard, Full-Page Form, Wizard]

**Layout Structure:**
```
[ASCII or text representation of the layout]
Header
Content Area
  └ [Component or sub-region]
Footer
```

**Component Hierarchy:**
```
[Screen Name]
 ├── [Region / Component]
 │    └── [Sub-component]
 └── [Region / Component]
```

**Responsive Behavior:**
| Breakpoint | Transformation |
|------------|----------------|
| Mobile | ... |
| Tablet | ... |
| Desktop | ... |

---

## Component Composition Summary
| Screen | Region | Component | Notes |
|--------|--------|-----------|-------|

---

## Assumptions & Open Questions
**Assumptions:**
- [Each structural assumption made during discovery]

**Open Questions:**
- [Unresolved structural items, if any — omit section if none]
```

---

## `design-system.md`

**Scope:** Visual standards and reusable UI components ONLY. No layout structure, no interaction behavior.

**Output path:** `docs/design/design-system.md`

**No Mermaid.**

**Discovery Dimensions** (ask ONE at a time, cover all 7 before drafting):
1. What is the brand personality and visual tone? (e.g., enterprise, modern SaaS, minimal, bold, trustworthy)
2. What is the color direction — any existing brand colors, or starting fresh?
3. What typography style fits the product? (clean sans-serif, editorial, technical, warm)
4. What density preference fits the audience? (compact / information-dense vs. spacious / breathing room)
5. What are the accessibility requirements? (WCAG level, contrast, large text support)
6. Is dark mode required, optional, or out of scope?
7. What UI components are central to this product and need clear visual guidelines?

**Artifact format:**

```markdown
# Design System: [Project Name]

## Metadata
- Design System Version: v0.1
- Last Updated: YYYY-MM-DD
- Derived From: docs/requirements/prd.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: <exact_model_name>
- Reviewed By:

---

## Brand Foundation
### Brand Personality
[Short description of personality and tone]

### Design Principles
1. [Principle]
2. [Principle]
3. [Principle]

---

## Colors
### Core Palette
| Token | Value | Usage |
|-------|-------|-------|
| color-primary | #... | Primary actions, key UI elements |
| color-secondary | #... | Supporting accents |
| color-background | #... | Page background |
| color-surface | #... | Card and panel backgrounds |
| color-text-primary | #... | Primary text |
| color-text-secondary | #... | Secondary / muted text |

### Semantic Colors
| Token | Value | Usage |
|-------|-------|-------|
| color-success | #... | Positive outcomes |
| color-warning | #... | Caution states |
| color-error | #... | Error states |
| color-info | #... | Informational states |

### Dark Mode Mapping
[Either map light tokens to dark equivalents, or state: "Dark mode is not in scope for this project."]

---

## Typography
### Font Families
- **Primary:** [Font name] — headings and UI labels
- **Secondary:** [Font name] — body text (or "same as primary")
- **Monospace:** [Font name] — code or data (if applicable)

### Type Scale
| Style | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| Heading 1 | 32px / 2rem | 700 | 1.25 | Page titles |
| Heading 2 | 24px / 1.5rem | 600 | 1.3 | Section titles |
| Heading 3 | 20px / 1.25rem | 600 | 1.4 | Subsection titles |
| Body Large | 18px / 1.125rem | 400 | 1.6 | Lead text |
| Body | 16px / 1rem | 400 | 1.5 | Default body text |
| Body Small | 14px / 0.875rem | 400 | 1.5 | Supporting text |
| Caption | 12px / 0.75rem | 400 | 1.4 | Labels, metadata |

---

## Spacing
### Base Unit
**Base unit:** [e.g., 4px or 8px]

### Spacing Scale
| Token | Value | Usage |
|-------|-------|-------|
| space-1 | [base × 1] | Tight inline spacing |
| space-2 | [base × 2] | Default inline spacing |
| space-3 | [base × 3] | Component internal padding |
| space-4 | [base × 4] | Section spacing |
| space-6 | [base × 6] | Large section spacing |
| space-8 | [base × 8] | Page-level margins |

### Border Radius
| Token | Value | Usage |
|-------|-------|-------|
| radius-none | 0 | Square elements |
| radius-sm | [value] | Subtle rounding |
| radius-md | [value] | Default UI components |
| radius-lg | [value] | Cards and panels |
| radius-full | 9999px | Pills and avatars |

---

## Components
For each component: define variants, visual rules, and token references. Do NOT define interaction behavior.

### Buttons
| Variant | Background | Text Color | Border | Padding |
|---------|-----------|------------|--------|---------|
| Primary | color-primary | color-text-inverse | none | space-3 space-4 |
| Secondary | transparent | color-primary | 1px color-primary | space-3 space-4 |
| Destructive | color-error | color-text-inverse | none | space-3 space-4 |
| Ghost | transparent | color-text-primary | none | space-3 space-4 |

### Inputs
[Define border, background, focus ring, placeholder color using tokens]

### Cards
[Define background, border, shadow, radius, padding using tokens]

### Tables
[Define header background, row dividers, row hover state using tokens]

### Pagination
[Define active page indicator, inactive page color, spacing]

### Interaction Visual States
| State | Visual Rule |
|-------|-------------|
| Hover | [e.g., opacity 0.9 or lighter background] |
| Focus | [e.g., 2px outline using color-primary offset 2px] |
| Active | [e.g., scale 0.98 or darker background] |
| Disabled | [e.g., opacity 0.4, cursor not-allowed] |
| Loading | [e.g., spinner overlay, reduced opacity] |
| Error | [e.g., border color-error, error message in color-error] |

---

## Accessibility Standards
- **WCAG Level:** [AA / AAA]
- **Minimum contrast ratio (text):** 4.5:1 (normal text), 3:1 (large text)
- **Minimum touch target size:** 44×44px
- **Focus ring:** [Describe focus ring appearance]
- **Text scaling:** Layouts must remain functional up to 200% browser zoom

---

## Assumptions & Open Questions
**Assumptions:**
- [Each assumption made during discovery]

**Open Questions:**
- [Unresolved visual items, if any — omit section if none]
```

---

## Reference Artifact Intake (ui-layout-spec.md and design-system.md only)

Runs after Skill Loading (and after Impeccable Shape Pass for `ui-layout-spec.md`), before Discovery Phase, when the opening context includes a `Reference Artifact: <path-or-url>` field. Skip entirely for `ux-spec.md` and when no such field is present.

1. **Load the artifact:** local file path → `Read`. `http(s)://` URL (e.g. a `claude.ai/artifacts` link) → `WebFetch`. If loading fails, tell the user and continue discovery without it — never block the run on a missing/unreachable artifact.
2. **Extract observations:** layout structure and regions, component inventory, visual patterns (color usage, typography, spacing) evident in the markup/styles.
3. **Treat as reference input, not ground truth** — cross-check against `ux-spec.md`/`prd.md` and flag any conflict to the user rather than silently overriding it.
4. **During Discovery Phase:** for each dimension the artifact already answers, propose the pre-filled answer and ask the user to confirm or correct it — never assume silently.
5. **During Draft Phase:** cite the artifact as the source for structural/visual decisions it informed.

---

## Impeccable Shape Pass (ui-layout-spec.md only)

Impeccable is a vendored third-party design-guidance tool, not part of cairn — cairn never ships or vendors it (see the spec's Impeccable section for the full rationale). This is a hard requirement scoped to `ui-layout-spec.md` only: `ux-spec.md` and `design-system.md` are entirely unaffected by Impeccable's presence or absence.

Runs after Skill Loading, before Discovery Phase, when producing `ui-layout-spec.md`:

1. Use `Glob` to check for `.claude/skills/impeccable/SKILL.md` in the current project.
2. **If absent:** `ABORT` this run only — "Impeccable is required for UI Layout Specification and isn't vendored in this project. Vendor it (see impeccable's own setup) and re-run." Do not write any file. `ux-spec.md` and `design-system.md` runs are unaffected — this abort applies only to a `ui-layout-spec.md` invocation.
3. **If present:** invoke `Skill(skill: "impeccable", args: "shape [ui-layout-spec scope/feature], upstream ux-spec: [ux-spec.md path]")` once.
4. Treat the design-brief output from `shape` purely as **pre-filled input** to the upcoming Discovery Phase — same treatment as Reference Artifact Intake's pre-fills (propose the pre-filled answer per discovery dimension, ask the user to confirm or correct, never assume silently). Do NOT treat this as a second freestanding interview layered on top of the normal Discovery Phase — `shape` itself runs its own interview internally; only its final output is used here, as pre-fill, not as a live second conversation.
5. If this is the first time Impeccable has run in this project (no `PRODUCT.md` present), its own `shape` invocation may divert into its own product-definition bootstrap first — this is a real, expected one-time cost on first use, not a bug. Do not attempt to skip or suppress it.
6. Proceed to Discovery Phase (or Reference Artifact Intake, if a `Reference Artifact:` field is also present).
