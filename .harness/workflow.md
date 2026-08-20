> Refines coding-chain behavior. Gates are additive only.

# Workflow Rules

## Branching
- Branch names: feature/<slug> — *from-codebase* (4 of 5 merged PRs)

## Commits / MR
- Plain imperative descriptions are the dominant style (~150 of 203 recent commits); `chore: bump dashboard submodule pointer — <description>` for submodule-bump commits — run `scripts/sync_dashboard_dist.sh` first and commit the resulting `dashboard-dist/` changes alongside the submodule pointer bump in the same commit; occasional `feat:`/`fix:`/`docs:` prefixes appear but aren't the norm — *from-codebase*
- `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` trailer on AI-authored commits — *from-codebase*
- PR body includes `## Summary`, `## Test plan` checklist (referencing `docs/.tasks/<slug>/UAT.md` when a coding-chain task exists), and an explicit "not in this PR" scope-boundary section — *from-codebase*
- Bump `version` in `.claude-plugin/plugin.json` (semver: minor for new/changed agents/commands/hooks or behavior changes, patch for fixes) whenever a consuming project would see the change; skip only for docs/tests/internal-refactor-only changes — *from-codebase*

## Gates (additive)
- `claude plugin validate . --strict` runs in CI on every push — *from-codebase*
