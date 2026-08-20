#!/usr/bin/env bash
# Smoke test for scripts/sync_dashboard_dist.sh. Pure deterministic shell,
# no LLM/tmux involved — same style as test_goal_guard.sh in this
# directory: feed the script an isolated scratch "repo" layout and assert
# on the resulting file-tree state, exit code, and stdout/stderr.
#
# The script resolves REPO_ROOT from its own file location
# ("$(dirname "${BASH_SOURCE[0]}")/.."), so it's copied into a
# scripts/sync_dashboard_dist.sh path inside the scratch dir rather than
# invoked in place — that way it operates entirely inside the scratch dir
# and never touches the real repo's dashboard/ or dashboard-dist/.
#
# Usage: bash tests/smoke/test_sync_dashboard_dist.sh [plugin-dir]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
SOURCE_SCRIPT="$PLUGIN_DIR/scripts/sync_dashboard_dist.sh"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-sync-dashboard-dist-test.XXXXXX)"
trap 'rm -rf "$SCRATCH_DIR"' EXIT

FAIL=0

mkdir -p "$SCRATCH_DIR/scripts"
cp "$SOURCE_SCRIPT" "$SCRATCH_DIR/scripts/sync_dashboard_dist.sh"
SCRATCH_SCRIPT="$SCRATCH_DIR/scripts/sync_dashboard_dist.sh"

# Case 1: fixture dashboard/dist/ exists -> synced into dashboard-dist/,
# nested files included, exits 0, prints a confirmation.
mkdir -p "$SCRATCH_DIR/dashboard/dist/assets"
echo '<html>fixture</html>' > "$SCRATCH_DIR/dashboard/dist/index.html"
echo 'body{}' > "$SCRATCH_DIR/dashboard/dist/assets/app.css"

OUT1="$(bash "$SCRATCH_SCRIPT" 2>&1)"
RC1=$?
if [ "$RC1" -ne 0 ]; then
  echo "FAIL case 1: expected exit 0, got $RC1. Output: $OUT1"
  FAIL=1
fi
if [ ! -f "$SCRATCH_DIR/dashboard-dist/index.html" ] || ! grep -q "fixture" "$SCRATCH_DIR/dashboard-dist/index.html"; then
  echo "FAIL case 1: expected dashboard-dist/index.html synced with fixture content"
  FAIL=1
fi
if [ ! -f "$SCRATCH_DIR/dashboard-dist/assets/app.css" ]; then
  echo "FAIL case 1: expected nested dashboard-dist/assets/app.css to exist"
  FAIL=1
fi
if ! echo "$OUT1" | grep -q "synced"; then
  echo "FAIL case 1: expected a confirmation message, got: $OUT1"
  FAIL=1
fi

# Case 2: a stale file already in dashboard-dist/ (not present in the
# source dashboard/dist/) is removed on the next sync — mirror semantics,
# not additive-only copy.
echo 'stale' > "$SCRATCH_DIR/dashboard-dist/stale.txt"
bash "$SCRATCH_SCRIPT" >/dev/null 2>&1
if [ -f "$SCRATCH_DIR/dashboard-dist/stale.txt" ]; then
  echo "FAIL case 2: expected stale.txt (absent from source) to be removed by sync"
  FAIL=1
fi
if [ ! -f "$SCRATCH_DIR/dashboard-dist/index.html" ]; then
  echo "FAIL case 2: expected real fixture content to still be present after re-sync"
  FAIL=1
fi

# Case 3: missing source dashboard/dist/ -> fails loudly (non-zero exit,
# explanatory message), doesn't crash with a raw stack trace.
rm -rf "$SCRATCH_DIR/dashboard"
OUT3="$(bash "$SCRATCH_SCRIPT" 2>&1)"
RC3=$?
if [ "$RC3" -eq 0 ]; then
  echo "FAIL case 3: expected non-zero exit when dashboard/dist/ is missing"
  FAIL=1
fi
if ! echo "$OUT3" | grep -q "does not exist"; then
  echo "FAIL case 3: expected an explanatory error message, got: $OUT3"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: sync_dashboard_dist.sh"
else
  echo "FAIL: sync_dashboard_dist.sh"
fi
exit $FAIL
