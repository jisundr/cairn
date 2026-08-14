#!/usr/bin/env bash
#
# check-setup.sh — fast, non-blocking sanity check on cairn's plugin content.
# Runs on SessionStart (there's no dedicated post-install/post-upgrade hook
# event in Claude Code, so SessionStart is the closest equivalent — it fires
# on the next session after an install or upgrade, and every session after).
# Structural only: no LLM calls, no cost. Behavioral routing correctness is
# covered separately by tests/test_intent_routing.py.
#
set -uo pipefail

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
problems=()

check_agent_frontmatter() {
  local file=$1 name=$2
  if [[ ! -f "$file" ]]; then
    problems+=("agents/${name}.md missing")
    return
  fi
  local field
  for field in name description tools model; do
    grep -qE "^${field}:" "$file" || problems+=("agents/${name}.md missing '${field}:' in frontmatter")
  done
  grep -q "^ROUTING DECISION" "$root/agents/${name}.md" \
    || problems+=("agents/${name}.md has no ROUTING DECISION contract")
}

check_agent_frontmatter "$root/agents/intent-analyzer.md" "intent-analyzer"

if [[ ${#problems[@]} -eq 0 ]]; then
  exit 0
fi

joined=$(IFS='; '; echo "${problems[*]}")
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"cairn setup check found issues: %s"}}\n' "$joined"
