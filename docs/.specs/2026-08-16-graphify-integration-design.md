# Design: Graphify integration — shared codebase/docs graph capability

## Summary

Adds Graphify (`Graphify-Labs/graphify`) as a soft-optional, shared code-graph capability available to eight cairn agents that read source and documentation as part of their work. A new thin skill, `cairn:graphify-context`, documents the detection contract and query guidance; it is not a reimplementation of Graphify itself, matching the "hard-required, never reimplemented" family cairn already uses for third-party tools (`idea-explorer` → `superpowers`, `market-researcher` → `marketing-skills`) — except here the requirement level is soft, not hard.

Nothing in this design hard-requires Graphify. Every integration point degrades silently to the agent's existing `Read`/`Glob`/`Grep` approach if Graphify isn't installed.

## Scope decision

The originating question was "code graph or Graphify, which is better" against `codebase-auditor`'s CLAUDE.md note that a prior maestro port dropped a "codegraph MCP dependency" as YAGNI. Three points were decided in sequence:

| Decision | Chosen | Why |
|---|---|---|
| Use case | General-purpose — any agent that reads codebases/docs, not one agent | User's explicit framing: "so that any agents can benefit when reading codebases and docs." |
| Requirement level | Soft-optional | Hard-requiring across 8 agents would make a single 4-month-old external tool load-bearing for most of cairn's read-heavy agents at once. Matches the existing precedent for exactly this kind of bet (`product-designer`'s Design Quality Pass, `software-engineer`'s Frontend Polish Pass) rather than the precedent for a stable, long-hard-required dependency (`superpowers`, `marketing-skills`). |
| Tool | Graphify (`Graphify-Labs/graphify`) | See ground-truthing below. User's explicit choice after investigation found no evidence of malicious tooling. |

Two narrower alternatives were considered and rejected before landing on the shared, soft-optional design:

| Option considered | Why not |
|---|---|
| Narrow: wire only into `codebase-auditor`'s dead-code step + `qa-auditor`'s impact analysis | Smaller diff, but doesn't match the user's stated intent — those are the two spots with a *documented* prior weakness, but the user explicitly wants the capability available anywhere an agent reads code or docs, not just those two. |
| New standalone `code-graph-analyst` agent, zero changes to existing agents | Purely additive, but doesn't actually upgrade any existing agent's weak step — just adds a parallel option next to it. Doesn't match "any agent... when reading" either, since nothing changes about how the other 8 agents read. |

## Investigated and rejected candidates, ground-truthed

Two other candidates surfaced during comparison research were excluded after investigation:

**Graphify itself initially triggered a flag** before being cleared: 106,726 stars on a repo created 2026-04-03 (~4.5 months old, ~790 stars/day sustained), against only 357 watchers and 10,382 forks — a star/growth-rate profile that resembles known bot-inflation patterns. A cluster of near-identical "X vs Y vs Z" comparison articles across Medium, dev.to, and several low-authority blogs (all promoting the same tool names) compounded the concern. Direct investigation reversed the initial caution: commit history is real and technically substantial (dozens of distinct GitHub contributors, detailed fix commits addressing genuine AST edge cases — generator function-expression shadowing, `.gitignore`-vs-git-tracked file resolution, `CLAUDE_CONFIG_DIR` handling), `pyproject.toml` has only ordinary `console_scripts` entries (no postinstall hooks), and a `[tool.bandit]` security-lint config is present. One sibling repo in the same family, `tirth8205/code-review-graph` (30,265 stars, similarly fast growth), showed the same pattern — including a commit titled *"docs(benchmarks): replace unverified claims with measured numbers,"* a good-faith self-correction signal. Neither repo shows evidence of supply-chain compromise; the anomalous star velocity is most plausibly explained by AI-accelerated development velocity (both repos carry heavy `Co-Authored-By: Claude Opus 4.8` commit trailers) driving unusually fast organic growth in the current environment, not fraud. Residual risk from youth (4–6 months) still applies — normal caution (pin a version, avoid blind `curl | sh`) is warranted, but this is not a reason to exclude the tool.

**`GitNexus` (`CodeWithJames-AI/gitnexus`)** was checked directly: 3 actual stars on GitHub against an earlier blog claim of "28.9k stars" — the mismatch confirms the blog aggregator content is unreliable and was excluded as a source of truth for this design.

## The candidates, ground-truthed

Verified directly via the GitHub API (`gh api repos/<owner>/<repo>`), not blog claims:

| Tool | Stars | Age | License | Approach | Notes |
|---|---|---|---|---|---|
| **Graphify** (chosen) | 106,726 | 4mo | Apache-2.0 / MIT (dual) | Tree-sitter → flat files (`graph.json`, `GRAPH_REPORT.md`), no vector store, no graph DB | `pip`/`uv` install; registers a `/graphify` Claude Code skill directly; MCP server via `graphify --mcp` |
| `oraios/serena` | 28,074 | 17mo | MIT | Real LSP language servers (symbol-level, not a persistent graph) | Mature, organic growth; different mechanism entirely — considered, not chosen, since the user wants a graph model |
| `CodeGraphContext` | 4,084 | 12mo | MIT | Tree-sitter → graph DB (FalkorDB/Kuzu/Neo4j) | Organic growth, smaller community |
| `codegraph-ai/CodeGraph` | 63 | 4mo | Apache-2.0 | Tree-sitter → RocksDB, 42 MCP tools | The other name from the original question; smallest community |

## `cairn:graphify-context` — the shared skill

New skill under `skills/graphify-context/SKILL.md`. Not invoked as a standalone user-facing capability — loaded by each of the 8 agents below at the point they'd otherwise reach straight for `Read`/`Glob`/`Grep`.

**Detection contract:** Graphify registers globally at `~/.claude/skills/graphify/SKILL.md` (not project-vendored, unlike Impeccable or the Emil Kowalski skills) — attempt `Skill(skill: "graphify")`. If the invocation fails, skip silently and proceed with the agent's normal `Read`/`Glob`/`Grep` approach. Never `ABORT`, never emit a `HARNESS FLAG:` for its absence — same rule the Frontend Polish Pass already established for missing third-party skills.

**When to prefer a graph query over grep/Read:** symbol lookup, call-chain / blast-radius analysis, cross-file dependency mapping, and doc-to-code traceability (Graphify indexes docs/configs alongside code, not just source). Prefer `Read` directly for anything that isn't a relationship question — a graph query is not a substitute for reading the actual file when the task is about that file's content.

**Non-goal / discipline:** graph output is advisory context, not a citable fact. An agent must always be able to point to the real `file:line` behind any graph-sourced finding — the same rule `codebase-auditor` already applies to its own grep-level dead-code guesses (Step 5's "label `INFO` unless corroborated").

## Components — one soft-optional addition per agent

Each of the 8 additions below follows the same shape: *attempt `Skill(skill: "graphify")` for `<purpose>`; on failure, skip silently and fall back to the agent's existing approach.* None of these change an agent's required `tools:` frontmatter beyond adding `Skill` where not already present.

1. **`codebase-auditor`** — Step 5 (dead-code/smell pass): a graph-corroborated finding is promoted from `INFO` to `LOW`/`MEDIUM` per Step 6's existing severity table, using the same corroboration rule Step 3 tooling already gets.
2. **`qa-auditor`** — impact analysis: supplement git-diff-based scoping with a blast-radius query (what calls/imports the changed symbols) to surface downstream impact a diff alone doesn't show. Still scoped to the task's own changed files per the agent's existing `HIGH`-finding rule — a graph hit outside that scope is `INFO` at most, same as today.
3. **`solution-architect`** — discovery phase: query existing dependency structure instead of manual `Glob`/`Read` exploration when scoping "what already exists" for architecture-spec/db-schema/ADR work.
4. **`documentation-auditor`** — cross-artifact traceability (e.g. PRD `FR-###` → user story) and source-accuracy checks: query the graph for symbol/doc cross-references instead of grep-only matching.
5. **`harness-engineer`** — Generate mode's "derive draft rules from the codebase itself": use graph structure/dependency observations as additional evidence before falling back to interview questions.
6. **`software-engineer`** — general code navigation in both Chain and Direct modes, gated to neither UI-facing work nor any other condition (distinct from, and in addition to, the existing UI-only Frontend Polish Pass). Requires adding `Skill` to its `tools:` frontmatter if not already present from the Frontend Polish Pass work.
7. **`qa-engineer`** — understanding code-under-test (what functions/paths a test needs to exercise) before writing failing tests (Chain) or post-hoc tests (Direct).
8. **`task-orchestrator`** — Plan Mode's feasibility read (Step 7): use graph-based scope/blast-radius understanding alongside the existing `qa-engineer`/`software-engineer` feasibility read.

## Data flow

No new cairn-owned state. Graphify's own outputs stay wherever it writes them (project-local `graphify-out/`, per its README) — cairn never manages, gitignores, or reads those files directly; all interaction goes through the `Skill(skill: "graphify")` invocation. No `.cairn/` involvement, no new `docs/` output path.

## Error handling

Same discipline as the existing Frontend Polish Pass / Design Quality Pass precedent: a missing or failing Graphify invocation is expected steady-state, not a fault — skip silently, never `ABORT`, never `HARNESS FLAG:` (that mechanism is reserved for undocumented codebase conventions, not third-party skill availability).

## Testing

No unit-testable surface changes (`tests/test_usage_dashboard.py`'s scope is untouched). Verification follows the existing command-file end-to-end pattern from `CLAUDE.md`'s Testing section: run each of the 8 agents headless against a scratch project with and without Graphify installed, confirming (a) no failure when absent, (b) the query path actually fires when present, (c) no agent ever presents a graph-sourced finding without a real `file:line` backing it.

## Open question for implementation

Graphify's public MCP-tools-reference page (`graphify.com/docs/mcp-tools`) returned 404 at investigation time, and its GitHub README doesn't enumerate exact MCP tool names. Before writing the implementation plan, install Graphify and inspect `graphify --mcp`'s actual tool list (`query_graph`, `get_neighbors`, `shortest_path`, and others were referenced in secondary sources but not confirmed against the primary source) to pin the exact call shapes `cairn:graphify-context` documents.

## Versioning

Behavior change to 8 already-wired agents plus one new skill — bump `.claude-plugin/plugin.json` per `CLAUDE.md`'s Versioning section (minor, new feature) once implemented.
