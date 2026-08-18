#!/usr/bin/env bash
# Red-phase smoke test for release-manager's .harness/ override behavior
# (plan Task 1 Step 3 HARD REQUIREMENTS: "ALWAYS read .harness/workflow.md
# ... if present, before drafting — a documented convention there overrides
# this agent's defaults"; spec Flow step 2 "Harness check").
#
# Seeds .harness/workflow.md with a non-default tag-naming convention
# ("release-X.Y.Z" instead of "vX.Y.Z") in the scratch repo and asserts the
# drafted tag name in the Propose-stage output follows that convention
# instead of the agent's own vX.Y.Z default.
#
# Usage: bash tests/smoke/test_release_manager_harness_override.sh <plugin-dir>
set -uo pipefail

PLUGIN_DIR="${1:?Usage: $0 <plugin-dir>}"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-release-test-harness.XXXXXX)"
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

mkdir -p .harness
cat > .harness/workflow.md <<'EOF'
# Workflow conventions

## Release tags

This project's release tags use the format `release-X.Y.Z` (no leading
`v`, prefixed with `release-` instead) rather than the generic `vX.Y.Z`
default. Always use this format when cutting a release tag.
EOF
git add .harness
git commit -q -m "chore: add harness workflow conventions"

OUTPUT="$(claude -p "/cairn:cairn-release" --plugin-dir "$PLUGIN_DIR" --permission-mode bypassPermissions --output-format text 2>&1)"
STATUS=$?

echo "===== raw output ====="
echo "$OUTPUT"
echo "======================="

FAIL=0

if ! echo "$OUTPUT" | grep -qiE "release-0\.2\.0"; then
  echo "FAIL: expected drafted tag name to follow .harness/workflow.md's 'release-X.Y.Z' convention (release-0.2.0), not the vX.Y.Z default"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_release_manager_harness_override"
  exit 0
else
  echo "FAIL: test_release_manager_harness_override (claude exit status was $STATUS)"
  exit 1
fi
