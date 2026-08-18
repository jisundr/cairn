# UAT Checklist: goal-file-plan-writing

Manual verification for "Add optional goal-file authoring to `cairn:plan-writing`" (`docs/.plans/2026-08-18-goal-file-plan-writing.md`, spec `docs/.specs/2026-08-18-goal-file-plan-writing-design.md`).

Automated coverage already run this task: `claude plugin validate . --strict` (pass), `pytest tests/test_usage_dashboard.py -v` (29/29), and a headless smoke test of Step 1 only (offer question reachable, plan save-path override confirmed). This is a markdown-only skill-definition change with no unit-testable code, so Steps 2-8 of the new flow below have no automated coverage — that's the gap this checklist exists to close manually.

- [ ] Run `/cairn:plan-writing` end-to-end (interactively, not headless) against a real spec, through to the point `superpowers:writing-plans` finishes writing and reviewing a plan.
- [ ] Confirm the new offer fires before the `executing-plans` hand-off: "Draft a `/goal` completion condition for this plan too, so you can run it unattended?"
- [ ] Decline the offer once — confirm it proceeds straight to the existing `executing-plans` hand-off with nothing else from the new section running.
- [ ] Re-run and accept the offer — confirm the pre-fill draws from the plan's own acceptance-criteria/testing sections rather than re-asking what the plan already establishes.
- [ ] Confirm the two follow-up questions appear one at a time: "Anything that must NOT change or happen on the way there?" and the turn/time-limit bound question — and that answering "none" to each is accepted cleanly.
- [ ] Confirm the composed condition is shown verbatim in a fenced block before anything is written, and that requesting an edit at that point works before final approval.
- [ ] After approval, confirm `docs/.plans/YYYY-MM-DD-<feature-name>-goal.md` is written beside the plan file, containing the approved condition text plus the captured end-state / stated-check / constraints / bound / date.
- [ ] Confirm the exact manual `/goal [condition]` command is printed afterward, along with the `/goal` / `/goal clear` status/cancel note and the auto-mode/tool-permissions reminder.
- [ ] Confirm `/goal` itself is never auto-invoked by this flow — only printed as text for the user to run.
- [ ] Spot-check the condition text is phrased as something Claude's own output can demonstrate (a test result, exit code, file count) rather than something requiring the evaluator to independently run commands or read files.
- [ ] Confirm the condition stays at or under 4,000 characters (or that the plan correctly prompts to cut detail when a draft runs over).
