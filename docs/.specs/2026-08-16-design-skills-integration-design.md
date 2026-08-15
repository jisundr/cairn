# Design: Design-skill integration for product-designer and software-engineer

## Summary

`product-designer` already hard-requires one third-party design tool (Impeccable, vendored per-project, gated to `ui-layout-spec.md`). This adds a small, deliberately **soft-optional** layer of additional design/frontend skills on top of that existing pattern, split across two agents:

- `product-designer` gains a new **Design Quality Pass** (Taste Skill) for `ui-layout-spec.md` and `design-system.md`.
- `software-engineer` gains a new **Frontend Polish Pass** (Anthropic Frontend Design, Taste Skill, Emil Kowalski skills), gated to UI-facing work only, and gains the `Skill` tool (it currently has none).
- `/cairn-doctor` gains a report-only recommended-plugin check for the two plugin-based pieces (Taste Skill, Anthropic Frontend Design), mirroring its existing `superpowers` check exactly — never auto-installs.

Nothing in this design is hard-required. Impeccable's existing hard-require is unchanged. A fifth candidate skill, "UI UX Pro Max," was investigated and dropped — see Rejected below.

## Scope decision

| Option considered | Why not |
|---|---|
| Hard-require all five skills (mirror Impeccable) | Three of the four real skills aren't installed anywhere yet; hard-requiring them would break `product-designer`/`software-engineer` for every user until all are vendored. Contradicts the user's own "might be overkill" framing of this request. |
| Soft mention only, no dedicated pass (mirror `competitor-analyst`'s pointer to `marketing-skills`) | Too weak a guarantee — a prose mention with no check step is easy for an agent to silently skip, which defeats the anti-slop goal. |
| One new named pass per agent, soft-optional per-skill inside it (**chosen**) | One deterministic integration point per agent (not five scattered ones), degrades gracefully skill-by-skill, no breakage for users who haven't vendored everything, still fires deterministically when relevant. |
| Include "UI UX Pro Max" as a sixth soft-optional entry | Investigated and rejected — see Rejected below. Not a trust or design-fit question, a verification failure. |

## Investigated and rejected: UI UX Pro Max

`https://github.com/nextlevelbuilder/ui-ux-pro-max-skill` claims 117,037 GitHub stars (confirmed via the GitHub API directly, not just the README) on a repo created 2025-11-30 — roughly 8.5 months old, averaging ~13,700 stars/month sustained with zero prior reputation. That velocity is a known signature of purchased/bot-inflated stars, a tactic used to make an unfamiliar package look trustworthy enough that people run its install step (`npm install -g ui-ux-pro-max-cli` followed by `uipro init`) without checking. The repo's own description is also internally inconsistent about what it even is ("an AI skill (not SKILL.md format)" vs. "a Claude Code plugin/skill that auto-activates," two different install paths offered). Excluded entirely — not deferred, not marked provisional.

## The four pieces, ground-truthed

Verified directly against each repo's actual file tree and API metadata, not marketing copy:

| Skill | Type | Install | Entry point |
|---|---|---|---|
| Impeccable | vendored, non-plugin | project-specific setup (unchanged, out of scope here) | `.claude/skills/impeccable/SKILL.md` |
| Taste Skill | **plugin** — has `.claude-plugin/plugin.json` + `marketplace.json` | `/plugin marketplace add Leonxlnx/taste-skill` → `/plugin install taste-skill@taste-skill` | `Skill(skill: "taste-skill:design-taste-frontend")` |
| Emil Kowalski skills | vendored, non-plugin — no `.claude-plugin` in the repo | `npx skills@latest add emilkowalski/skills` | `.claude/skills/emil-design-eng/SKILL.md` (anchor skill; 9 sibling skills — `animate`, `review-animations`, `improve-animations`, `find-animation-opportunities`, `animation-vocabulary`, `apple-design`, `pick-ui-library`, `prototype`, `ask-sonner` — vendor alongside it, mentioned as available but not force-loaded) |
| Anthropic Frontend Design | **plugin** (already installed on this machine) | `/plugin marketplace add anthropics/claude-code` → `/plugin install frontend-design@claude-code-plugins` | `Skill(skill: "frontend-design:frontend-design")` |

Taste Skill's own SKILL.md scopes itself explicitly: *"Landing pages, portfolios, and redesigns. Not dashboards, not data tables, not multi-step product UI."* Both integration points below carry this caveat forward as guidance, not a hard filter — the consuming agent applies judgment about whether Taste Skill's aesthetic direction actually fits the artifact/task at hand, the same way Impeccable's pre-fill is treated as input rather than a mandate.

## Component 1 — `product-designer`: Design Quality Pass

New pass, soft-optional, in `agents/product-designer.md`.

**Trigger:** producing `ui-layout-spec.md` or `design-system.md`. Never `ux-spec.md` (interaction/behavior only, no visual layer — same reasoning that already excludes it from the Impeccable Shape Pass).

**Position:** after Skill Loading (`writer-shared`, `product-design-writing`), after the existing Impeccable Shape Pass when producing `ui-layout-spec.md`, before Discovery Phase.

**Procedure:**
1. Attempt `Skill(skill: "taste-skill:design-taste-frontend")`.
2. If it succeeds, fold its design-direction output into the same pre-fill role Impeccable already plays for `ui-layout-spec.md` — for `design-system.md`, which has no Impeccable Shape Pass today, this is the *first* pre-fill input it gets.
3. If the invocation fails (plugin not installed), skip silently and proceed to Discovery Phase as today. No `ABORT`, no message to the user beyond the existing `Flags` line at COMPLETION.

**Completion banner change:** `Flags` line gains a third possible value — `Taste Skill pre-fill applied` — alongside the existing `Impeccable pre-fill applied` / `Reference Artifact used` / `none`.

**Tools:** no change — `product-designer` already carries `Skill`.

## Component 2 — `software-engineer`: Frontend Polish Pass

New pass, soft-optional, in `agents/software-engineer.md`. Requires adding `Skill` to its `tools:` frontmatter line (currently `Read, Glob, Grep, Bash, Write, Edit`).

**Trigger — task must be UI-facing, checked once, not per-file:**
- **Chain mode:** the plan (`docs/.plans/<slug>.md`, already read in Step 2) describes UI/frontend/component/visual/interaction work, or names `docs/design/ui-layout-spec.md` / `docs/design/design-system.md` as source material.
- **Direct mode:** the opening request's wording is UI-facing, or the files it's about to touch match UI file types (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, `.scss`, template/markup files).
- Feasibility Assessment mode: never runs this pass — that mode writes nothing and stops at a verdict.

**Position:** new step between the existing Step 3 (`.harness/` load) and Step 5 (Implement) — call it **Step 3.5: Frontend Polish Pass**, sequenced after `.harness/` load so project-specific conventions are already in hand, before any code gets written.

**Procedure (each of the three checked independently, none blocking the others):**
1. Attempt `Skill(skill: "frontend-design:frontend-design")` — Anthropic Frontend Design. Skip silently on failure.
2. Attempt `Skill(skill: "taste-skill:design-taste-frontend")` — same skill `product-designer` uses. Skip silently on failure. Apply only where its own stated scope fits (landing/portfolio/marketing-style UI, not dashboards/data tables/multi-step product flows) — judgment call, not a hard filter.
3. `Glob(.claude/skills/emil-design-eng/SKILL.md)`. If present, `Read` it (and any of the 9 sibling skills relevant to the specific work — e.g. `animate` when building a new animation, `review-animations` as a self-check pass over animation code just written). If absent, skip silently.

If none of the three are present, the pass is a no-op — Step 5 proceeds exactly as it does today.

**Harness flag interaction:** none of this feeds `HARNESS FLAG:` — that mechanism is for undocumented *codebase* conventions, not for missing third-party skills. A missing skill here is never worth a flag; it's expected steady-state for most projects until they opt in.

**Completion banner change:** both Chain and Direct mode `PHASE HANDOFF` blocks gain a `Flags` line entry — `Frontend Polish Pass: [n of 3 applied | not UI-facing, skipped]` — for visibility into what actually fired.

## Component 3 — `/cairn-doctor` extension

`commands/cairn-doctor.md` gains two new report-only checks, inserted after the existing Step 2 (`superpowers` check), renumbering subsequent steps:

**New Step — Taste Skill / Anthropic Frontend Design.** Mirror Step 2's exact shape: check `claude plugin list --json` for `taste-skill@taste-skill` and `frontend-design@claude-code-plugins`, each `enabled: true` and scoped to this project. Report per-plugin: installed/enabled → note which passes benefit (`product-designer` Design Quality Pass, `software-engineer` Frontend Polish Pass); missing → suggest the real install commands as text (from the table above), same "never auto-install, needs the user's explicit action" rule as the existing `superpowers` check.

**New Step — Emil Kowalski skills.** `Glob(.claude/skills/emil-design-eng/SKILL.md)` in the current project. Present → report `software-engineer`'s Frontend Polish Pass can use it. Absent → suggest `npx skills@latest add emilkowalski/skills` as text, not run automatically.

Both new steps are informational only, exactly like every other `/cairn-doctor` check — "None of them are gates" is unchanged.

## Testing

No unit-testable surface changes (`tests/test_usage_dashboard.py`'s scope is untouched). Verification is the existing command-file end-to-end pattern from `CLAUDE.md`'s Testing section — run `product-designer` and `software-engineer` headless against a scratch project with and without the four skills vendored, confirm: (a) no failure/abort when absent, (b) the pass actually invokes when present, (c) the UI-facing trigger correctly fires/skips for representative Chain, Direct, and Feasibility Assessment requests, (d) `/cairn-doctor`'s new checks report accurately in both states.

## Versioning

This is a behavior change to two already-wired agents plus `/cairn-doctor` — bump `.claude-plugin/plugin.json` per `CLAUDE.md`'s Versioning section (minor, new feature) once implemented.
