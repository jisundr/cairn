#!/usr/bin/env bash
#
# log-version.sh — records which cairn version was active for this
# session, so the usage dashboard can show a version column per session.
# Runs on SessionStart (fires once per session). The session transcript
# itself records the Claude Code CLI version but not the cairn plugin
# version, so this is the only source of that data.
#
set -uo pipefail

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
plugin_json="$root/.claude-plugin/plugin.json"

command -v jq >/dev/null 2>&1 || exit 0
[[ -f "$plugin_json" ]] || exit 0

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
[[ -z "$session_id" ]] && exit 0

version=$(jq -r '.version // "unknown"' "$plugin_json")
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p .cairn
printf '{"session_id":"%s","timestamp":"%s","version":"%s"}\n' \
  "$session_id" "$timestamp" "$version" >> .cairn/version-log.jsonl
