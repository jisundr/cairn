#!/usr/bin/env bash
# Red-phase smoke test for pr-reviewer (plan Task 1: Input Resolution +
# Initial Review mode), GitHub path.
#
# Real public target: octocat/Hello-World PR #1 (per plan Task 4 Step 6 --
# the one live verification for the code-review name-collision residual
# risk: Claude Code's built-in code-review capability vs. an unrelated
# always-posts community marketplace plugin sharing the same name). Written
# at red phase per that step's own instruction to treat this as a real
# test, not optional -- scoped here to what Task 1 alone delivers (Input
# Resolution + Initial Review's findings/draft/save; the Confirmation &
# Posting Phase itself is only a Task 4 TODO placeholder in Task 1, so no
# posting should happen regardless of which code-review resolves yet).
#
# Confirms:
#   1. pr-reviewer's own Initial Review Draft Phase actually ran (not a
#      generic fallback / unrelated response from --plugin-dir pointing at
#      the wrong tree, and not the orchestrating session just answering
#      inline instead of dispatching the subagent) -- verified via the
#      deterministic docs/.reviews/<host>-<owner-repo>-<number>.md artifact
#      path and its Draft Phase content shape, NOT by grepping the outer
#      CLI's paraphrased/compressed final text. The prompt below names the
#      agent explicitly and passes a full URL: bare-number prompts like
#      "review PR #1 on this repo" were empirically found to trigger
#      Agent-tool dispatch only ~2/7 of the time in live testing, making a
#      text-output-based assertion pass/fail on dispatch luck rather than
#      agents/pr-reviewer.md's actual correctness.
#   2. Findings come from Skill(skill: "code-review", ...) WITHOUT
#      --comment -- draft/save happens locally, nothing is posted. Comment
#      count on the real PR must be identical before and after; if it
#      changed, the WRONG code-review resolved (the marketplace plugin) --
#      the accepted-residual-risk scenario documented in the plan's
#      EXIT & DERAILMENT table (Task 4 Step 3).
#   3. The draft is auto-saved to docs/.reviews/ (Hard Requirement --
#      mandatory, not itself a gate) using this target's identity, in the
#      expected Draft Phase shape (a `## Finding N -- ...` heading per
#      finding, or an explicit no-findings note).
#   4. The target's source branch (patch-1) is never checked out locally
#      (Hard Requirement -- fetch only).
#
# Usage: bash tests/smoke/test_pr_reviewer_github_initial_review.sh <plugin-dir>
set -uo pipefail

PLUGIN_DIR="${1:?Usage: $0 <plugin-dir>}"
SCRATCH_DIR="$(mktemp -d /tmp/cairn-pr-reviewer-test-github.XXXXXX)"
trap 'rm -rf "$SCRATCH_DIR"' EXIT

cd "$SCRATCH_DIR" || exit 1
git init -q
git config user.email "test@example.com"
git config user.name "Test"
git commit --allow-empty -q -m "chore: initial commit"
git remote add origin https://github.com/octocat/Hello-World.git

BEFORE_COUNT="$(gh pr view 1 --repo octocat/Hello-World --json comments --jq '.comments | length' 2>&1)"
if ! [[ "$BEFORE_COUNT" =~ ^[0-9]+$ ]]; then
  echo "SKIP: could not read baseline comment count from octocat/Hello-World#1 (gh output: $BEFORE_COUNT) -- network/auth issue, not a pr-reviewer defect"
  exit 0
fi

STARTING_BRANCH="$(git branch --show-current)"

OUTPUT="$(claude -p "Use the pr-reviewer agent to review https://github.com/octocat/Hello-World/pull/1" --plugin-dir "$PLUGIN_DIR" --permission-mode bypassPermissions --output-format text 2>&1)"
STATUS=$?

echo "===== raw output (informational only -- assertions below check the docs/.reviews/ artifact instead) ====="
echo "$OUTPUT"
echo "======================="

AFTER_COUNT="$(gh pr view 1 --repo octocat/Hello-World --json comments --jq '.comments | length' 2>&1)"
CURRENT_BRANCH="$(git branch --show-current)"

FAIL=0

EXPECTED_DRAFT="docs/.reviews/github-octocat-Hello-World-1.md"
if [ ! -f "$EXPECTED_DRAFT" ]; then
  echo "FAIL: expected a mandatory-saved draft at $EXPECTED_DRAFT (host-owner-repo-number naming) -- found none. This is the positive evidence that pr-reviewer's own Initial Review mode actually ran (not a generic fallback, and not the orchestrating session skipping subagent dispatch)."
  FAIL=1
else
  DRAFT_CONTENT="$(cat "$EXPECTED_DRAFT")"
  # Order-independent zero-findings check: pr-reviewer.md's Draft Phase only
  # mandates literal wording for the CHAT-PRESENTED first line -- the saved
  # docs/.reviews/ file's zero-findings note is deliberately unconstrained in
  # exact phrasing ("0 findings", "No findings", "Zero findings", "Findings: 0",
  # "Finding count: 0", etc.), so this checks per-line for the word "finding"
  # co-occurring with a standalone no/0/zero token in either order, rather than
  # requiring the zero-indicator immediately before "finding(s)".
  SHAPE_OK=0
  if echo "$DRAFT_CONTENT" | grep -qiE '^## Finding [0-9]+'; then
    SHAPE_OK=1
  elif echo "$DRAFT_CONTENT" | grep -iE 'finding' | grep -qiE '(^|[^a-zA-Z])(no|0|zero)([^a-zA-Z]|$)'; then
    SHAPE_OK=1
  fi
  if [ -z "$DRAFT_CONTENT" ]; then
    echo "FAIL: $EXPECTED_DRAFT exists but is empty"
    FAIL=1
  elif [ "$SHAPE_OK" != "1" ]; then
    echo "FAIL: $EXPECTED_DRAFT doesn't match pr-reviewer's own Draft Phase format (expected a '## Finding N -- ...' heading per finding, or an explicit no-findings note). Content:"
    echo "$DRAFT_CONTENT"
    FAIL=1
  fi
fi

if [ "$CURRENT_BRANCH" != "$STARTING_BRANCH" ]; then
  echo "FAIL: local branch changed from '$STARTING_BRANCH' to '$CURRENT_BRANCH' -- pr-reviewer must never check out the target's source branch (fetch only)"
  FAIL=1
fi

if [[ "$AFTER_COUNT" =~ ^[0-9]+$ ]] && [ "$AFTER_COUNT" != "$BEFORE_COUNT" ]; then
  echo "FAIL: comment count changed on octocat/Hello-World#1 ($BEFORE_COUNT -> $AFTER_COUNT) -- code-review posted without --comment, or the wrong (marketplace) code-review resolved. STOP -- this is the accepted-residual-risk scenario from the plan's EXIT & DERAILMENT table; do not retry against the real PR."
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "PASS: test_pr_reviewer_github_initial_review"
  exit 0
else
  echo "FAIL: test_pr_reviewer_github_initial_review (claude exit status was $STATUS)"
  exit 1
fi
