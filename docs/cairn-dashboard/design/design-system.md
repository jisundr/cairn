# Design System: cairn-dashboard

## Metadata
- Design System Version: v0.2
- Last Updated: 2026-08-19
- Derived From: docs/cairn-dashboard/requirements/prd.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: claude-sonnet-5
- Reviewed By:

---

## Brand Foundation
### Brand Personality
Modern, calm, developer-tool minimal — quiet confidence over expression. Not warm/artisan, not marketing/persuasive. The visitor came to check status, not be sold something.

### Design Principles
1. Read-only clarity — nothing on screen invites an edit/delete/trigger action; visual weight goes to information, never controls.
2. Function over ornamentation — no decorative imagery, no marketing chrome, no gradients-for-mood.
3. Restrained color, semantic when it matters — neutral base, one accent for primary emphasis, color reserved for real state (stalled = red, done = green) not decoration.
4. Native-feeling and fast — system fonts, no web-font loading cost, matches the zero-dependency ethos of the product itself.

---

## Colors
### Core Palette
| Token | Value | Usage |
|-------|-------|-------|
| color-primary | #3d6fd9 | Primary actions, active tab indicator, key emphasis, "currently active/running" states (Swarms Running pill, current step in a progress timeline), Tracker's In Review column (reused rather than adding a 5th semantic color — both mean "needs attention now") |
| color-secondary | #6b6b62 | Supporting accents, secondary text emphasis |
| color-background | #f7f7f5 | Page background (light) |
| color-surface | #ffffff | Card and panel backgrounds (light) |
| color-text-primary | #1c1c1a | Primary text (light) |
| color-text-secondary | #6b6b62 | Secondary / muted text |

### Semantic Colors
| Token | Value | Usage |
|-------|-------|-------|
| color-success | #3d8b5f | Done status, healthy/alive tmux indicator |
| color-warning | #d9a441 | Soft "no progress" hint, In Progress status |
| color-error | #b5482f | Authoritative STALLED badge, Blocked status |
| color-info | #4472c4 | Groomed status, informational badges |

### Dark Mode Mapping
| Token | Light | Dark |
|-------|-------|------|
| color-background | #f7f7f5 | #15171a |
| color-surface | #ffffff | #1e2124 |
| color-text-primary | #1c1c1a | #e9e7e0 |
| color-text-secondary | #6b6b62 | #9c9a92 |
| color-primary | #3d6fd9 | #5b8aef |
| color-success | #3d8b5f | #4fae7c |
| color-warning | #d9a441 | #e0b256 |
| color-error | #b5482f | #d16249 |

Follows `prefers-color-scheme` by default (no manual toggle required for v1) — standard practice for a tool used alongside a code editor.

---

## Typography
### Font Families
- **Primary:** System sans-serif stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`) — headings and UI labels
- **Secondary:** Same as primary — body text
- **Monospace:** System monospace stack (`ui-monospace, SFMono-Regular, monospace`) — branch names, slugs, code-like data

### Type Scale
| Style | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| Heading 1 | 20px / 1.25rem | 700 | 1.3 | Page title ("Cairn Dashboard") |
| Heading 2 | 16px / 1rem | 600 | 1.35 | Section headings (card group headers) |
| Heading 3 | 14px / 0.875rem | 600 | 1.4 | Sub-section labels |
| Body Large | 16px / 1rem | 400 | 1.5 | Stat tile values |
| Body | 14px / 0.875rem | 400 | 1.45 | Default UI text |
| Body Small | 13px / 0.8125rem | 400 | 1.4 | Table cells, metadata |
| Caption | 11px / 0.6875rem | 600 | 1.4 | Uppercase labels (stat tile labels, table headers) |

Numeric data (costs, token counts, timestamps) uses `font-variant-numeric: tabular-nums` throughout for column alignment.

---

## Spacing
### Base Unit
**Base unit:** 4px

### Spacing Scale
| Token | Value | Usage |
|-------|-------|-------|
| space-1 | 4px | Tight inline spacing (icon-to-label) |
| space-2 | 8px | Default inline spacing |
| space-3 | 12px | Component internal padding |
| space-4 | 16px | Section spacing |
| space-6 | 24px | Large section spacing (between major regions) |
| space-8 | 32px | Page-level margins |

Density target: "Daily App" (standard web-app spacing) — not cockpit-tight (this isn't a trading terminal) and not art-gallery-airy (this is a tool checked frequently, not admired).

### Border Radius
| Token | Value | Usage |
|-------|-------|-------|
| radius-none | 0 | Table cells, dividers |
| radius-sm | 6px | Buttons, tabs, badges |
| radius-md | 8px | Stat tiles, small components |
| radius-lg | 10px | Cards (swarm cards, task cards, panels) |
| radius-full | 9999px | Status badges, pills |

---

## Components
### Buttons / Tabs
| Variant | Background | Text Color | Border | Padding |
|---------|-----------|------------|--------|---------|
| Tab (active) | color-surface | color-text-primary | none | space-2 space-3 |
| Tab (inactive) | transparent | color-text-secondary | none | space-2 space-3 |
| Primary button | color-primary | #ffffff | none | space-2 space-4 |
| Ghost button | transparent | color-text-primary | 1px color-background | space-2 space-4 |

### Stat Tiles
Background `color-surface`, 1px border in a neutral tint of `color-background`, `radius-md`, `space-4` padding. Label in Caption style (uppercase, `color-text-secondary`), value in Body Large (bold, `color-text-primary` or `color-primary` for the primary/accented stat).

### Cards (swarm cards, task cards)
Background `color-surface`, 1px border, `radius-lg`, `space-4` padding, no shadow by default (flat, bordered — shadows reserved for nothing in this system; elevation communicated by border + background contrast, not drop shadow).

### Tables
Header row: Caption style, uppercase, `color-text-secondary`, bottom border. Row dividers: 1px `color-background`-tinted border between rows, no border under the last row. No row hover background (read-only, no row-click action exists).

### Badges (status, stalled)
`radius-full`, `space-1 space-2` padding, Caption-weight text, white text on a semantic-color background (success/warning/error/info per token above). Stalled badge always uses `color-error`; soft "no progress" hint renders as plain `color-text-secondary` text, not a badge (it's a hint, not a status).

### Empty States
Centered, `color-text-secondary`, Body style, `space-8` vertical padding — no illustration, plain text message per screen (e.g. "No tasks tracked yet — run project-manager to decompose a PRD into docs/.tasks/TRACKER.md.").

### Interaction Visual States
| State | Visual Rule |
|-------|-------------|
| Hover | Tabs/buttons: background shifts to `color-background` tint |
| Focus | 2px outline in `color-primary`, offset 2px (keyboard nav for tab bar) |
| Active | Tab: background becomes `color-surface`, text becomes `color-text-primary` |
| Disabled | Not applicable — no disabled controls exist in a read-only interface |
| Loading | Plain "Loading…" text, no skeleton loaders (first-fetch only, brief) |
| Error | Stale-data indicator: small `color-warning`-toned text/icon on the existing view, non-blocking |

---

## Accessibility Standards
- **WCAG Level:** AA (standard practice — not a hard product requirement per PRD, but the baseline this system targets)
- **Minimum contrast ratio (text):** 4.5:1 (normal text), 3:1 (large text)
- **Minimum touch target size:** 44×44px (tab bar buttons, sub-tab buttons)
- **Focus ring:** 2px solid `color-primary`, 2px offset, visible on keyboard navigation of the tab bar and any interactive element
- **Text scaling:** Layouts remain functional up to 200% browser zoom (verified structurally by UI Layout Spec's single-column mobile fallback already covering the narrow-viewport case)

---

## Assumptions & Open Questions
**Assumptions:**
- No brand logo/wordmark beyond the existing "Cairn Dashboard" text title — no icon/logo system needed.
- No component library dependency introduced — these tokens are implemented as plain CSS custom properties in `dashboard/src/index.css`, consistent with the "no new dependencies" constraint.

**Open Questions:**
- None — all 7 discovery dimensions covered directly from Product Principles and confirmed answers, no unresolved visual items.
