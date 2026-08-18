#!/usr/bin/env bash
# Red-phase smoke test for docs/.plans/2026-08-18-chain-direct-heuristic-and-backoff-monitoring.md
# Task 2 (backoff-paced /loop mode in commands/cairn-run-task.md).
#
# This is the one property in that plan most worth a real test: Doc Gate caught
# a HIGH regression twice during planning where a rewritten Stale detection
# paragraph could have let a legitimately paused `HANDOFF NEEDED` task get
# marked `STALLED` and have its tmux session killed. The shipped plan carries
# a triple-redundant carve-out for this (backoff loop mode items 3+4, the
# Stale detection paragraph, and Global Constraints) — this script exercises
# the observable safety property those carve-outs exist to guarantee:
#
#   A `Mode: Unattended` task sitting at `Phase: HANDOFF NEEDED` with an
#   unchanging fingerprint must NEVER get a `STALLED` marker written to its
#   `STATE.md` `Status` field, and its detached tmux session must NEVER be
#   killed — no matter how many times the no-target backoff check runs.
#
# It also exercises the feature's actual entry point: `/cairn-run-task`
# invoked with NO target (`$ARGUMENTS` empty) is supposed to run backoff loop
# mode over every active Unattended task silently, never asking the user to
# disambiguate which task to check. Pre-implementation, `commands/cairn-run-task.md`
# has no empty-`$ARGUMENTS` branch in Input resolution at all, so with two
# candidate tasks present the command has no defined behavior and (observed
# empirically while writing this test) the agent asks the user which task to
# run instead of silently checking both — that clarifying-question fallback is
# exactly what backoff loop mode is supposed to replace, so its absence is
# asserted below as the primary "still unimplemented" signal.
#
# Caveat shared with the sibling release-manager smoke tests: a headless
# `claude -p` call is a fresh one-shot session with no memory of a prior
# invocation, so it cannot literally drive backoff-loop-mode's internal
# multi-tick timer/memory (that state is deliberately transient to one running
# `/loop` session, never persisted to disk — see the plan's Global
# Constraints). This script simulates "multiple ticks" by invoking the command
# several times in a row against an unchanging fixture and re-checking the
# safety property after every single invocation — each call must independently
# uphold the invariant regardless of how many times it's been checked before.
#
# Usage: bash tests/smoke/test_cairn_run_task_backoff_handoff_safety.sh <plugin-dir>
set -uo pipefail

PLUGIN_DIR="${1:?Usage: $0 <plugin-dir>}"
TICKS=3
HANDOFF_BRANCH="feature/fake-handoff-task"
OTHER_BRANCH="feature/fake-other-task"

SCRATCH_DIR="$(mktemp -d /tmp/cairn-backoff-handoff-test.XXXXXX)"

cleanup() {
  tmux kill-session -t "$HANDOFF_BRANCH" >/dev/null 2>&1
  tmux kill-session -t "$OTHER_BRANCH" >/dev/null 2>&1
  rm -rf "$SCRATCH_DIR"
}
trap cleanup EXIT

cd "$SCRATCH_DIR" || exit 1
git init -q
git config user.email "test@example.com"
git config user.name "Test"
git commit --allow-empty -q -m "chore: initial commit"

mkdir -p docs/.tasks/2026-08-18-fake-handoff-task docs/.tasks/2026-08-18-fake-other-task

# Task A: Unattended, sitting at HANDOFF NEEDED — the task this script must
# never see harmed, no matter how many ticks run against it.
cat > docs/.tasks/2026-08-18-fake-handoff-task/STATE.md <<EOF
# Task: fake-handoff-task

Mode: Unattended
Phase: HANDOFF NEEDED
Handoff to: software-engineer
Status: Pending question — waiting on human answer about approach X.
Plan: docs/.plans/2026-08-18-fake-handoff-task.md
Ticket: none
Worktree: $SCRATCH_DIR/.worktrees/feature-fake-handoff-task
Branch: $HANDOFF_BRANCH
Key info: Pending question: should we use approach X or Y?
Harness flags: none
EOF
cat > docs/.tasks/2026-08-18-fake-handoff-task/HISTORY.md <<'EOF'
# History: fake-handoff-task

2026-08-18T00:00:00Z — PLAN — fixture line.
2026-08-18T00:05:00Z — QA-RED — fixture line 2.
EOF

# Task B: a second Unattended, non-terminal task in the discovery set — present
# so the no-target invocation has more than one candidate and can't trivially
# "just handle the only task there is" (which is the case a single-task
# fixture would let a not-yet-implemented command pass by accident).
cat > docs/.tasks/2026-08-18-fake-other-task/STATE.md <<EOF
# Task: fake-other-task

Mode: Unattended
Phase: QA-RED
Handoff to: software-engineer
Status: In progress.
Plan: docs/.plans/2026-08-18-fake-other-task.md
Ticket: none
Worktree: $SCRATCH_DIR/.worktrees/feature-fake-other-task
Branch: $OTHER_BRANCH
Key info: none
Harness flags: none
EOF
cat > docs/.tasks/2026-08-18-fake-other-task/HISTORY.md <<'EOF'
# History: fake-other-task

2026-08-18T00:00:00Z — PLAN — fixture line.
EOF

tmux kill-session -t "$HANDOFF_BRANCH" >/dev/null 2>&1
tmux kill-session -t "$OTHER_BRANCH" >/dev/null 2>&1
tmux new-session -d -s "$HANDOFF_BRANCH" 'sleep 600'
tmux new-session -d -s "$OTHER_BRANCH" 'sleep 600'

if ! tmux has-session -t "$HANDOFF_BRANCH" 2>/dev/null || ! tmux has-session -t "$OTHER_BRANCH" 2>/dev/null; then
  echo "FAIL: could not start fixture tmux sessions — test environment problem, not a real result"
  exit 1
fi

FAIL=0

for i in $(seq 1 "$TICKS"); do
  OUTPUT="$(claude -p "/cairn:cairn-run-task" --plugin-dir "$PLUGIN_DIR" --permission-mode bypassPermissions --output-format text 2>&1)"

  echo "===== tick $i output ====="
  echo "$OUTPUT"
  echo "==========================="

  # --- Safety property: HANDOFF NEEDED task never marked STALLED ---
  HANDOFF_STATUS_LINE="$(grep '^Status:' docs/.tasks/2026-08-18-fake-handoff-task/STATE.md)"
  if echo "$HANDOFF_STATUS_LINE" | grep -qi 'STALLED'; then
    echo "FAIL (tick $i): fake-handoff-task's STATE.md Status field was marked STALLED — a HANDOFF NEEDED task must never be stalled: $HANDOFF_STATUS_LINE"
    FAIL=1
  fi
  if grep -qi 'STALLED' docs/.tasks/2026-08-18-fake-handoff-task/HISTORY.md; then
    echo "FAIL (tick $i): fake-handoff-task's HISTORY.md recorded a STALLED entry"
    FAIL=1
  fi

  # --- Safety property: its tmux session was never killed ---
  if ! tmux has-session -t "$HANDOFF_BRANCH" 2>/dev/null; then
    echo "FAIL (tick $i): tmux session for $HANDOFF_BRANCH was killed — a HANDOFF NEEDED task's detached session must never be torn down"
    FAIL=1
    # Recreate so later ticks can still meaningfully check for a repeat kill.
    tmux new-session -d -s "$HANDOFF_BRANCH" 'sleep 600' >/dev/null 2>&1
  fi

  # --- Feature-present signal: no-target run must not fall back to asking
  # the user which task to check (that's the pre-implementation behavior;
  # backoff loop mode processes every active Unattended task itself). ---
  if echo "$OUTPUT" | grep -qiE 'which (one|task)|please (specify|provide)'; then
    echo "FAIL (tick $i): command asked the user to disambiguate which task to run instead of running backoff loop mode over all active Unattended tasks — empty-\$ARGUMENTS backoff loop mode is not implemented yet"
    FAIL=1
  fi

  # Sanity: the second (non-HANDOFF-NEEDED) task's session must survive too —
  # nothing here should be stalled given both fingerprints are unchanging
  # across ticks.
  if ! tmux has-session -t "$OTHER_BRANCH" 2>/dev/null; then
    echo "FAIL (tick $i): tmux session for $OTHER_BRANCH was killed unexpectedly"
    FAIL=1
    tmux new-session -d -s "$OTHER_BRANCH" 'sleep 600' >/dev/null 2>&1
  fi
done

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_cairn_run_task_backoff_handoff_safety"
  exit 0
else
  echo "FAIL: test_cairn_run_task_backoff_handoff_safety"
  exit 1
fi
