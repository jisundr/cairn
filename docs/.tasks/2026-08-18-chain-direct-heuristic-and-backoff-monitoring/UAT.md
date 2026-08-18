# UAT Checklist: chain-direct-heuristic-and-backoff-monitoring

Manual verification for two documentation-only changes: (1) a Chain-vs-Direct
regression-risk routing heuristic added to `CLAUDE.md`, and (2) a backoff-paced
no-target `/loop` monitoring mode added to `commands/cairn-run-task.md`.

## Chain-vs-Direct routing heuristic (CLAUDE.md)

- [ ] Run a `brainstorm-first` request whose resulting plan modifies an
      *existing* file's behavior (not just an append). Confirm the invoking
      session reads the plan's `### Task N:` Files sections, recommends
      **Chain flow**, and presents that recommendation via one
      `AskUserQuestion` (never silently picks a flow).
- [ ] Run a `brainstorm-first` request whose resulting plan is `Create:`-only
      or purely additive `Modify:`. Confirm the session recommends **Direct
      flow with `task-orchestrator` Lightweight Start**, again via
      `AskUserQuestion`.
- [ ] Confirm a `proceed-directly` request (task type `bug-fix`/`decision`)
      skips the heuristic entirely and goes straight to Direct flow, with no
      plan file involved.
- [ ] Read `CLAUDE.md`'s new paragraph plus the `- **Direct flow**` and
      `- **Chain flow**` bullets immediately below it — confirm they read
      consistently (no contradiction between the heuristic's redirect and
      each bullet's opening clause).

## Backoff monitoring loop (commands/cairn-run-task.md)

- [ ] Run `/cairn-run-task` with no target while at least one Unattended task
      is at a non-terminal `Phase`. Confirm it enters backoff-loop mode
      rather than falling back to "which task?" disambiguation.
- [ ] Confirm the backoff cadence: first tick immediate, then 1 min, doubling
      per unchanged tick, capped at 30 min; a detected change (phase advance,
      new `HANDOFF NEEDED`, new `STALLED`, `PUBLISH`/terminal reached) fully
      resets the interval to 1 min.
- [ ] Confirm the user is notified only on a state change — an unchanged tick
      produces no notification.
- [ ] Set up a task at `Phase: HANDOFF NEEDED` with an unchanging fingerprint
      across several ticks. Confirm it is never marked `STALLED` and its
      tmux session is never killed (the core safety property — see
      `tests/smoke/test_cairn_run_task_backoff_handoff_safety.sh`).
- [ ] Set up a task whose fingerprint (`git rev-parse HEAD` + `git status
      --porcelain` + `STATE.md` `Phase`) is byte-identical for 3 consecutive
      ticks at the 30-min cap, and whose `Phase` is neither `PUBLISH` nor
      `HANDOFF NEEDED`. Confirm it is marked `STALLED` in `STATE.md`/
      `HISTORY.md` and its tmux session is killed.
- [ ] Confirm `README.md` and `CLAUDE.md` both mention the new no-target
      backoff loop mode alongside the existing single-target monitor/stale
      detection description.

## General

- [ ] `claude plugin validate . --strict` passes.
- [ ] `pytest tests/ -v -s` passes (unit tests green; eval suite at or above
      its aggregate `MIN_PASS` threshold).
- [ ] `bash tests/smoke/test_cairn_run_task_backoff_handoff_safety.sh` passes.
