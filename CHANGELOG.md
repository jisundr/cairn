# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.20.2] - 2026-08-20

### Added
- Bare Claude Code plugin scaffold with intent-analyzer agent, routing eval suite, and setup check
- /cairn-setup and /cairn-teardown commands; /cairn-usage command wrapping codeburn web, later replaced by cairn's own usage dashboard
- /cairn-doctor health-check command
- idea-explorer agent
- writer-shared and mermaid-diagrams skills
- requirements-engineer agent and requirements-writing skill (4 doc types + Draft Mode)
- product-designer agent and product-design-writing skill (3 doc types + Impeccable pre-fill)
- solution-architect agent and solution-architecture-writing skill (3 doc types + ADR)
- documentation-auditor and documentation-engineer agents
- codebase-auditor, competitor-analyst, and market-researcher agents
- Full coding-chain port: harness-engineer, project-manager, task-orchestrator, qa-engineer, software-engineer, and qa-auditor agents, coding-chain-shared skill, /cairn-run-task command, and documentation gates (DOC PASS) across the chain
- GitHub/GitLab/ClickUp ticket sync, expanded TRACKER.md status vocabulary with Idea/Groomed states, light submodule support, and reinstated unattended execution for the task tracker
- Redesigned usage dashboard as Cairn Dashboard with task tracker board+roadmap, then a full Vite+React redesign — /api/swarms endpoint and static-file serving from plugin root
- Environment Preflight (task-orchestrator Plan Mode Step 4.5) and environment.md harness file
- Design Quality Pass (product-designer) and Frontend Polish Pass (software-engineer) via Taste Skill, Anthropic Frontend Design, and Emil Kowalski skills, plus recommended-plugin checks in /cairn-doctor
- Graphify integration: soft-optional code-graph query wired into codebase-auditor, qa-auditor, solution-architect, documentation-auditor, harness-engineer, software-engineer, qa-engineer, and task-orchestrator via a shared graphify-context skill
- Lightweight worktree+PR/MR mode (task-orchestrator Start/Finish) for Direct flow, brainstorming, and documentation-engineer doc-sync work; per-phase usage/cost table in Chain-flow PR/MR bodies
- feedback-context shared skill, /cairn-feedback command, and feedback wiring into all 16 agents' EXIT & DERAILMENT handling
- release-manager agent and /cairn-release command
- pr-reviewer agent (Input Resolution + Initial Review mode)
- Chain-vs-Direct routing heuristic and backoff-paced Unattended monitoring
- Optional goal-file authoring in cairn:plan-writing, with the Chain-vs-goal complexity heuristic later moved into plan-writing itself
- Multi-repo publish safety for task-orchestrator, /goal misuse guard hook, and plan-writing complexity routing

### Fixed
- Escaped goal-guard.sh JSON output via jq instead of raw printf
- Resolved dashboard static assets from plugin root, not project cwd (#15)
- Tracked dashboard build output in-repo instead of via submodule, so a fresh /plugin install can't fail to serve the dashboard UI (#16)
- Whole-branch review fix waves for Lightweight worktree+PR/MR mode, worktree self-contradictions in software-engineer, and feedback-context tool-mismatch/sanitization/version lookup
