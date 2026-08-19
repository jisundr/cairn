#!/usr/bin/env bash
#
# goal-guard.sh — warns when /goal is pointed directly at a raw
# implementation plan instead of a proper goal file (the *-goal.md
# convention plan-writing itself produces). Non-blocking, best-effort:
# exits 0 in every case, same philosophy as check-setup.sh/log-version.sh.
#
set -uo pipefail

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat)
prompt=$(printf '%s' "$input" | jq -r '.prompt // empty')
[[ -z "$prompt" ]] && exit 0

# Only match "/goal <something ending in .md>" -- any other /goal form (a
# plain condition sentence, /goal with no args, /goal clear) is expected
# usage, not the misuse this guards against.
if [[ "$prompt" =~ ^/goal[[:space:]]+([^[:space:]]+\.md)([[:space:]]|$) ]]; then
  path="${BASH_REMATCH[1]}"
else
  exit 0
fi

# Only warn for a path under docs/.plans/ that doesn't already look like a
# goal file.
case "$path" in
  docs/.plans/*-goal.md) exit 0 ;;
  docs/.plans/*.md) ;;
  *) exit 0 ;;
esac

slug=$(basename "$path" .md)
sibling="docs/.plans/${slug}-goal.md"
if [[ -f "$sibling" ]]; then
  hint=" A goal file already exists for this plan at ${sibling} -- did you mean to run /goal with that file's condition instead?"
else
  hint=" No goal file exists for this plan yet -- plan-writing can draft one, or run /cairn-run-task ${slug} to execute the plan directly."
fi

context="/goal sets a completion condition for autonomous looping -- it does not execute a plan. ${path} looks like a raw implementation plan, not a goal condition.${hint}"
printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$context"
