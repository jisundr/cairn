---
name: spec-writing
description: cairn's path-override wrapper for superpowers:brainstorming's architectural-path spec output. Invoke instead of superpowers:brainstorming directly whenever intent-analyzer's Brainstorming Gate has fired — runs the real methodology unchanged, only redirects the design-doc save path to docs/.specs/ instead of the vendor default docs/superpowers/specs/.
---

# Spec Writing (cairn path override)

Thin wrapper around `superpowers:brainstorming`. Does not reimplement or duplicate that skill's methodology — invokes it directly and changes exactly one thing: where the architectural-path design doc gets saved.

## Hard requirement

The `superpowers` plugin must be installed. At the start of every invocation, invoke `Skill` with `skill: "superpowers:brainstorming"` to load the real methodology. If that invocation fails or the plugin is unavailable, stop and report: `ABORT: The superpowers plugin is required and not installed.` Do not fall back to a remembered or improvised version of brainstorming.

## The one override

Follow the loaded `superpowers:brainstorming` skill exactly, with one substitution: wherever it says to save the design doc to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` (the "Write design doc" step of its architectural path), save it to `docs/.specs/YYYY-MM-DD-<topic>-design.md` instead. Every other step runs unchanged — classification into spike/bounded/architectural, clarifying questions, approaches, sectioned design presentation, approval gates, spec self-review, user review gate.

If the brainstorming dialogue classifies the request as spike or bounded (no spec produced), this override never applies — just follow that path as-is; there is nothing to redirect.

After the spec is written and reviewed, brainstorming's own "Transition to implementation" step hands off to `writing-plans` — redirect that handoff to `Skill(skill: "cairn:plan-writing")` instead, so the resulting plan also lands under cairn's overridden path.

## Why this exists

Keeps cairn's process documents under a consistent, dot-prefixed, flat convention (`docs/.drafts/` / `docs/.specs/` / `docs/.plans/`) instead of nesting under the vendor's `docs/superpowers/` — without editing the vendored `superpowers` skill files (which would drift from upstream) or writing this preference into every consuming project's `CLAUDE.md`. Ships with the plugin, so it applies in any project cairn is installed into, with no per-project setup step required.
