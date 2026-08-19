#!/usr/bin/env bash
# Smoke test for hooks/scripts/goal-guard.sh. Pure deterministic shell, no
# LLM involved — unlike the release-manager smoke tests in this directory
# (which invoke `claude -p` because they test LLM judgment), this feeds
# fixture stdin JSON straight to the hook script and asserts exact
# stdout/exit code per case.
#
# Usage: bash tests/smoke/test_goal_guard.sh [plugin-dir]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
HOOK="$PLUGIN_DIR/hooks/scripts/goal-guard.sh"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-goal-guard-test.XXXXXX)"
trap 'rm -rf "$SCRATCH_DIR"' EXIT

FAIL=0

run_hook() {
  # $1 = prompt text
  jq -n --arg prompt "$1" '{prompt: $prompt}' | (cd "$SCRATCH_DIR" && "$HOOK")
}

# Case 1: raw plan path, no sibling goal file -> warns, mentions no goal file exists
mkdir -p "$SCRATCH_DIR/docs/.plans"
: > "$SCRATCH_DIR/docs/.plans/2026-01-01-foo.md"
OUT1="$(run_hook '/goal docs/.plans/2026-01-01-foo.md')"
if ! echo "$OUT1" | grep -q "does not execute a plan"; then
  echo "FAIL case 1: expected explanatory warning, got: $OUT1"
  FAIL=1
fi
if ! echo "$OUT1" | grep -q "No goal file exists"; then
  echo "FAIL case 1: expected 'no goal file exists' hint, got: $OUT1"
  FAIL=1
fi

# Case 2: raw plan path, sibling goal file present -> warns, points at the sibling
: > "$SCRATCH_DIR/docs/.plans/2026-01-01-foo-goal.md"
OUT2="$(run_hook '/goal docs/.plans/2026-01-01-foo.md')"
if ! echo "$OUT2" | grep -q "2026-01-01-foo-goal.md"; then
  echo "FAIL case 2: expected the sibling goal file to be named, got: $OUT2"
  FAIL=1
fi

# Case 3: a proper goal file itself -> no warning
OUT3="$(run_hook '/goal docs/.plans/2026-01-01-foo-goal.md')"
if [ -n "$OUT3" ]; then
  echo "FAIL case 3: expected no output for a proper goal file, got: $OUT3"
  FAIL=1
fi

# Case 4: /goal with a plain condition sentence, not a path -> no warning
OUT4="$(run_hook '/goal all tests pass')"
if [ -n "$OUT4" ]; then
  echo "FAIL case 4: expected no output for a non-path condition, got: $OUT4"
  FAIL=1
fi

# Case 5: /goal pointed at an .md file outside docs/.plans/ -> no warning
OUT5="$(run_hook '/goal README.md')"
if [ -n "$OUT5" ]; then
  echo "FAIL case 5: expected no output for a path outside docs/.plans/, got: $OUT5"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_goal_guard"
  exit 0
else
  echo "FAIL: test_goal_guard"
  exit 1
fi
