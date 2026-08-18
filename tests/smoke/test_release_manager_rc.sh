#!/usr/bin/env bash
# Red-phase smoke test for release-manager's rc argument path (plan Task 1
# Step 4/Step 1 frontmatter example 2; spec "RC tags" row).
#
# Same first-ever-release scratch repo as test_release_manager_baseline.sh,
# but passes "rc" so the drafted tag name should carry an -rcN suffix
# instead of a bare vX.Y.Z. Propose-stage only — see baseline script's
# header comment for why Execute isn't reachable headlessly.
#
# Usage: bash tests/smoke/test_release_manager_rc.sh <plugin-dir>
set -uo pipefail

PLUGIN_DIR="${1:?Usage: $0 <plugin-dir>}"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-release-test-rc.XXXXXX)"
trap 'rm -rf "$SCRATCH_DIR"' EXIT

cd "$SCRATCH_DIR" || exit 1
git init -q
git config user.email "test@example.com"
git config user.name "Test"
git commit --allow-empty -q -m "chore: initial commit"
mkdir -p .claude-plugin
printf '{"name":"test-plugin","version":"0.1.0"}' > .claude-plugin/plugin.json
git add .claude-plugin
git commit -q -m "feat: add plugin manifest"

OUTPUT="$(claude -p "/cairn:cairn-release rc" --plugin-dir "$PLUGIN_DIR" --permission-mode bypassPermissions --output-format text 2>&1)"
STATUS=$?

echo "===== raw output ====="
echo "$OUTPUT"
echo "======================="

FAIL=0

if ! echo "$OUTPUT" | grep -qiE "v0\.2\.0-rc[0-9]+"; then
  echo "FAIL: expected an rc-suffixed draft tag name (v0.2.0-rcN) in output when 'rc' argument is passed"
  FAIL=1
fi

if [ -n "$(git tag -l)" ]; then
  echo "FAIL: a git tag was created without confirmation"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_release_manager_rc"
  exit 0
else
  echo "FAIL: test_release_manager_rc (claude exit status was $STATUS)"
  exit 1
fi
