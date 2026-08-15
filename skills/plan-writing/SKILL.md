---
name: plan-writing
description: cairn's path-override wrapper for superpowers:writing-plans. Invoke instead of superpowers:writing-plans directly whenever intent-analyzer's Brainstorming Gate has fired, or when cairn:spec-writing hands off to it — runs the real methodology unchanged, only redirects the implementation-plan save path to docs/.plans/ instead of the vendor default docs/superpowers/plans/.
---

# Plan Writing (cairn path override)

Thin wrapper around `superpowers:writing-plans`. Does not reimplement or duplicate that skill's methodology — invokes it directly and changes exactly one thing: where the implementation plan gets saved.

## Hard requirement

The `superpowers` plugin must be installed. At the start of every invocation, invoke `Skill` with `skill: "superpowers:writing-plans"` to load the real methodology. If that invocation fails or the plugin is unavailable, stop and report: `ABORT: The superpowers plugin is required and not installed.` Do not fall back to a remembered or improvised version of writing-plans.

## The one override

Follow the loaded `superpowers:writing-plans` skill exactly, with one substitution: wherever it says to save the plan to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`, save it to `docs/.plans/YYYY-MM-DD-<feature-name>.md` instead. Every other step runs unchanged — reading the spec/requirements, structuring tasks, review checkpoints.

If the plan references an upstream spec, expect it at `docs/.specs/` (`cairn:spec-writing`'s output path), not the vendor default.

After the plan is written, `superpowers:writing-plans` hands off to `superpowers:executing-plans` — that handoff is unchanged; `executing-plans` reads whatever plan path it is given, so no override is needed there.

## Why this exists

Same reason as `cairn:spec-writing` — keeps cairn's process documents under a consistent, dot-prefixed, flat convention without editing vendored skill files or writing this preference into every consuming project's `CLAUDE.md`. Ships with the plugin, so it applies in any project cairn is installed into.
