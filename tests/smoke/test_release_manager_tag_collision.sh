#!/usr/bin/env bash
# Red-phase smoke test for release-manager's tag-collision hard stop
# (plan Task 1 Step 3 HARD REQUIREMENTS "NEVER create a tag that already
# exists"; EXIT & DERAILMENT row "Proposed tag already exists").
#
# Pre-creates a tag matching the version that would otherwise be proposed
# (v0.2.0, from a 0.1.0 baseline plus one feat: commit), then confirms the
# agent's report flags the collision explicitly rather than silently
# re-proposing v0.2.0 as if uncontested, and that nothing further was
# written. This only exercises the collision *detection* surfaced in the
# Propose-stage report — the Execute-step "hard stop before writing
# anything" re-validation cannot be exercised headlessly (see baseline
# script's header comment); this script only proves detection happens
# before the confirmation is even reached, which is the strongest signal
# available without an interactive AskUserQuestion answer.
#
# Usage: bash tests/smoke/test_release_manager_tag_collision.sh <plugin-dir>
set -uo pipefail

PLUGIN_DIR="${1:?Usage: $0 <plugin-dir>}"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-release-test-collision.XXXXXX)"
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
git tag v0.1.0
git commit --allow-empty -q -m "feat: add another feature"
# Pre-create the colliding tag that would otherwise be proposed next.
git tag v0.2.0

OUTPUT="$(claude -p "/cairn:cairn-release" --plugin-dir "$PLUGIN_DIR" --permission-mode bypassPermissions --output-format text 2>&1)"
STATUS=$?

echo "===== raw output ====="
echo "$OUTPUT"
echo "======================="

FAIL=0

if ! echo "$OUTPUT" | grep -qiE "collis|already exist|conflict"; then
  echo "FAIL: expected output to flag the v0.2.0 tag collision explicitly"
  FAIL=1
fi

# The pre-existing tag must be untouched (still points at the same commit)
# and no new tag was added.
TAG_COUNT="$(git tag -l | wc -l | tr -d ' ')"
if [ "$TAG_COUNT" != "2" ]; then
  echo "FAIL: expected exactly the 2 pre-seeded tags (v0.1.0, v0.2.0), found $TAG_COUNT"
  FAIL=1
fi

if [ -f CHANGELOG.md ]; then
  echo "FAIL: CHANGELOG.md was written without confirmation"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_release_manager_tag_collision"
  exit 0
else
  echo "FAIL: test_release_manager_tag_collision (claude exit status was $STATUS)"
  exit 1
fi
