#!/usr/bin/env bash
# Runs every release-manager headless smoke test in this directory against
# a given plugin dir (defaults to the repo root two levels up from this
# script, i.e. this worktree) and reports a pass/fail summary.
#
# Usage: bash tests/smoke/run_all.sh [plugin-dir]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

TESTS=(
  test_release_manager_baseline.sh
  test_release_manager_rc.sh
  test_release_manager_tag_collision.sh
  test_release_manager_existing_tags.sh
  test_release_manager_harness_override.sh
)

PASS=0
FAIL=0
FAILED_NAMES=()

for t in "${TESTS[@]}"; do
  echo "### Running $t ###"
  if bash "$SCRIPT_DIR/$t" "$PLUGIN_DIR"; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("$t")
  fi
  echo
done

echo "===== summary ====="
echo "Passed: $PASS / $((PASS + FAIL))"
if [ "$FAIL" -gt 0 ]; then
  echo "Failed:"
  for n in "${FAILED_NAMES[@]}"; do
    echo "  - $n"
  done
  exit 1
fi
exit 0
