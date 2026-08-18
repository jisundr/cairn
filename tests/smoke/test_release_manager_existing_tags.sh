#!/usr/bin/env bash
# Red-phase smoke test for release-manager's Detect step on a repo that
# already has a prior release tag (plan Task 1 Step 4 Flow item 1:
# `git describe --tags --abbrev=0`; spec Flow step 1).
#
# The plan's own Task 1 Step 7 baseline only covers the no-tags-yet
# bootstrap path (diff from the first commit). This scenario seeds a prior
# v0.1.0 tag with a distinctive pre-tag commit, then a distinctive
# post-tag feat: commit, and asserts the gathered evidence/changelog draft
# reflects only what changed *since* v0.1.0 — proving Detect uses the tag,
# not the repo's first commit, once a tag exists.
#
# Usage: bash tests/smoke/test_release_manager_existing_tags.sh <plugin-dir>
set -uo pipefail

PLUGIN_DIR="${1:?Usage: $0 <plugin-dir>}"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-release-test-existingtags.XXXXXX)"
trap 'rm -rf "$SCRATCH_DIR"' EXIT

cd "$SCRATCH_DIR" || exit 1
git init -q
git config user.email "test@example.com"
git config user.name "Test"
git commit --allow-empty -q -m "chore: pretag marker commit"
mkdir -p .claude-plugin
printf '{"name":"test-plugin","version":"0.1.0"}' > .claude-plugin/plugin.json
git add .claude-plugin
git commit -q -m "feat: pretag plugin manifest"
git tag v0.1.0
git commit --allow-empty -q -m "feat: posttag distinctive feature"

OUTPUT="$(claude -p "/cairn:cairn-release" --plugin-dir "$PLUGIN_DIR" --permission-mode bypassPermissions --output-format text 2>&1)"
STATUS=$?

echo "===== raw output ====="
echo "$OUTPUT"
echo "======================="

FAIL=0

if ! echo "$OUTPUT" | grep -qi "posttag"; then
  echo "FAIL: expected the post-tag commit ('posttag distinctive feature') to appear in the gathered evidence/changelog draft"
  FAIL=1
fi

if echo "$OUTPUT" | grep -qi "pretag"; then
  echo "FAIL: pre-tag commits ('pretag marker commit'/'pretag plugin manifest') should NOT appear — Detect should diff since v0.1.0, not from the repo's first commit"
  FAIL=1
fi

if ! echo "$OUTPUT" | grep -qiE "0\.2\.0"; then
  echo "FAIL: expected proposed version 0.2.0 (minor bump from the v0.1.0 tag baseline)"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_release_manager_existing_tags"
  exit 0
else
  echo "FAIL: test_release_manager_existing_tags (claude exit status was $STATUS)"
  exit 1
fi
