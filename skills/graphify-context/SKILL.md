---
name: graphify-context
description: Detection contract and query guidance for Graphify, a soft-optional third-party code-graph tool. Loaded by 8 cairn agents (codebase-auditor, qa-auditor, solution-architect, documentation-auditor, harness-engineer, software-engineer, qa-engineer, task-orchestrator) at the point they'd otherwise reach straight for Read/Glob/Grep. Never reimplements Graphify itself — documents how to detect it, when a graph query beats a plain file read, and the discipline for treating its output as advisory, not fact.
---

# Graphify Context — shared detection and query guidance

Graphify (`Graphify-Labs/graphify`) is a globally-installed third-party code-graph tool, never shipped or reimplemented by cairn — same "hard-required, never reimplemented" family as `superpowers`/`marketing-skills`, except here the requirement level is **soft**: every agent that loads this skill degrades silently to its own existing `Read`/`Glob`/`Grep` approach if Graphify isn't installed. See `${CLAUDE_PLUGIN_ROOT}/docs/.specs/2026-08-16-graphify-integration-design.md` for the full rationale and scope decision — a bare `docs/...` path would resolve against the consuming project's cwd, not the plugin's install location, and fail.

## Detection contract

Graphify registers globally at `~/.claude/skills/graphify/SKILL.md` — not project-vendored, unlike Impeccable or the Emil Kowalski skills, so the check is a `Skill` invocation, never a `Glob`.

1. Attempt `Skill(skill: "graphify")` once.
2. **If it fails** (not installed) — skip silently, proceed with the calling agent's normal `Read`/`Glob`/`Grep` approach. Never `ABORT`, never emit a `HARNESS FLAG:` for its absence — a missing third-party skill is expected steady-state, not a fault.
3. **If it succeeds** — use it per the guidance below for the rest of the calling step, then return control to the agent's normal flow.

## Known limitations

The exact skill name (`graphify`) and invocation shape documented above were not ground-truthed against an actual Graphify install at the time this integration was written — if the real skill registers under a different name, every attempt in step 1 above simply fails and falls back per step 2, so the blast radius of a wrong name is a silent no-op, never a break. Separately, if Graphify's own skill drives its CLI via `Bash`, the pass is a structural no-op in any calling agent that doesn't carry `Bash` in its `tools:` (currently `documentation-auditor` and `solution-architect`) — this is a known gap, not a bug to work around by speculatively granting `Bash` to agents that are deliberately scoped without it.

## When to prefer a graph query over grep/Read

Prefer a graph query for a **relationship** question: symbol lookup, call-chain or blast-radius analysis, cross-file dependency mapping, or doc-to-code traceability (Graphify indexes docs/configs alongside code, not just source). Prefer `Read` directly for anything that isn't a relationship question — a graph query is not a substitute for reading a file's actual content when the task is about that file.

## Non-goal / discipline

Graph output is advisory context, never a citable fact on its own. Before presenting any graph-sourced finding, confirm it against the real `file:line` it points to — the same discipline `codebase-auditor` already applies to its own grep-level dead-code guesses (its Step 5: "label `INFO` unless corroborated"). An agent that cites a graph relationship without having read the actual file it names is not following this skill correctly.
