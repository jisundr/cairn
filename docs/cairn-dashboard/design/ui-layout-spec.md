# UI Layout Specification: cairn-dashboard

## Metadata
- UI Layout Specification Version: v0.11
- Last Updated: 2026-08-19
- Derived From: docs/cairn-dashboard/design/ux-spec.md
- Author:
  - AI Tool: Claude Code
  - LLM Model: claude-sonnet-5
- Reviewed By:

---

## Global Regions
| Region ID | Region Name | Scope | Description |
|-----------|-------------|-------|-------------|
| REG-1 | Top Nav | Global | Tab bar (Usage / Tracker / Swarms), always visible, present on every screen |
| REG-2 | Screen Toolbar | Per-screen | Secondary controls specific to the active screen — Usage's period/anchor/timezone controls, Tracker's Board/Roadmap sub-tabs, Swarms' sort-order control. |
| REG-3 | Main Content Area | Per-screen | The screen's primary content, fills remaining vertical space below REG-1/REG-2 |
| REG-4 | Detail Pane | Swarms only | Right-hand panel within Swarms' Main Content Area, showing the selected swarm's full detail; empty-state prompt when nothing is selected |

---

## Screen Layouts

### Usage
**Layout Pattern:** Dashboard (stacked sections)

**Layout Structure:**
```
Top Nav (REG-1)
Screen Toolbar (REG-2): period buttons + anchor nav (prev/next/Latest) + UTC/Local toggle + info icon
Main Content Area (REG-3)
  └ Usage heatmap (full history, Sunday-start weeks, month labels; static —
                    shown first because it does not respond to REG-2's
                    period/anchor filter, only re-buckets on tz toggle)
  └ Stat Grid (cost, tokens, calls, sessions, cache-hit)
  └ Ranking lists (by-model, by-version, by-subagent, by-skill; always
                    scoped to REG-2's period/anchor window)
  └ Cost-over-time chart (24 hourly buckets for Daily; daily buckets for
                           Weekly/Monthly/YTD; monthly buckets for Yearly)
  └ Sessions table (Model/Version filter, sortable columns, pagination)
```

**Component Hierarchy:**
```
Usage Screen
 ├── TopNav (shared)
 ├── PeriodToolbar
 │    ├── PeriodButton × 5 (Daily, Weekly, Monthly, Yearly, YTD)
 │    ├── AnchorNav (prev, anchor label, next, Latest — hidden for YTD)
 │    ├── TimezoneToggle (UTC, Local)
 │    └── InfoIcon
 └── MainContent
      ├── UsageHeatmap
      │    ├── MonthLabelRow
      │    ├── WeekColumn × N
      │    │    └── DayCell × 7 (empty-padding cells at the grid's edges)
      │    └── HeatmapLegend (Less → More, 5-level swatch key)
      ├── StatGrid
      │    └── StatTile × 5
      ├── RankingSection × 4 (by-model, by-version, by-subagent, by-skill)
      │    └── RankRow × N
      ├── CostChart
      └── SessionsTable
           ├── SessionsFilterBar (Model select, Version select — both default "All")
           ├── SessionRow × N (per page; header cells sortable)
           └── Pagination (Prev, page indicator, Next — shown only above one page)
```

**Responsive Behavior:**
| Breakpoint | Transformation |
|------------|----------------|
| Mobile | Stat grid stacks to 1 column, ranking sections stack vertically (no longer side-by-side), sessions table scrolls horizontally within its own container |
| Tablet | Stat grid reflows to 2-3 columns, ranking sections in 2-column grid |
| Desktop | Stat grid at full column count, ranking sections in 2×2 grid, sessions table full-width |

---

### Tracker
**Layout Pattern:** Kanban board (Board sub-view) / Grouped list (Roadmap sub-view)

**Layout Structure:**
```
Top Nav (REG-1)
Screen Toolbar (REG-2): Board / Roadmap sub-tabs
Main Content Area (REG-3)
  Board sub-view:
    └ Status columns (Idea, Groomed, In Progress, In Review, Blocked, Done)
        └ Task cards
  Roadmap sub-view:
    └ Milestone groups (rail/station layout)
        └ Task cards
```

**Component Hierarchy:**
```
Tracker Screen
 ├── TopNav (shared)
 ├── SubViewToolbar
 │    └── SubTabButton × 2 (Board, Roadmap)
 └── MainContent
      ├── (Board) BoardView
      │    └── StatusColumn × 6
      │         └── TaskCard × N
      └── (Roadmap) RoadmapView
           └── MilestoneStation × M
                └── TaskCard × N
```

**Responsive Behavior:**
| Breakpoint | Transformation |
|------------|----------------|
| Mobile | Board columns stack vertically (single column, scroll down instead of across); Roadmap stations stack vertically |
| Tablet | Board columns scroll horizontally (2-3 visible at once); Roadmap stations scroll horizontally |
| Desktop | Board columns all visible side-by-side (horizontal scroll only if more than fit); Roadmap stations laid out horizontally |

---

### Swarms
**Layout Pattern:** List + Detail (two-pane split, list narrow/left, detail wide/right — same family as an issue tracker's list-and-detail view)

**Layout Structure:**
```
Top Nav (REG-1)
Screen Toolbar (REG-2): sort-order control (Priority / Recent activity / Name)
Main Content Area (REG-3)
  ├ List Pane (~40% width)
  │   └ Swarm list item × N (one per Mode:Unattended task), ordered per REG-2
  │       └ slug, phase, tmux liveness, elapsed time
  └ Detail Pane (~60% width, REG-4)
      └ (no selection) empty-state prompt
      └ (selected) phase-progress timeline, branch, worktree, elapsed time,
                    recent-history log, pane-tail excerpt (HANDOFF NEEDED only)
```

**Component Hierarchy:**
```
Swarms Screen
 ├── TopNav (shared)
 ├── SortToolbar (REG-2)
 │    └── SortButton × 3 (Priority, Recent activity, Name)
 └── MainContent
      ├── SwarmList (List Pane)
      │    └── SwarmListItem × N
      │         ├── SwarmHeader (slug, phase)
      │         ├── LivenessDot
      │         └── ElapsedTime
      └── SwarmDetailPanel (Detail Pane, REG-4)
           ├── (empty) DetailEmptyState
           └── (selected)
                ├── PhaseTimeline (7 fixed steps, current highlighted)
                ├── SwarmMeta (branch, worktree, elapsed time)
                ├── StatusBadge (stalled | soft-hint | none)
                ├── HistoryLog (recent HISTORY.md entries, newest first)
                └── PaneTailExcerpt (conditional: HANDOFF NEEDED only)
```

**Responsive Behavior:**
| Breakpoint | Transformation |
|------------|----------------|
| Mobile | List and detail pane stack vertically — list first (full width), detail pane appears below it once a swarm is selected (or replaces the list entirely with a back affordance, implementer's choice within this constraint) |
| Tablet | Two-pane split narrows (e.g. 45/55) but stays side-by-side down to a minimum list-pane width, then falls back to the mobile stacked behavior |
| Desktop | Full two-pane split, ~40/60 |

---

## Component Composition Summary
| Screen | Region | Component | Notes |
|--------|--------|-----------|-------|
| Usage | REG-1 | TopNav | Shared across all screens |
| Usage | REG-2 | PeriodToolbar | 5 period buttons + anchor nav + UTC/Local toggle + info icon |
| Usage | REG-3 | UsageHeatmap, StatGrid, RankingSection ×4, CostChart, SessionsTable | Heatmap always shows full history, independent of REG-2's period/anchor. CostChart and RankingSection always match REG-2's window (no independent scope/metric controls). SessionsTable adds its own Model/Version filter, sortable headers, and pagination on top of REG-2's period window. |
| Tracker | REG-1 | TopNav | Shared |
| Tracker | REG-2 | SubViewToolbar | Board/Roadmap toggle |
| Tracker | REG-3 | BoardView or RoadmapView | Mutually exclusive, one active at a time |
| Swarms | REG-1 | TopNav | Shared |
| Swarms | REG-2 | SortToolbar | Priority / Recent activity / Name |
| Swarms | REG-3 | SwarmList | List pane within REG-3, ordered per REG-2 |
| Swarms | REG-4 | SwarmDetailPanel | Right pane; empty-state or selected-swarm detail |

---

## Assumptions & Open Questions
**Assumptions:**
- Desktop-first: this is a local dev tool typically viewed in a wide browser window, but mobile/tablet breakpoints are still defined for robustness, not treated as the primary target.
- No component library or visual styling decided here — that's Design System's scope (not yet produced, tracked as an open item).

**Open Questions:**
- None structural — all 5 discovery dimensions covered. Visual styling (colors, typography, spacing) intentionally deferred to a future `design-system.md` pass.
