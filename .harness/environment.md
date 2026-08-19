> Refines coding-chain behavior. Blocking checks gate task-orchestrator Plan Mode.

# Environment Checks

## Toolchain
- [blocking] python >= 3.11 — tool-version: python, min 3.11 — evidence: pyproject.toml requires-python

## Services
<!-- no convention observed -->

## Env vars
<!-- no convention observed -->

## Other checks
- [blocking] claude CLI on PATH — command: claude --version, expect-exit 0 — evidence: user-specified (required by tests/test_intent_routing.py and every tests/smoke/*.sh script)
