> Refines coding-chain behavior. Blocking checks gate task-orchestrator Plan Mode.

# Environment Checks

## Toolchain
- [blocking] python >= 3.11 — tool-version: python, min 3.11 — evidence: pyproject.toml requires-python
- [warning] node >= 18.18.0 — tool-version: node, min 18.18.0 — evidence: dashboard/package.json devDependency vite@^5.4.0 (Vite 5's published engine requirement); docs/.plans/2026-08-19-cairn-dashboard-react-redesign.md Task 7
- [warning] npm >= 9.0.0 — tool-version: npm, min 9.0.0 — evidence: inferred from node >= 18.18.0 (npm bundled with that Node line); docs/.plans/2026-08-19-cairn-dashboard-react-redesign.md Task 7 npm install/test/build usage

## Services
<!-- no convention observed -->

## Env vars
<!-- no convention observed -->

## Other checks
- [blocking] claude CLI on PATH — command: claude --version, expect-exit 0 — evidence: user-specified (required by tests/test_intent_routing.py and every tests/smoke/*.sh script)
