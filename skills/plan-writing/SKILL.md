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

`superpowers:writing-plans` itself ends by offering a choice between its own Subagent-Driven/Inline execution modes, the latter via `superpowers:executing-plans` — Override 2's Step 0 below supersedes that offer entirely: every plan produced through this wrapper routes to either `task-orchestrator` Plan Mode (Chain flow) or Direct flow's own entry point, never to `executing-plans` directly. No path override is needed for `executing-plans` itself (it reads whatever plan path it's given), but this wrapper never actually reaches it.

## Override 2: complexity check + optional goal-file authoring

After `superpowers:writing-plans` completes its own flow (plan written, reviewed), run two more steps before any further hand-off: first, a complexity check that can route the plan to `task-orchestrator` Plan Mode outright (Step 0); only when it doesn't, an offer to draft a `/goal` completion condition for the plan (Steps 1–7), before Step 8 hands off to wherever Step 0 decided.

`/goal` is a built-in Claude Code slash command, not a marketplace skill — it is not invocable via the `Skill` tool. This step never invokes it; it drafts and persists the condition, then prints the exact manual command for the user to run themselves.

0. **Complexity check.** Read the plan's `### Task N:` blocks and their **Files** sections. If any task's `Modify: <path>` entry changes an *existing* file's current behavior (not just an appended paragraph/bullet — an edit to existing agent process steps, an existing skill's methodology, or similar), present via `AskUserQuestion`: *"This plan changes existing behavior — recommend running it through the coding chain (`task-orchestrator`) instead, for independent verification. Route through Chain flow, or proceed with Direct flow anyway?"* — citing which task/file drove the recommendation. If every task is `Create:` (new files) or purely additive `Modify:` (append-only, no behavior change), no question needed — Direct flow is the default outcome, same as this heuristic recommended before it moved here. This is a judgment call reading the plan, not a mechanical count of `Modify:` lines — the same kind of distinction `qa-auditor` already draws between an added/modified line and a pre-existing one.
   - **Chain flow chosen:** skip the rest of this section entirely, including Step 1's `/goal` offer — a `/goal` file has no role once Chain flow is running its own Attended/Unattended machinery. Hand off to `task-orchestrator` Plan Mode with the plan's slug instead of the `executing-plans` hand-off in Step 8 below.
   - **Direct flow chosen (or the default for a purely additive plan):** proceed to Step 1 below. Step 8's hand-off changes too: not to `executing-plans` (which has no submodule/chain awareness at all — the exact gap `docs/.specs/2026-08-19-coding-chain-multi-repo-safety-design.md` exists to close), but to Direct flow's own entry per `CLAUDE.md`'s Direct-flow section — the invoking session's Lightweight Start ask still happens there, right before `software-engineer` (Direct Mode) is actually dispatched, same as it always has. The `/goal` offer below is an optional layer on top of that dispatch, not a replacement for it.
1. **Offer.** One `AskUserQuestion`: "Draft a `/goal` completion condition for this plan too, so you can run it unattended?" On decline, proceed straight to Step 8's hand-off — nothing else in this section applies.
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
8. Proceed to the hand-off Step 0 determined: Direct flow's own entry point per `CLAUDE.md`'s Direct-flow section (this branch only reaches Step 8 when Step 0 chose or defaulted to Direct flow — Chain flow already exited at Step 0 itself).

## Why this exists

Same reason as `cairn:spec-writing` — keeps cairn's process documents under a consistent, dot-prefixed, flat convention without editing vendored skill files or writing this preference into every consuming project's `CLAUDE.md`. Ships with the plugin, so it applies in any project cairn is installed into.
