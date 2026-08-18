#!/usr/bin/env bash
# Red-phase smoke test for release-manager (Task 1) / /cairn-release (Task 2).
#
# Mirrors docs/.plans/2026-08-18-release-manager.md Task 1 Step 7 exactly:
# first-ever release (no tags yet), one feat: commit since the first commit.
# Covers Detect -> Harness Check -> Gather Evidence -> Propose only — headless
# `-p` runs stop at the AskUserQuestion confirmation, so Execute (actual
# tag/push, version-match validation, commit-before-tag ordering) is NOT
# exercised by this script. See test_release_manager_tag_collision.sh,
# test_release_manager_rc.sh, test_release_manager_existing_tags.sh, and
# test_release_manager_harness_override.sh for the other Propose-stage
# scenarios qa-engineer added at red phase.
#
# Usage: bash tests/smoke/test_release_manager_baseline.sh <plugin-dir>
set -uo pipefail

PLUGIN_DIR="${1:?Usage: $0 <plugin-dir>}"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-release-test-baseline.XXXXXX)"
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

OUTPUT="$(claude -p "/cairn:cairn-release" --plugin-dir "$PLUGIN_DIR" --permission-mode bypassPermissions --output-format text 2>&1)"
STATUS=$?

echo "===== raw output ====="
echo "$OUTPUT"
echo "======================="

FAIL=0

if ! echo "$OUTPUT" | grep -qiE "0\.2\.0"; then
  echo "FAIL: expected proposed version 0.2.0 (minor bump from 0.1.0 for a feat: commit) in output"
  FAIL=1
fi

if ! echo "$OUTPUT" | grep -qiE "changelog"; then
  echo "FAIL: expected a changelog draft mention in output"
  FAIL=1
fi

if ! echo "$OUTPUT" | grep -qiE "v0\.2\.0"; then
  echo "FAIL: expected draft tag name v0.2.0 in output"
  FAIL=1
fi

# Nothing should be written before confirmation.
if [ -f CHANGELOG.md ]; then
  echo "FAIL: CHANGELOG.md was written without confirmation"
  FAIL=1
fi
if ! grep -q '"version":"0.1.0"' .claude-plugin/plugin.json 2>/dev/null && ! grep -q '"version": "0.1.0"' .claude-plugin/plugin.json 2>/dev/null; then
  echo "FAIL: .claude-plugin/plugin.json version was modified without confirmation"
  FAIL=1
fi
if [ -n "$(git tag -l)" ]; then
  echo "FAIL: a git tag was created without confirmation"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_release_manager_baseline"
  exit 0
else
  echo "FAIL: test_release_manager_baseline (claude exit status was $STATUS)"
  exit 1
fi
