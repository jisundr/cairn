# Design: merge goal-file authoring into `cairn:plan-writing`

## Summary

Ports the useful part of maestro's `goal-engineer` agent — drafting and persisting a `/goal` completion condition — into cairn without shipping it as a separate agent. Folded into `cairn:plan-writing` as a second, optional override on top of the existing save-path override, offered once a plan has just been written and reviewed. `/goal` is a built-in Claude Code slash command, not a marketplace skill — absent from this environment's skill registry the same way maestro found it absent from its own — so, same as maestro, the result is a persisted condition file plus a manual command handed back to the user, never an auto-invocation.

## Scope decision

| Decision | Chosen | Why |
|---|---|---|
| Merge scope | Plan-tied only — no standalone ad-hoc-goal path | User-selected. Maestro's `goal-engineer` also covered goals with no task/plan (`.artifacts/YYYYMMDD_goal.md` fallback); dropped here to match "merge into writing plan" literally and keep cairn's agent count from growing for a rarely-exercised edge case. |
| Draft source | Pre-fill end-state + stated-check from the plan's own acceptance-criteria/testing sections; ask only constraints + bound | User-selected. `writing-plans`' own review checkpoints already establish success criteria per task — re-running a full 4-question interview immediately after the user just reviewed those would be redundant. |
| Where it lives | Inline as a second override in `skills/plan-writing/SKILL.md`, no new agent file | Keeps the "thin wrapper, does not reimplement the vendor methodology" framing intact for the *existing* save-path override, while the goal-file step is cairn-original behavior layered on top — documented as such, not disguised as part of `superpowers:writing-plans` itself. |
| Cardinality | One goal condition per plan (no per-phase goals) | Carried over unchanged from maestro's hard requirement — a new `/goal` call replaces whatever's active, so drafting more than one per run would just discard the others. YAGNI beyond whole-plan completion. |
| File location | `docs/.plans/YYYY-MM-DD-<feature-name>-goal.md`, sibling to the plan | Maestro's `.tasks/T###-goal.md` assumed a task ID that exists by the time `goal-engineer` runs. At `plan-writing` time, `task-orchestrator` hasn't created the task folder yet — the plan file itself is the only anchor available, so the goal file sits beside it under the same dated slug. |

## Flow

Runs as the last step of `cairn:plan-writing`, after `superpowers:writing-plans` completes its own flow (plan written, reviewed, ready to hand off to `executing-plans`):

1. **Offer.** One `AskUserQuestion`: "Draft a `/goal` completion condition for this plan too, so you can run it unattended?" Decline → proceed to `executing-plans` exactly as today; nothing else in this design applies.
2. **Pre-fill draft.** Read the just-written plan's acceptance-criteria / testing sections. Compose a candidate end-state + stated-check from them.
3. **Ask what's missing** (one question at a time, `AskUserQuestion`):
   - Constraints: "Anything that must NOT change or happen on the way there? Say 'none' if there aren't any."
   - Bound: "Cap this by a turn or time limit in case it can't converge? Say 'none' to let it run until the condition is met or you cancel it."
4. **Compose final condition text** — end-state + stated-check + constraints (if any) + bound clause (if any). Validate ≤4,000 characters; if over, cut non-essential detail with the user.
5. **Show verbatim** in a fenced block, get explicit approval or edits — nothing is written until the user has seen and approved the literal wording (carried over from maestro's own non-negotiable rule).
6. **Write** `docs/.plans/YYYY-MM-DD-<feature-name>-goal.md`: the approved condition text, plus the end-state / stated-check / constraints / bound captured above, and the date drafted.
7. **Print** the exact manual command:
   ```
   /goal [the exact approved condition text]
   ```
   Plus a one-line note: `/goal` alone shows status, `/goal clear` cancels — once the user has actually invoked it.
8. Proceed to the existing hand-off to `executing-plans` (unchanged).

## Carried-over constraints (unchanged from maestro, properties of `/goal` itself)

- The condition must be phrased as something Claude's own output can demonstrate (a test result, a build exit code, a file count) — never something requiring the evaluator to independently run commands or read files, since it cannot.
- ≤4,000 characters.
- Never guess end-state/check/constraints — always ask; a condition the evaluator can't judge from the transcript is a goal that never clears.
- `/goal` doesn't change tool permissions — Claude still asks before tool calls settings don't already allow. One-line reminder to pair with auto mode if the user wants a fully unattended run.

## Out of scope

- No standalone agent, no ad-hoc (plan-less) goal path — see Scope decision above.
- No auto-invocation of `/goal` — stays a manual hand-back regardless of whether a future environment exposes it as an invocable Skill; re-visit only if that changes.
- No interaction with `task-orchestrator`'s Unattended (tmux-detached) execution — the two are orthogonal (a session-level Stop-hook evaluator vs. a detached chain run); this design doesn't wire them together.

## Implementation note

Touches `skills/plan-writing/SKILL.md` (add the second override, steps above) and `CLAUDE.md`'s `plan-writing` description (mention both overrides instead of one). No new files beyond the goal artifact itself at runtime.
