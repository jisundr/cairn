#!/usr/bin/env bash
#
# log-version.sh — records which cairn version was active for this
# session, so the usage dashboard can show a version column per session.
# Runs on SessionStart (fires once per session). The session transcript
# itself records the Claude Code CLI version but not the cairn plugin
# version, so this is the only source of that data.
#
# Only does anything if the project has actually run /cairn-setup (the
# <!-- cairn:start --> marker is present in root CLAUDE.md) -- cairn
# shouldn't create .cairn/ in every project it happens to be installed
# in, only ones that opted in.
#
set -uo pipefail

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
plugin_json="$root/.claude-plugin/plugin.json"

[[ -f CLAUDE.md ]] || exit 0
grep -qxF '<!-- cairn:start -->' CLAUDE.md || exit 0

command -v jq >/dev/null 2>&1 || exit 0
[[ -f "$plugin_json" ]] || exit 0

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
[[ -z "$session_id" ]] && exit 0

version=$(jq -r '.version // "unknown"' "$plugin_json")
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p .cairn
[[ -f .cairn/.gitignore ]] || printf '*\n' > .cairn/.gitignore
printf '{"session_id":"%s","timestamp":"%s","version":"%s"}\n' \
  "$session_id" "$timestamp" "$version" >> .cairn/version-log.jsonl
