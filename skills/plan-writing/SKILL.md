---
name: plan-writing
description: cairn's path-override wrapper for superpowers:writing-plans. Invoke instead of superpowers:writing-plans directly whenever intent-analyzer's Brainstorming Gate has fired, or when cairn:spec-writing hands off to it — runs the real methodology unchanged, redirecting the implementation-plan save path to docs/.plans/ instead of the vendor default docs/superpowers/plans/, and adding two steps after that: a complexity check that can route a plan changing existing behavior to task-orchestrator instead, and — only when it doesn't — an optional step that drafts a /goal completion condition for the plan.
---

# Plan Writing (cairn path override)

Thin wrapper around `superpowers:writing-plans`. Does not reimplement or duplicate that skill's methodology — invokes it directly and changes exactly one thing about where the plan is saved, and adds two steps after that: a complexity check that can route a plan changing existing behavior to `task-orchestrator` instead, and — only when it doesn't — an optional step that drafts a `/goal` completion condition for the plan after it's written.

## Hard requirement

The `superpowers` plugin must be installed. At the start of every invocation, invoke `Skill` with `skill: "superpowers:writing-plans"` to load the real methodology. If that invocation fails or the plugin is unavailable, stop and report: `ABORT: The superpowers plugin is required and not installed.` Do not fall back to a remembered or improvised version of writing-plans.

## Override 1: save path

Follow the loaded `superpowers:writing-plans` skill exactly, with one substitution: wherever it says to save the plan to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`, save it to `docs/.plans/YYYY-MM-DD-<feature-name>.md` instead. Every other step runs unchanged — reading the spec/requirements, structuring tasks, review checkpoints.

If the plan references an upstream spec, expect it at `docs/.specs/` (`cairn:spec-writing`'s output path), not the vendor default.

After the plan is written, `superpowers:writing-plans` hands off to `superpowers:executing-plans` — that handoff is unchanged; `executing-plans` reads whatever plan path it is given, so no override is needed there.

## Override 2: optional goal-file authoring

After `superpowers:writing-plans` completes its own flow (plan written, reviewed, ready to hand off to `executing-plans`), run one more step before that hand-off: offer to draft a `/goal` completion condition for the plan just written.

`/goal` is a built-in Claude Code slash command, not a marketplace skill — it is not invocable via the `Skill` tool. This step never invokes it; it drafts and persists the condition, then prints the exact manual command for the user to run themselves.

0. **Complexity check.** Read the plan's `### Task N:` blocks and their **Files** sections. If any task's `Modify: <path>` entry changes an *existing* file's current behavior (not just an appended paragraph/bullet — an edit to existing agent process steps, an existing skill's methodology, or similar), present via `AskUserQuestion`: *"This plan changes existing behavior — recommend running it through the coding chain (`task-orchestrator`) instead of a `/goal` loop, for independent verification. Route through Chain flow, or continue with `/goal`-file drafting?"* — citing which task/file drove the recommendation. This is a judgment call reading the plan, not a mechanical count of `Modify:` lines — the same kind of distinction `qa-auditor` already draws between an added/modified line and a pre-existing one.
   - **Chain flow chosen:** skip the rest of this section entirely — a `/goal` file has no role once Chain flow is running its own Attended/Unattended machinery. Hand off to `task-orchestrator` Plan Mode with the plan's slug instead of the `executing-plans` hand-off in Step 8 below.
   - **Continue with `/goal` chosen, or the plan is purely additive** (every task is `Create:`, or `Modify:` is append-only with no behavior change) — no question needed in the additive case, proceed straight to Step 1 below, unchanged.
1. **Offer.** One `AskUserQuestion`: "Draft a `/goal` completion condition for this plan too, so you can run it unattended?" On decline, proceed straight to the existing `executing-plans` hand-off — nothing else in this section applies.
2. **Pre-fill.** Read the plan's own acceptance-criteria/testing sections (the review checkpoints `writing-plans` itself just produced). Compose a candidate end-state and stated-check from them — do not re-ask what the plan already establishes.
3. **Ask what's missing**, one question at a time via `AskUserQuestion`:
   - "Anything that must NOT change or happen on the way there? Say 'none' if there aren't any." (constraints)
   - "Cap this by a turn or time limit in case it can't converge? Say 'none' to let it run until the condition is met or you cancel it." (bound)
4. **Compose** the final condition text: end-state + stated-check + constraints (if any) + bound clause (if any). Validate it's ≤4,000 characters; if over, cut non-essential detail with the user before continuing.
5. **Show verbatim** in a fenced block and get explicit approval or edits — nothing is written until the user has seen and approved the literal wording. The condition must be phrased as something Claude's own output can demonstrate (a test result, a build exit code, a file count) — never something requiring the evaluator to independently run commands or read files, since it cannot.
6. **Write** `docs/.plans/YYYY-MM-DD-<feature-name>-goal.md` (same date and feature-name as the plan file itself, sibling to it): the approved condition text, plus the end-state / stated-check / constraints / bound captured above, and the date drafted.
7. **Print** the exact manual command:
   ```
   /goal [the exact approved condition text]
   ```
   Plus a one-line note: `/goal` alone shows status, `/goal clear` cancels — once actually invoked. Also remind once, briefly: `/goal` doesn't change tool permissions — Claude still asks before tool calls your settings don't already allow; pair with auto mode for a fully unattended run.
8. Proceed to the existing hand-off to `executing-plans`, unchanged.

## Why this exists

Same reason as `cairn:spec-writing` — keeps cairn's process documents under a consistent, dot-prefixed, flat convention without editing vendored skill files or writing this preference into every consuming project's `CLAUDE.md`. Ships with the plugin, so it applies in any project cairn is installed into.
